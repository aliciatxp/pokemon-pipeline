"""
scraper.py  –  Scrapes a torecacamp order receipt page.
Uses Selenium to handle JavaScript-rendered Shopify customer account pages.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re


def _get_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def _click_show_more(driver):
    """Click 'Show more items' button until it disappears."""
    while True:
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            btns = driver.find_elements(By.XPATH, "//button[@aria-label='Show more items']")
            if not btns:
                break

            btn = btns[0]
            rows_before = len(driver.find_elements(By.XPATH, "//*[@role='row']"))
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", btn)

            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.XPATH, "//*[@role='row']")) > rows_before
            )
        except Exception:
            break


def scrape_receipt(url: str) -> list[dict]:
    """
    Returns a list of dicts with keys:
        raw_name, condition_raw, buy_price_yen_raw, quantity
    """
    driver = _get_driver(headless=True)
    try:
        driver.get(url)
        time.sleep(3)

        # If redirected to login, reopen with visible browser for manual login
        if "login" in driver.current_url:
            driver.quit()
            print("\n⚠️  Login required. A browser window will open.")
            print("   Please log in, then the script will continue automatically.\n")
            driver = _get_driver(headless=False)
            driver.get(url)
            WebDriverWait(driver, 180).until(
                lambda d: "orders" in d.current_url and "login" not in d.current_url
            )
            time.sleep(3)

        # Click "Show more" until all items are loaded
        _click_show_more(driver)

        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        driver.quit()

    results = []
    rows = soup.find_all(attrs={"role": "row"})

    for row in rows:
        # Card name comes from the aria-label on the product link
        link = row.find("a", attrs={"aria-label": True})
        if not link:
            continue
        raw_name = link["aria-label"].strip()

        # Condition is in <span class="oBbb8">
        cond_el = row.find("span", class_="oBbb8")
        condition_raw = cond_el.get_text(strip=True) if cond_el else ""

        # Price: last role="cell" contains the line total
        cells = row.find_all(attrs={"role": "cell"})
        price_raw = ""
        if cells:
            last_cell = cells[-1]
            price_span = last_cell.find("span")
            if price_span:
                price_raw = price_span.get_text(strip=True)

        # Quantity: number is a text node immediately after the <span>Quantity</span>
        quantity = 1
        qty_span = row.find("span", class_="_1m6j2n31b")
        if qty_span:
            # The quantity number is the next sibling text node
            next_sibling = qty_span.next_sibling
            if next_sibling:
                try:
                    q = int(str(next_sibling).strip())
                    if 1 <= q <= 99:
                        quantity = q
                except (ValueError, TypeError):
                    pass

        # For qty > 1, the displayed price is the LINE TOTAL.
        # There's also a per-unit price in a <small> tag like ￥1,980/ユニット.
        # We use the line total and let main.py divide by quantity.

        if not raw_name:
            continue

        results.append({
            "raw_name":          raw_name,
            "condition_raw":     condition_raw,
            "buy_price_yen_raw": price_raw,
            "quantity":          quantity,
        })

    if not results:
        raise RuntimeError(
            "No items found on the receipt page. "
            "The page structure may have changed, or login may be required."
        )

    return results


'''
"""
scraper.py  –  Scrapes a torecacamp order receipt page.
"""

import requests
from bs4 import BeautifulSoup


def scrape_receipt(url: str) -> list[dict]:
    """
    Returns a list of dicts with keys:
        raw_name, condition_raw, buy_price_yen_raw, quantity
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
        price_el = (
            row.select_one("td:nth-of-type(3) span") or
            row.select_one(".order-summary__emphasis") or
            row.select_one("td.text-right span")
        )

        # ── Quantity ──────────────────────────────────────────────
        # XPath: td[1]/div/span  (first cell → div → span)
        quantity = 1
        try:
            qty_el = row.select_one("td:first-child div span")
            if qty_el:
                qty_text = qty_el.get_text(strip=True).lstrip("×x✕").strip()
                parsed_qty = int(qty_text)
                if 1 <= parsed_qty <= 99:  # sanity check
                    quantity = parsed_qty
        except (ValueError, TypeError):
            quantity = 1

        entry = {
            "raw_name":          name_el.get_text(strip=True)  if name_el  else None,
            "condition_raw":     cond_el.get_text(strip=True)  if cond_el  else None,
            "buy_price_yen_raw": price_el.get_text(strip=True) if price_el else None,
            "quantity":          quantity,
        }

        if any(v for v in entry.values()):
            results.append(entry)

    if not results:
        raise RuntimeError(
            "No items found on the receipt page. "
            "The page structure may have changed, or you may need to be logged in."
        )

    return results
'''