# Pokemon Card Receipt Pipeline

An order receipt parser which scrapes all the cards from the url, translates the Pokemon Japanese names to English, converts the price to SGD (with your card's exchange rate + bank fee), and dumps everything neatly into a Google Sheet.

---

## What It Does

```
Torecacamp order URL
  → scrape cards
  → translate JP names to EN (Gemini)
  → convert JPY → SGD (Mastercard or Visa rate + 3.25% bank fee)
  → append to Google Sheet (batch number, date, card details, buy price)
```

---

## Requirements

- Python 3.11+
- Anaconda
- A Google Cloud project (for Sheets API)
- A Google AI Studio API key (free, for Gemini translation)
- Access to the Google Sheet

---

## Usage

See [`SETUP_WINDOWS.md`](SETUP_WINDOWS.md)

```bash
conda activate pokemon-pipeline

# Dry run first (doesn't write to the google sheet)
python main.py "https://torecacamp-pokemon.com/.../orders/..." --dry-run

# Full run with Mastercard rate (default)
python main.py "https://torecacamp-pokemon.com/.../orders/..."

# Full run with Visa rate
python main.py "https://torecacamp-pokemon.com/.../orders/..." --card visa
```

## Files

| File | What it does |
|---|---|
| `main.py` | Entry point, orchestrates everything |
| `scraper.py` | Scrapes the order page |
| `parser.py` | Parses Japanese card names into fields |
| `translator.py` | Translates card names via Gemini API |
| `currency.py` | Fetches exchange rate (Mastercard/Visa) + applies bank fee |
| `sheets.py` | Writes to Google Sheets |
| `.env.example` | Template for secrets — copy to `.env` and fill in |

---

## Notes

- Exchange rates use Mastercard's public settlement endpoint or ECB mid-market (Visa/fallback), with a fixed 3.25% bank fee calculated in
- Card names are translated in one batch API call per receipt
- Promo cards (XY-P, SM-P, SV-P, etc.) are handled separately from standard sets

---

## But why use an LLM for translation?

Pokemon card names seem simple until you're dealing with them at scale since Pokemon card listings in online shops can vary wildly in formatting, causing traditional dictionary lookups or translation APIs to fall apart. Some examples of the challenges I faced with traditional methods before deciding on using an LLM:

**Mechanic suffixes are baked into the name:**
Cards are listed as `ピカチュウex`, `リザードンVMAX`, `ミュウGX` — the mechanic suffix (`ex`, `VMAX`, `GX`) is part of the card identity, not just a descriptor. A naive translator would mangle these or drop them entirely.

**Tag team cards use special characters:**
Cards like `セレビィ＆フシギバナGX` use the full-width `＆` character and combine two Pokemon into one card name. The official English name follows a specific format (`Celebi & Venusaur GX`) that requires knowing both Pokemon names and the convention for writing them together.

**Trainer, item, and stadium cards don't follow Pokemon naming rules:**
`グズマ` → `Guzma`, `フウとラン` → `Winona`, `シロナ` → `Cynthia` — these are character names with no direct translation. A standard translation API would give you a phonetic mess. An LLM knows the official English card names.

**Regional variants have specific naming conventions:**
`アローラキュウコン` isn't just "Alolan Ninetales" — the official English card name is `Alolan Ninetales`, not `Ninetales (Alola Form)` or any other variant. Same goes for Galarian, Hisuian, and Paldean forms.

**Promo cards often have context-dependent names:**
A promo Pikachu listed as `ピカチュウ` with a special set code could be one of dozens of different cards. The LLM can factor in surrounding context from the listing (set code, card number, rarity) to give a more accurate translation.

**And many other edge cases:**
`ニャビー` → `Litten`, `ウパー` → `Wooper`, `ペロッパフ` → `Swirlix` — these have no phonetic relationship to their English names whatsoever. A rules-based approach would need a manually maintained dictionary of thousands of entries that goes stale with every new set. An LLM handles these out of the box and stays current with newer card sets without any maintenance.