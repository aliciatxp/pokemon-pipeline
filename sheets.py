"""
sheets.py  –  Writes processed card rows to Google Sheets.

Existing sheet layout (columns A–I):
  A: Batch Number       ← left blank (fill manually or via Apps Script)
  B: Card Name (EN)     ← written by this script
  C: Condition          ← written by this script
  D: Set                ← written by this script
  E: Card Number        ← written by this script
  F: Date Bought        ← left blank (fill manually or via Apps Script)
  G: Buy Price (SGD)    ← written by this script
  H: Wanted Sell Price  ← auto-filled from most recent matching row, else blank
  I: Date Sold          ← left blank
  J: Sale Price         ← left blank

Only columns B, C, D, E, G are written. Everything else is left blank.
"""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Config ─────────────────────────────────────────────────────────────────────

SCOPES           = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID         = os.environ.get("GOOGLE_SHEET_ID", "")
SHEET_TAB        = os.environ.get("GOOGLE_SHEET_TAB", "Sheet1")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Column indices (0-based), matching the sheet layout above
COL_BATCH     = 0   # A - batch number        (blank)
COL_NAME      = 1   # B - card name EN        (written)
COL_CONDITION = 2   # C - condition           (written)
COL_SET       = 3   # D - set                 (written)
COL_NUMBER    = 4   # E - card number         (written)
COL_DATE_BUY  = 5   # F - date bought         (blank)
COL_BUY_SGD   = 6   # G - buy price SGD       (written)
COL_SELL_SGD  = 7   # H - wanted sell price   (auto-filled or blank)
COL_DATE_SOLD = 8   # I - date sold           (blank)
COL_SALE      = 9   # J - sale price          (blank)

TOTAL_COLS = 10     # A through J


# ── Auth ───────────────────────────────────────────────────────────────────────

def _get_service():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Google credentials file not found at '{CREDENTIALS_FILE}'. "
            "See SETUP.md for instructions."
        )
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


# ── Sell price lookup ──────────────────────────────────────────────────────────

def _find_sell_price(existing_rows: list[list], set_code: str, card_number: str) -> str:
    """
    Scan existing rows newest-first for a row where set + card number match
    and a wanted sell price exists. Returns that price or "" if not found.
    """
    if not set_code or not card_number:
        return ""

    # Skip header row (row 0)
    for row in reversed(existing_rows[1:]):
        row_set    = row[COL_SET]      if len(row) > COL_SET      else ""
        row_number = row[COL_NUMBER]   if len(row) > COL_NUMBER   else ""
        row_sell   = row[COL_SELL_SGD] if len(row) > COL_SELL_SGD else ""

        if (row_set.strip().upper()  == set_code.strip().upper() and
                row_number.strip()   == card_number.strip() and
                row_sell.strip()):
            return row_sell.strip()

    return ""


# ── Main write function ────────────────────────────────────────────────────────

def write_to_sheet(processed_rows: list[dict]) -> tuple[int, int]:
    """
    Append new rows to the existing Google Sheet.
    Returns (written_count, skipped_count).
    """
    if not SHEET_ID:
        raise EnvironmentError("GOOGLE_SHEET_ID not set. Add it to your .env file.")

    service = _get_service()
    sheet   = service.spreadsheets()

    # Fetch all existing data (A:J) for sell-price lookup
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!A:J",
    ).execute()
    existing_rows = result.get("values", [])

    new_rows = []

    for item in processed_rows:
        set_code    = item.get("set_code", "")
        card_number = item.get("card_number", "")
        buy_sgd     = item.get("buy_price_sgd", "")

        sell_price = _find_sell_price(existing_rows, set_code, card_number)

        # Build a full-width row so columns land in the right place
        row = [""] * TOTAL_COLS
        row[COL_NAME]      = item.get("card_name_en", "")
        row[COL_CONDITION] = item.get("condition", "")
        row[COL_SET]       = set_code
        row[COL_NUMBER]    = card_number
        row[COL_BUY_SGD]   = f"${buy_sgd:.2f}" if isinstance(buy_sgd, float) else ""
        row[COL_SELL_SGD]  = sell_price  # blank if no prior entry found

        new_rows.append(row)

    if not new_rows:
        return 0, 0

    sheet.values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()

    return len(new_rows), 0