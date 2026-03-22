"""
Pokemon Card Receipt Pipeline
Scrapes torecacamp order → parses cards → translates with Gemini → converts JPY→SGD → writes to Google Sheets
"""

import sys
import json
import argparse
# Load .env before anything else
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from scraper import scrape_receipt
from parser import parse_raw_name
from translator import translate_card_name
from currency import get_mastercard_jpy_sgd_rate
from sheets import write_to_sheet

def process_receipt(url: str, dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"Processing receipt: {url}")
    print(f"{'='*60}\n")

    # ── Step 1: Scrape ──────────────────────────────────────────
    print("📦 Step 1: Scraping receipt...")
    raw_items = scrape_receipt(url)
    print(f"   Found {len(raw_items)} item(s)\n")

    # ── Step 2: Get exchange rate ────────────────────────────────
    print("💱 Step 2: Fetching Mastercard JPY→SGD rate...")
    rate, rate_date, rate_source = get_mastercard_jpy_sgd_rate()
    print(f"   Rate: 1 JPY = {rate:.6f} SGD  (source: {rate_source}, date: {rate_date})\n")

    # ── Step 3: Parse + translate each card ─────────────────────
    print("🃏 Step 3: Parsing and translating cards...")
    processed = []
    for i, item in enumerate(raw_items, 1):
        raw_name = item.get("raw_name")
        condition = item.get("condition_raw", "")
        price_raw = item.get("buy_price_yen_raw", "")

        # Parse card fields
        parsed = parse_raw_name(raw_name) if raw_name else {}

        # Translate name using Gemini
        jp_name = parsed.get("pokemon_name_jp") or raw_name
        en_name = translate_card_name(jp_name) if jp_name else None

        # Convert price
        buy_jpy = None
        buy_sgd = None
        try:
            price_clean = price_raw.replace("¥", "").replace("￥", "").replace(",", "").strip()
            buy_jpy = int(price_clean)
            buy_sgd = round(buy_jpy * rate, 2)
        except (ValueError, TypeError, AttributeError):
            pass

        row = {
            "card_name_en":  en_name or "",
            "condition":     condition or "",
            "set_code":      parsed.get("set_code") or "",
            "card_number":   parsed.get("card_number") or "",
            "buy_price_sgd": buy_sgd,
            "_raw_name":     raw_name,
            "_buy_jpy":      buy_jpy,
        }
        processed.append(row)

        print(f"   [{i}] {en_name or '(untranslated)'} | {parsed.get('set_code','')} {parsed.get('card_number','')} | "
              f"¥{buy_jpy} → S${buy_sgd}")

    print()

    # ── Step 4: Write to Google Sheets ──────────────────────────
    if dry_run:
        print("🧪 Dry run — skipping Google Sheets write. Rows that would be written:")
        for row in processed:
            print(f"   {json.dumps({k:v for k,v in row.items() if not k.startswith('_')}, ensure_ascii=False)}")
    else:
        print("📊 Step 4: Writing to Google Sheets...")
        written, skipped = write_to_sheet(processed)
        print(f"   ✅ Written: {written} row(s)")
        if skipped:
            print(f"   ⏭  Skipped (duplicate): {skipped} row(s)")

    print("\nDone!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pokemon card receipt pipeline")
    parser.add_argument("url", help="Torecacamp order URL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print without writing to Google Sheets")
    args = parser.parse_args()
    process_receipt(args.url, dry_run=args.dry_run)