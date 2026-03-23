"""
sheets.py  –  Writes processed card rows to Google Sheets.

Sheet layout (columns A–J):
  A: Batch Number       ← written by this script (auto-incremented)
  B: Card Name (EN)     ← written by this script
  C: Condition          ← written by this script
  D: Set                ← written by this script
  E: Card Number        ← written by this script
  F: Date Bought        ← written by this script (today's date)
  G: Buy Price (SGD)    ← written by this script
  H: Wanted Sell Price  ← never touched (may contain formulas)
  I: Date Sold          ← never touched
  J: Sale Price         ← never touched

Columns H, I, J are never written — safe for formulas.
"""

import os
from datetime import date
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Config ─────────────────────────────────────────────────────────────────────

SCOPES           = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID         = os.environ.get("GOOGLE_SHEET_ID", "")
SHEET_TAB        = os.environ.get("GOOGLE_SHEET_TAB", "Sheet1")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")


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

def _find_first_empty_row(sheet) -> int:
    """First empty row in column B (1-based)."""
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!B:B",
    ).execute()
    return len(result.get("values", [])) + 1


def _get_next_batch_number(sheet) -> int:
    """Read column A, find the highest batch number, return it + 1."""
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!A:A",
    ).execute()
    values = result.get("values", [])
    max_batch = 0
    for row in values[1:]:  # skip header
        if row:
            try:
                val = int(row[0])
                if val > max_batch:
                    max_batch = val
            except (ValueError, TypeError):
                pass
    return max_batch + 1


# ── Main write function ────────────────────────────────────────────────────────

def write_to_sheet(processed_rows: list[dict]) -> tuple[int, int]:
    """
    Append rows to the sheet starting at the first empty row in column B.
    Writes columns A, B, C, D, E, F, G only — H, I, J are never touched.
    Returns (written_count, skipped_count).
    """
    if not SHEET_ID:
        raise EnvironmentError("GOOGLE_SHEET_ID not set. Add it to your .env file.")
    if not processed_rows:
        return 0, 0

    service   = _get_service()
    sheet     = service.spreadsheets()

    start_row   = _find_first_empty_row(sheet)
    batch_num   = _get_next_batch_number(sheet)
    today_str   = date.today().strftime("%d/%m/%Y")  # dd/MM/yyyy e.g. 24/03/2026
    n           = len(processed_rows)
    end_row     = start_row + n - 1

    # Build per-column value lists
    col_A, col_B, col_C, col_D, col_E, col_F, col_G = [], [], [], [], [], [], []

    for item in processed_rows:
        card_number = item.get("card_number", "")
        buy_sgd     = item.get("buy_price_sgd", "")

        col_A.append([batch_num])
        col_B.append([item.get("card_name_en", "")])
        col_C.append([item.get("condition", "")])
        col_D.append([item.get("set_code", "")])
        col_E.append([f"'{card_number}" if card_number else ""])  # plain text
        col_F.append([today_str])
        col_G.append([round(buy_sgd, 2) if isinstance(buy_sgd, float) else ""])

    # One ValueRange per column — H, I, J untouched
    data = [
        {"range": f"{SHEET_TAB}!A{start_row}:A{end_row}", "values": col_A},
        {"range": f"{SHEET_TAB}!B{start_row}:B{end_row}", "values": col_B},
        {"range": f"{SHEET_TAB}!C{start_row}:C{end_row}", "values": col_C},
        {"range": f"{SHEET_TAB}!D{start_row}:D{end_row}", "values": col_D},
        {"range": f"{SHEET_TAB}!E{start_row}:E{end_row}", "values": col_E},
        {"range": f"{SHEET_TAB}!F{start_row}:F{end_row}", "values": col_F},
        {"range": f"{SHEET_TAB}!G{start_row}:G{end_row}", "values": col_G},
    ]

    sheet.values().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": data,
        },
    ).execute()

    print(f"   Batch #{batch_num} | Date: {today_str}")
    return n, 0