"""
Pokemon Card Receipt Pipeline
Scrapes torecacamp order → parses cards → translates with Gemini → converts JPY→SGD → writes to Google Sheets
"""

import json
import argparse
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from scraper import scrape_receipt
from parser import parse_raw_name, extract_condition_letter
from translator import translate_card_names
from currency import get_mastercard_jpy_sgd_rate
from sheets import write_to_sheet


def is_card(item: dict) -> bool:
    """Filter out order totals, shipping lines, and blank rows."""
    name      = (item.get("raw_name") or "").strip()
    condition = (item.get("condition_raw") or "").strip()
    price_raw = (item.get("buy_price_yen_raw") or "").strip()

    if not name or not condition:
        return False
    try:
        price_clean = price_raw.replace("¥", "").replace("￥", "").replace(",", "").strip()
        price = int(price_clean)
        if price > 100_000:
            return False
    except (ValueError, TypeError):
        return False
    return True


def process_receipt(url: str, dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"Processing receipt: {url}")
    print(f"{'='*60}\n")

    # ── Step 1: Scrape ──────────────────────────────────────────
    print("📦 Step 1: Scraping receipt...")
    raw_items   = scrape_receipt(url)
    card_items  = [item for item in raw_items if is_card(item)]
    skipped     = len(raw_items) - len(card_items)
    print(f"   Found {len(raw_items)} row(s) → {len(card_items)} card(s)"
          + (f", {skipped} non-card row(s) skipped" if skipped else "")
          + "\n")

    # ── Step 2: Get exchange rate ────────────────────────────────
    print("💱 Step 2: Fetching Mastercard JPY→SGD rate...")
    rate, rate_date, rate_source = get_mastercard_jpy_sgd_rate()
    print(f"   Rate: 1 JPY = {rate:.6f} SGD  (source: {rate_source}, date: {rate_date})\n")

    # ── Step 3: Parse all cards ──────────────────────────────────
    print("🃏 Step 3: Parsing cards...")
    parsed_items = []
    for item in card_items:
        raw_name  = item.get("raw_name")
        price_raw = item.get("buy_price_yen_raw", "")
        quantity  = item.get("quantity", 1)

        parsed    = parse_raw_name(raw_name) if raw_name else {}
        condition = extract_condition_letter(item.get("condition_raw", ""))

        buy_jpy = None
        buy_sgd = None
        try:
            price_clean = price_raw.replace("¥", "").replace("￥", "").replace(",", "").strip()
            buy_jpy = int(price_clean)
            buy_sgd = round(buy_jpy * rate, 2)
        except (ValueError, TypeError, AttributeError):
            pass

        parsed_items.append({
            "jp_name":        parsed.get("pokemon_name_jp") or raw_name or "",
            "mechanic_suffix": parsed.get("mechanic_suffix"),   # e.g. "ex", "GX", "VMAX"
            "condition":      condition,
            "set_code":       parsed.get("set_code") or "",
            "card_number":    parsed.get("card_number") or "",
            "buy_jpy":        buy_jpy,
            "buy_sgd":        buy_sgd,
            "quantity":       quantity,
        })

    # ── Batch translate all names in one API call ────────────────
    print(f"   Translating {len(parsed_items)} card name(s) in one batch call...")
    jp_names   = [item["jp_name"] for item in parsed_items]
    translated = translate_card_names(jp_names)

    # ── Assemble final rows, expanding quantity > 1 ──────────────
    processed = []
    row_num   = 1
    for item in parsed_items:
        base_en    = translated.get(item["jp_name"], item["jp_name"])
        suffix     = item["mechanic_suffix"]

        # Append mechanic suffix to English name if not already present
        if suffix and not base_en.lower().endswith(suffix.lower()):
            en_name = f"{base_en} {suffix}"
        else:
            en_name = base_en

        row = {
            "card_name_en":  en_name,
            "condition":     item["condition"],
            "set_code":      item["set_code"],
            "card_number":   item["card_number"],
            "buy_price_sgd": item["buy_sgd"],
        }

        qty = item["quantity"]
        for _ in range(qty):
            processed.append(row.copy())

        qty_label = f" ×{qty}" if qty > 1 else ""
        print(f"   [{row_num}] {en_name}{qty_label} | {item['set_code']} {item['card_number']} | "
              f"¥{item['buy_jpy']} → S${item['buy_sgd']}")
        row_num += qty

    print(f"\n   Total rows to write: {len(processed)}\n")

    # ── Step 4: Write to Google Sheets ──────────────────────────
    if dry_run:
        print("🧪 Dry run — skipping Google Sheets write. Rows that would be written:")
        for row in processed:
            print(f"   {json.dumps(row, ensure_ascii=False)}")
    else:
        print("📊 Step 4: Writing to Google Sheets...")
        written, _ = write_to_sheet(processed)
        print(f"   ✅ Written: {written} row(s)")

    print("\nDone!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pokemon card receipt pipeline")
    parser.add_argument("url", help="Torecacamp order URL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print without writing to Google Sheets")
    args = parser.parse_args()
    process_receipt(args.url, dry_run=args.dry_run)