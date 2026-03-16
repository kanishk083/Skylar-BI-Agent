"""
import_to_monday.py — Seeds Work_Order_Tracker_Data.xlsx into Monday.com
Real column names confirmed from actual file analysis (Section 7, AGENT_CONTEXT).
Usage: cd data && python import_to_monday.py
Prerequisite: backend/.env must have MONDAY_API_TOKEN and MONDAY_ORDER_BOARD_ID
"""
import pandas as pd
import httpx
import os
import json
import time
from dotenv import load_dotenv

load_dotenv("../backend/.env")

TOKEN   = os.getenv("MONDAY_API_TOKEN")
API     = "https://api.monday.com/v2"
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

# Only import these columns — skip the 100%-null ones confirmed from analysis
KEEP_COLS = {
    "Deal name masked":                                    "name",
    "Customer Name Code":                                  "customer_name",
    "Serial #":                                            "serial_id",
    "Nature of Work":                                      "nature_of_work",
    "Execution Status":                                    "execution_status",
    "Sector":                                              "sector",
    "Type of Work":                                        "type_of_work",
    "Date of PO/LOI":                                     "po_date",
    "Probable Start Date":                                 "start_date",
    "Probable End Date":                                   "end_date",
    "Document Type":                                       "document_type",
    "Amount in Rupees (Excl of GST) (Masked)":            "contract_value",
    "Billed Value in Rupees (Excl of GST.) (Masked)":     "billed_value",
    "Amount to be billed in Rs. (Exl. of GST) (Masked)": "unbilled_amount",
    "Amount Receivable (Masked)":                          "amount_receivable",
    "Invoice Status":                                      "invoice_status",
    "WO Status (billed)":                                  "wo_status",
    "Billing Status":                                      "billing_status",
    "BD/KAM Personnel code":                               "owner_code",
}


def create_item(board_id: str, name: str, cols: dict) -> dict:
    gql = """mutation ($b: ID!, $n: String!, $c: JSON!) {
      create_item(board_id: $b, item_name: $n, column_values: $c) { id }
    }"""
    r = httpx.post(
        API,
        json={"query": gql, "variables": {"b": board_id, "n": name, "c": json.dumps(cols)}},
        headers=HEADERS,
        timeout=15,
    )
    res = r.json()
    if "errors" in res:
        print(f"  WARN: {res['errors'][0]['message']}")
    return res


def import_work_orders():
    board_id = os.getenv("MONDAY_ORDER_BOARD_ID")
    if not board_id:
        print("ERROR: MONDAY_ORDER_BOARD_ID not set in backend/.env")
        return

    # Real file: headers in row 0, actual data from row 1 onwards
    df = pd.read_excel(
        "Work_Order_Tracker_Data.xlsx",
        sheet_name="work order tracker",
        header=0,
    )
    df.columns = df.iloc[0]      # row 0 = actual headers
    df = df.iloc[1:].copy()
    df = df.reset_index(drop=True)

    # Keep only useful columns
    available = {k: v for k, v in KEEP_COLS.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)

    # Skip 100%-null columns
    df = df.dropna(axis=1, how="all")

    print(f"Importing {len(df)} work orders to board {board_id}")
    success = failed = skipped = 0

    for _, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name or name.lower() in ("nan", ""):
            skipped += 1
            continue

        cols: dict = {}
        for col, val in row.items():
            if col == "name":
                continue
            if pd.isna(val):
                continue
            str_val = str(val).strip()
            if str_val.lower() in ("nan", "", "nat"):
                continue
            cols[col] = str_val[:255]

        result = create_item(board_id, name, cols)
        if "data" in result:
            print(f"  [OK] {name}")
            success += 1
        else:
            print(f"  [FAIL] {name}")
            failed += 1
        time.sleep(0.35)  # stay under Monday.com 60 req/min limit

    print(f"\nDone: {success} imported | {failed} failed | {skipped} skipped (no name)")
    print("Verify at monday.com before starting the build timer.")


if __name__ == "__main__":
    import_work_orders()
