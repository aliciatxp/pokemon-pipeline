"""
scraper.py  –  Scrapes a torecacamp order receipt page.
"""

import requests
from bs4 import BeautifulSoup


def scrape_receipt(url: str) -> list[dict]:
    """
    Returns a list of dicts with keys:
        raw_name, condition_raw, buy_price_yen_raw
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en;q=0.9",
    }

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    rows = soup.select("table tbody tr")

    for row in rows:
        name_el  = row.select_one("span.product__description__name")
        cond_el  = row.select_one(
            "span.product__description__variant.order-summary__small-text"
        )
        # Try multiple selectors for the price cell
        price_el = (
            row.select_one("td:nth-of-type(3) span") or
            row.select_one(".order-summary__emphasis") or
            row.select_one("td.text-right span")
        )

        entry = {
            "raw_name":          name_el.get_text(strip=True)  if name_el  else None,
            "condition_raw":     cond_el.get_text(strip=True)  if cond_el  else None,
            "buy_price_yen_raw": price_el.get_text(strip=True) if price_el else None,
        }

        # Skip completely empty rows
        if any(v for v in entry.values()):
            results.append(entry)

    if not results:
        raise RuntimeError(
            "No items found on the receipt page. "
            "The page structure may have changed, or you may need to be logged in."
        )

    return results
