import fitz  # PyMuPDF
import re
import os
import pandas as pd
import psycopg2
import pdfplumber
from psycopg2.extras import execute_values


def normalize_number(value):
    if value is None:
        return None
    value = value.replace(',', '').lower()
    multiplier = 1
    if 'million' in value:
        multiplier = 1_000_000
        value = re.sub(r'million', '', value)
    elif 'billion' in value:
        multiplier = 1_000_000_000
        value = re.sub(r'billion', '', value)
    try:
        return round(float(value.strip()) * multiplier)
    except:
        return None


def extract_from_tables(pdf_path):
    table_data = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text().lower()
                restated_context = any(kw in text for kw in ["restated", "hyperinflation", "inflation adjusted"])
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and len(row) > 1:
                            label = row[0].strip().lower()
                            value = row[1]
                            if not value:
                                continue
                            value = value.strip()
                            if "revenue" in label or "turnover" in label:
                                table_data["revenue"] = normalize_number(value)
                            elif "ebitda" in label:
                                table_data["ebitda"] = normalize_number(value)
                            elif "profit before" in label:
                                table_data["operating_profit"] = normalize_number(value)
                            elif "profit for the year" in label or "net profit" in label:
                                table_data["net_profit"] = normalize_number(value)
                            elif "total assets" in label:
                                table_data["total_assets"] = normalize_number(value)
                            elif "total equity" in label or "capital and reserves" in label:
                                table_data["total_equity"] = normalize_number(value)
                            elif "cash" in label and "equivalents" in label:
                                table_data["cash_equivalents"] = normalize_number(value)
                if restated_context:
                    table_data["data_source"] = "restated"
    except Exception as e:
        print(f"Error reading tables: {e}")
    return table_data


def extract_financial_data_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text("text") for page in doc)
    doc.close()

    lines = text.splitlines()
    clean_lines = [line.strip() for line in lines if line.strip()]
    clean_text = "\n".join(clean_lines)
    lower_text = clean_text.lower()

    data = {
        "company_name": None,
        "report_date": None,
        "revenue": None,
        "ebitda": None,
        "operating_profit": None,
        "net_profit": None,
        "total_assets": None,
        "total_liabilities": None,
        "total_equity": None,
        "debt_short_term": None,
        "debt_long_term": None,
        "cash_equivalents": None,
        "capex": None,
        "dividend": None,
        "exchange_losses": None,
        "hyperinflation_adjustment": None,
        "auditor_opinion": None,
        "data_source": "historical"
    }

    if any(term in lower_text for term in ["restated", "inflation adjusted", "hyperinflationary"]):
        data["data_source"] = "restated"

    aliases = {
        "revenue": ["revenue", "turnover", "sales", "group revenue"],
        "ebitda": ["ebitda", "earnings before interest", "EBITDA before fair value"],
        "operating_profit": ["operating profit", "profit before tax", "profit before taxation"],
        "net_profit": ["net profit", "profit for the year", "profit attributable"],
        "total_equity": ["total equity", "shareholders’ equity", "capital and reserves"],
        "total_assets": ["total assets", "asset base", "statement of financial position"],
        "dividend": ["dividend", "final dividend", "interim dividend"]
    }

    match = re.search(r"(?i)ok zimbabwe|econet wireless|delta corporation|cbz holdings|innscor africa|national foods", clean_text)
    if match:
        data["company_name"] = match.group(0).strip().title()

    match = re.search(r"(?i)(?:year\s+ended|as\s+at)\s+(\d{1,2}\s+\w+\s+\d{4})", clean_text)
    if match:
        data["report_date"] = match.group(1)

    for key in ["revenue", "ebitda", "operating_profit", "net_profit", "total_equity", "total_assets"]:
        data[key] = find_first_match(clean_text, aliases[key]) if 'find_first_match' in globals() else None

    # Fallback: get missing fields from tables
    table_fields = extract_from_tables(pdf_path)
    for key in table_fields:
        if data.get(key) is None:
            data[key] = table_fields[key]
        if key == "data_source":
            data["data_source"] = table_fields["data_source"]

    try:
        assets = data["total_assets"]
        equity = data["total_equity"]
        data["total_liabilities"] = assets - equity if assets and equity else None
    except:
        pass

    match = re.search(r"(?i)cash and cash equivalents.*?([0-9,]+)\s*", clean_text)
    if match:
        data["cash_equivalents"] = normalize_number(match.group(1))

    match = re.search(r"(?i)capital expenditure.*?([0-9,]+)\s*", clean_text)
    if match:
        data["capex"] = normalize_number(match.group(1))

    match = re.search(r"(?i)dividend.*?(\d+\.\d+)\s*RTGS\s*cents", clean_text)
    if match:
        data["dividend"] = float(match.group(1))

    match = re.search(r"(?i)short[-\s]?term (borrowings|debt|loans).*?([0-9,]+)\s*", clean_text)
    if match:
        data["debt_short_term"] = normalize_number(match.group(2))

    match = re.search(r"(?i)long[-\s]?term (borrowings|debt|loans).*?([0-9,]+)\s*", clean_text)
    if match:
        data["debt_long_term"] = normalize_number(match.group(2))

    match = re.search(r"(?i)(foreign exchange loss|exchange losses).*?([0-9.,]+)\s*", clean_text)
    if match:
        data["exchange_losses"] = normalize_number(match.group(2))

    match = re.search(r"(?i)monetary (gain|loss).*?([0-9.,]+)\s*", clean_text)
    if match:
        data["hyperinflation_adjustment"] = normalize_number(match.group(2))

    if "unqualified" in clean_text.lower():
        data["auditor_opinion"] = "Unqualified"
    elif "qualified" in clean_text.lower():
        data["auditor_opinion"] = "Qualified"
    else:
        data["auditor_opinion"] = "Not Found"

    return data


def save_to_postgres(records):
    conn = psycopg2.connect(
        host="localhost",
        database="debtmaturity",
        user="postgres",
        password="admin"
    )
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO financial_statements (
        company_name, report_date, revenue, ebitda, operating_profit, net_profit,
        total_assets, total_liabilities, total_equity, debt_short_term, debt_long_term,
        cash_equivalents, capex, dividend, exchange_losses, hyperinflation_adjustment, auditor_opinion
    ) VALUES %s
    """

    values = [
        (
            r["company_name"], r["report_date"], r["revenue"], r["ebitda"], r["operating_profit"], r["net_profit"],
            r["total_assets"], r["total_liabilities"], r["total_equity"], r["debt_short_term"], r["debt_long_term"],
            r["cash_equivalents"], r["capex"], r["dividend"], r["exchange_losses"], r["hyperinflation_adjustment"], r["auditor_opinion"]
        )
        for r in records
    ]

    execute_values(cursor, insert_query, values)
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Data saved to PostgreSQL")


def process_all_pdfs(folder):
    results = []
    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            path = os.path.join(folder, file)
            print(f"Processing: {file}")
            result = extract_financial_data_from_pdf(path)
            result["filename"] = file
            results.append(result)

    df = pd.DataFrame(results)
    df.to_csv("extracted_financials.csv", index=False)
    print("✅ Extraction complete. Data saved to 'extracted_financials.csv'")

    save_to_postgres(results)

def find_first_match(text, patterns):
    for pattern in patterns:
        match = re.search(rf"(?i){pattern}.*?([0-9,]+)", text)
        if match:
            return normalize_number(match.group(1))
    return None

# Example use:
# process_all_pdfs("./statements")
