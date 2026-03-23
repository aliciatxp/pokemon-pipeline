"""
sheets.py  –  Writes processed card rows to Google Sheets.

Sheet layout (columns A–J):
  A: Batch Number       ← never touched
  B: Card Name (EN)     ← written by this script
  C: Condition          ← written by this script
  D: Set                ← written by this script
  E: Card Number        ← written by this script
  F: Date Bought        ← never touched
  G: Buy Price (SGD)    ← written by this script
  H: Wanted Sell Price  ← never touched (may contain formulas)
  I: Date Sold          ← never touched
  J: Sale Price         ← never touched

Strategy:
  - Find the first empty row in column B
  - Write ONLY columns B, C, D, E, G using individual range updates
  - Never write a full row — this guarantees other columns are untouched
"""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Config ─────────────────────────────────────────────────────────────────────

SCOPES           = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID         = os.environ.get("GOOGLE_SHEET_ID", "")
SHEET_TAB        = os.environ.get("GOOGLE_SHEET_TAB", "Sheet1")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Columns to write (A=1, B=2, ... in Sheets API 1-based notation)
WRITE_COLS = {
    "B": "card_name_en",
    "C": "condition",
    "D": "set_code",
    "E": "card_number",
    "G": "buy_price_sgd",
}


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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_first_empty_row(sheet, sheet_id: str, tab: str) -> int:
    """
    Returns the 1-based row number of the first empty cell in column B.
    Scans column B only — never reads other columns.
    """
    result = sheet.values().get(
        spreadsheetId=sheet_id,
        range=f"{tab}!B:B",
    ).execute()
    values = result.get("values", [])
    # values is a list of 1-element lists e.g. [["Card Name"], ["Pikachu"], ...]
    # First empty row is len(values) + 1 (1-based)
    return len(values) + 1


# ── Main write function ────────────────────────────────────────────────────────

def write_to_sheet(processed_rows: list[dict]) -> tuple[int, int]:
    """
    Append rows to the sheet starting at the first empty row in column B.
    Writes ONLY columns B, C, D, E, G — all other columns are never touched.
    Returns (written_count, skipped_count).
    """
    if not SHEET_ID:
        raise EnvironmentError("GOOGLE_SHEET_ID not set. Add it to your .env file.")
    if not processed_rows:
        return 0, 0

    service = _get_service()
    sheet   = service.spreadsheets()

    start_row = _find_first_empty_row(sheet, SHEET_ID, SHEET_TAB)
    n         = len(processed_rows)
    end_row   = start_row + n - 1

    # Build column data — one list per column
    col_data = {col: [] for col in WRITE_COLS}

    for item in processed_rows:
        col_data["B"].append([item.get("card_name_en", "")])
        col_data["C"].append([item.get("condition", "")])
        col_data["D"].append([item.get("set_code", "")])
        # Apostrophe prefix forces Sheets to treat as plain text (preserves leading zeros)
        card_number = item.get("card_number", "")
        col_data["E"].append([f"'{card_number}" if card_number else ""])
        buy_sgd = item.get("buy_price_sgd", "")
        col_data["G"].append([round(buy_sgd, 2) if isinstance(buy_sgd, float) else ""])

    # Build batch update — one ValueRange per column
    data = []
    for col, values in col_data.items():
        data.append({
            "range":  f"{SHEET_TAB}!{col}{start_row}:{col}{end_row}",
            "values": values,
        })

    sheet.values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": data,
        },
    ).execute()

    return n, 0