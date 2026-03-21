"""
sheets.py  –  Writes processed card rows to Google Sheets.

Sheet layout (columns A–F):
  A: Card Name (EN)
  B: Condition
  C: Set Code
  D: Card Number
  E: Buy Price (SGD)
  F: Wanted Sell Price (SGD)   ← auto-filled from last matching entry, else blank

Matching logic for sell price:
  Looks for the most recent row where Set Code + Card Number match,
  then copies the Wanted Sell Price from that row.
"""

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Config ─────────────────────────────────────────────────────────────────────

SCOPES            = ["https://www.spreadsheets.google.com/feeds",
                     "https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID          = os.environ.get("GOOGLE_SHEET_ID", "")
SHEET_TAB         = os.environ.get("GOOGLE_SHEET_TAB", "Inventory")
CREDENTIALS_FILE  = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Column indices (0-based, matching A–F layout above)
COL_NAME      = 0
COL_CONDITION = 1
COL_SET       = 2
COL_NUMBER    = 3
COL_BUY_SGD   = 4
COL_SELL_SGD  = 5

HEADER_ROW = ["Card Name (EN)", "Condition", "Set Code",
              "Card Number", "Buy Price (SGD)", "Wanted Sell Price (SGD)"]


# ── Auth ───────────────────────────────────────────────────────────────────────

def _get_service():
    creds_path = CREDENTIALS_FILE
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"Google credentials file not found at '{creds_path}'. "
            "See SETUP.md for instructions."
        )
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ensure_header(service, existing_rows: list[list]) -> None:
    """Write header row if sheet is empty."""
    if not existing_rows:
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_TAB}!A1",
            valueInputOption="RAW",
            body={"values": [HEADER_ROW]},
        ).execute()


def _find_sell_price(existing_rows: list[list], set_code: str, card_number: str) -> str:
    """
    Scan existing rows (newest first) for a matching set+number and return
    the Wanted Sell Price if one was set, else return "".
    """
    if not set_code or not card_number:
        return ""

    # Skip header row
    data_rows = existing_rows[1:] if existing_rows else []

    for row in reversed(data_rows):
        row_set    = row[COL_SET]    if len(row) > COL_SET    else ""
        row_number = row[COL_NUMBER] if len(row) > COL_NUMBER else ""
        row_sell   = row[COL_SELL_SGD] if len(row) > COL_SELL_SGD else ""

        if (row_set.strip().upper() == set_code.strip().upper() and
                row_number.strip() == card_number.strip() and
                row_sell.strip()):
            return row_sell.strip()

    return ""


# ── Main write function ────────────────────────────────────────────────────────

def write_to_sheet(processed_rows: list[dict]) -> tuple[int, int]:
    """
    Append rows to the Google Sheet.
    Returns (written_count, skipped_count).
    """
    if not SHEET_ID:
        raise EnvironmentError(
            "GOOGLE_SHEET_ID not set. Add it to your .env file."
        )

    service = _get_service()
    sheet   = service.spreadsheets()

    # Fetch all existing data for sell-price lookup
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!A:F",
    ).execute()
    existing_rows = result.get("values", [])

    _ensure_header(service, existing_rows)

    new_rows = []
    skipped  = 0

    for item in processed_rows:
        set_code    = item.get("set_code", "")
        card_number = item.get("card_number", "")
        buy_sgd     = item.get("buy_price_sgd", "")

        # Look up previous wanted sell price for this card
        sell_price = _find_sell_price(existing_rows, set_code, card_number)

        row = [
            item.get("card_name_en", ""),
            item.get("condition", ""),
            set_code,
            card_number,
            f"{buy_sgd:.2f}" if isinstance(buy_sgd, float) else "",
            sell_price,  # blank string = manual input needed
        ]
        new_rows.append(row)

    if not new_rows:
        return 0, skipped

    sheet.values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()

    return len(new_rows), skipped
