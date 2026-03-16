"""
import_deal_funnel.py — Seeds Deal_funnel_Data_1_.xlsx into Monday.com Deal Funnel board
Exact column names confirmed from actual file analysis (Section 7c, AGENT_CONTEXT).
Usage: cd data && python import_deal_funnel.py
"""
import pandas as pd
import httpx
import os
import json
import time
from dotenv import load_dotenv

load_dotenv("../backend/.env")

TOKEN   = os.getenv("MONDAY_API_TOKEN")
BOARD   = os.getenv("MONDAY_DEAL_BOARD_ID")
API     = "https://api.monday.com/v2"
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

KEEP_COLS = {
    "Deal Name":            "name",
    "Owner code":           "owner",
    "Client Code":          "client_code",
    "Deal Status":          "deal_status",
    "Closure Probability":  "probability",
    "Masked Deal value":    "deal_value",
    "Tentative Close Date": "tentative_close_date",
    "Deal Stage":           "stage",
    "Product deal":         "product_type",
    "Sector/service":       "sector",
    "Created Date":         "created_date",
}


def create_item(name: str, cols: dict) -> dict:
    gql = """mutation ($b: ID!, $n: String!, $c: JSON!) {
      create_item(board_id: $b, item_name: $n, column_values: $c) { id }
    }"""
    r = httpx.post(
        API,
        json={"query": gql, "variables": {"b": BOARD, "n": name, "c": json.dumps(cols)}},
        headers=HEADERS,
        timeout=15,
    )
    res = r.json()
    if "errors" in res:
        print(f"  WARN: {res['errors'][0]['message']}")
    return res


def import_deal_funnel():
    if not BOARD:
        print("ERROR: MONDAY_DEAL_BOARD_ID not set in backend/.env")
        return

    df = pd.read_excel("Deal_funnel_Data_1_.xlsx", sheet_name="Deal tracker", header=0)

    # Remove header-repeat rows (Deal Stage column value = "Deal Stage")
    df = df[df["Deal Stage"] != "Deal Stage"].copy()
    df = df[df["Deal Status"] != "Deal Status"].copy()

    available = {k: v for k, v in KEEP_COLS.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)
    df = df.reset_index(drop=True)

    print(f"Importing {len(df)} deals to board {BOARD}")
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
            s = str(val).strip()
            if s.lower() in ("nan", "", "nat"):
                continue
            cols[col] = s[:255]

        result = create_item(name, cols)
        if "data" in result:
            print(f"  [OK] {name}")
            success += 1
        else:
            print(f"  [FAIL] {name}")
            failed += 1
        time.sleep(0.35)

    print(f"\nDone: {success} imported | {failed} failed | {skipped} skipped")


if __name__ == "__main__":
    import_deal_funnel()
