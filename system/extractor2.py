import os
import re
import csv
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from rapidfuzz import fuzz, process
import camelot

# Normalize number string
def normalize_number(num_str):
    try:
        num_str = num_str.replace(",", "").replace(" ", "").replace("USD", "")
        return float(re.findall(r"[-+]?\d*\.\d+|\d+", num_str)[0])
    except Exception:
        return None

# OCR and fuzzy logic
def ocr_and_fuzzy_extract(pdf_path, aliases):
    data = {}
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = pytesseract.image_to_string(img).lower()

                for key, patterns in aliases.items():
                    if data.get(key) is not None:
                        continue
                    best_match, score, match_text = None, 0, ""
                    for pattern in patterns:
                        result = process.extractOne(pattern, ocr_text.splitlines(), scorer=fuzz.partial_ratio)
                        if result and result[1] > score and re.search(r"\d", result[0]):
                            best_match = pattern
                            score = result[1]
                            match_text = result[0]
                    if best_match and score > 80:
                        match = re.search(r"([0-9,.]+)", match_text)
                        if match:
                            data[key] = normalize_number(match.group(1))
    except Exception as e:
        print(f"OCR error in {pdf_path}: {e}")
    return data

# Main extraction logic
def extract_financial_data_from_pdf(pdf_path, aliases):
    data = {key: None for key in aliases}

    try:
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
    except Exception as e:
        print(f"Table extraction error in {pdf_path}: {e}")
        tables = []

    for table in tables:
        df = table.df.apply(lambda x: x.str.lower() if x.dtype == "object" else x)
        for key, patterns in aliases.items():
            if data.get(key) is not None:
                continue
            for pattern in patterns:
                match = df[df.apply(lambda row: row.astype(str).str.contains(pattern).any(), axis=1)]
                if not match.empty:
                    value_row = match.iloc[0]
                    for cell in value_row:
                        if re.search(r"[0-9,.]+", cell):
                            val = normalize_number(cell)
                            if val is not None:
                                data[key] = val
                                break

    # Fallback OCR + Fuzzy
    ocr_fuzzy_data = ocr_and_fuzzy_extract(pdf_path, aliases)
    for key in ocr_fuzzy_data:
        if data.get(key) is None:
            data[key] = ocr_fuzzy_data[key]

    return data

# Save to CSV
def save_to_csv(csv_path, filename, results):
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            # Write header if the file doesn't exist
            writer.writerow(["filename"] + list(results.keys()))
        writer.writerow([filename] + list(results.values()))

# Process all PDFs in folder
def process_folder(folder_path, csv_path="financials_export.csv"):
    aliases = {
        "revenue": ["revenue", "turnover", "sales"],
        "ebitda": ["ebitda", "operating profit", "earnings before interest", "operating income"],
        "net_profit": ["net profit", "net income", "profit after tax", "profit for the year"],
        "assets": ["total assets", "gross assets", "asset base"],
        "equity": ["shareholders' equity", "equity", "net worth"],
        "liabilities": ["total liabilities", "liabilities", "debt"]
    }

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("No PDFs found in the folder.")
        return

    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        print(f"\n📄 Processing: {pdf_file}")
        results = extract_financial_data_from_pdf(pdf_path, aliases)

        for k, v in results.items():
            print(f"  {k.title():<12}: {v if v is not None else 'Not found'}")

        save_to_csv(csv_path, pdf_file, results)

    print("\n✅ All data saved to CSV.")

# Run the script
if __name__ == "__main__":
    folder_to_process = "pdfs"  # Your folder with PDFs
    process_folder(folder_to_process)
