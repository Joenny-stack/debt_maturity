import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

url = "https://www.rbz.co.zw/index.php"

# Suppress InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

response = requests.get(url, verify=False)
# Check for successful response
if response.status_code == 200:
    print("Page successfully fetched!")
else:
    print(f"Failed to fetch page. Status code: {response.status_code}")

soup = BeautifulSoup(response.text, "html.parser")

# Find all tables
tables = soup.find_all("table")
print(f"Number of tables found: {len(tables)}")  # Debug: number of tables

rates = []

for table in tables:
    headers = [th.text.strip() for th in table.find_all("th")]
    for row in table.find_all("tr")[1:]:
        cells = [td.text.strip() for td in row.find_all("td")]
        print(cells)  # Debug: print the cells in each row
        if len(cells) >= 2:
            date = cells[0]
            rate = cells[1]
            rates.append((date, rate))

# Print out the extracted rates
if rates:
    for date, rate in rates:
        print(f"{date}: {rate}")
else:
    print("No rates found.")
