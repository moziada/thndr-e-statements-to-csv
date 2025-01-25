from typing import List
import os
import re
from datetime import datetime
from PyPDF2 import PdfReader
import pandas as pd
from pathlib import Path

def extract_date(file_name: str):
    # Split the filename to get the date part
    parts = file_name.split("_")
    month = parts[1]
    year = parts[2]
    day = parts[3].split(".")[0]
    return datetime.strptime(f"{day} {month} {year}", "%d %b %Y")

def get_transaction_lines(content: str) -> List[str]:
    pattern = r"^\d{1,2}/\d{1,2}/\d{4}.*$"
    matches = re.findall(pattern, content, re.MULTILINE)
    return matches

def extract_transactions(f_paths: List[str]):
    transactions = []
    for file_path in f_paths:
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_content = page.extract_text()
                transactions += get_transaction_lines(page_content)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return transactions

def extract_dividend_transactions(transactions: List):
    pattern = '^(?P<date>\d{1,2}/\d{1,2}/\d{4})\s+(?P<transaction_type>Cash Dividends)\s+[-].+\s+[-]\s+(?P<ticker>.+)\s+[-]\s+(?P<shares>\d+).*No:\d+\s+(?P<value>[\d,]+(?:\.\d+)?)'
    results = []
    for t in transactions:
        match = re.search(pattern, t)
        if match:
            result = {
                "date": match.group("date"),
                "transaction_type": match.group("transaction_type"),
                "ticker": match.group("ticker"),
                "shares": int(match.group("shares")),  # Convert to int
                "amount": float(match.group("value")),  # Convert to float
                "amount_per_share": round(float(match.group("value").replace(",", "")) / int(match.group("shares")), 3),
            }
            results.append(result)
        else:
            # check if it is dividend transaction
            check_pattern = '^(?P<date>\d{1,2}/\d{1,2}/\d{4})\s+(?P<transaction_type>Cash Dividends).*'
            match = re.search(check_pattern, t)
            if match:
                print(f"Non matched transaction: {t}")
    return results

def extract_buy_sell_transactions(transactions: List):
    pattern = '^(?P<date>\d{1,2}/\d{1,2}/\d{4})\s+(?P<transaction_type>\w+)\s+(?P<stock>.+?)\s+\((?P<quantity>\d+)@(?P<price>\d+\.\d+)\s*\)\s+[-]?(?P<value>[\d,]+(?:\.\d+)?)'
    results = []
    for t in transactions:
        match = re.search(pattern, t)
        if match:
            result = {
                "date": match.group("date"),
                "transaction_type": match.group("transaction_type"),
                "stock": match.group("stock"),
                "quantity": int(match.group("quantity")),  # Convert to int
                "price": float(match.group("price")),  # Convert to float
                "price_with_commission": round(float(match.group("value").replace(",", "")) / int(match.group("quantity")), 3),
            }
            results.append(result)
        else:
            # check if it is Buy/Sell transaction
            check_pattern = '^(?P<date>\d{1,2}/\d{1,2}/\d{4})\s+(?P<transaction_type>\w+).*'
            match = re.search(check_pattern, t)
            if match:
                transaction_type = match.group("transaction_type")
                if transaction_type == "Buy" or transaction_type == "Sell":
                    print(f"Non matched transaction: {t}")
    return results

STATEMENTS_PATH = Path("./E-STATEMENTS")
OUTPUT_PATH = Path('output')

files = [f for f in os.listdir(STATEMENTS_PATH) if f.startswith("E-STATEMENT") and f.endswith(".pdf")]
sorted_files = sorted(files, key=extract_date)
sorted_files_path = [STATEMENTS_PATH / file for file in sorted_files]
transactions = extract_transactions(sorted_files_path)

dividend_transactions = extract_dividend_transactions(transactions)
buy_sell_transactions = extract_buy_sell_transactions(transactions)

dividend_transactions_df = pd.DataFrame(dividend_transactions)
buy_sell_transactions_df = pd.DataFrame(buy_sell_transactions)

dividend_transactions_df.to_csv(OUTPUT_PATH / 'dividend_transactions.csv', index=False)
buy_sell_transactions_df.to_csv(OUTPUT_PATH / 'buy_sell_transactions.csv', index=False)
print("------ FILES EXPORTED TO `output` DIRECTORY")