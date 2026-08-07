"""
scraper.py – Scrapes a TorecaCamp order receipt page.
Uses Selenium to handle JavaScript-rendered Shopify customer account pages.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup
import time


def _get_driver(headless=True):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

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
    """Click 'Show More' until all items are loaded."""

    while True:
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            buttons = driver.find_elements(By.TAG_NAME, "button")

            show_more = None

            for b in buttons:
                text = (b.text or "").strip()
                aria = (b.get_attribute("aria-label") or "").strip()

                if (
                    "Show more" in text
                    or "Show more" in aria
                    or "さらに表示" in text
                    or "さらに表示" in aria
                ):
                    show_more = b
                    break

            if show_more is None:
                print("No more 'Show More' button found.")
                break

            rows_before = len(driver.find_elements(By.XPATH, "//*[@role='row']"))

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                show_more,
            )

            time.sleep(0.5)

            driver.execute_script(
                "arguments[0].click();",
                show_more,
            )

            print(f"Clicked Show More ({rows_before} rows loaded)")

            WebDriverWait(driver, 10).until(
                lambda d: len(
                    d.find_elements(By.XPATH, "//*[@role='row']")
                ) > rows_before
            )

            rows_after = len(driver.find_elements(By.XPATH, "//*[@role='row']"))
            print(f"Rows: {rows_before} -> {rows_after}")

            time.sleep(1)

        except Exception as e:
            print("Stopped loading more items:", e)
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

        if "login" in driver.current_url:
            driver.quit()

            print("\n⚠ Login required.")
            print("A browser window will open.")
            print("Log in and the scraper will continue.\n")

            driver = _get_driver(headless=False)
            driver.get(url)

            WebDriverWait(driver, 180).until(
                lambda d: "orders" in d.current_url
                and "login" not in d.current_url
            )

            time.sleep(3)

        _click_show_more(driver)

        soup = BeautifulSoup(driver.page_source, "html.parser")

    finally:
        driver.quit()

    results = []

    rows = soup.find_all(attrs={"role": "row"})

    for row in rows:

        link = row.find("a", attrs={"aria-label": True})
        if not link:
            continue

        raw_name = link["aria-label"].strip()

        cond_el = row.find("span", class_="oBbb8")
        condition_raw = cond_el.get_text(strip=True) if cond_el else ""

        cells = row.find_all(attrs={"role": "cell"})

        price_raw = ""

        if cells:
            last_cell = cells[-1]
            price_span = last_cell.find("span")

            if price_span:
                price_raw = price_span.get_text(strip=True)

        quantity = 1

        qty_span = row.find("span", class_="_1m6j2n31b")

        if qty_span:
            next_sibling = qty_span.next_sibling

            if next_sibling:
                try:
                    q = int(str(next_sibling).strip())
                    if 1 <= q <= 99:
                        quantity = q
                except (ValueError, TypeError):
                    pass

        results.append(
            {
                "raw_name": raw_name,
                "condition_raw": condition_raw,
                "buy_price_yen_raw": price_raw,
                "quantity": quantity,
            }
        )

    if not results:
        raise RuntimeError(
            "No items found. The page structure may have changed."
        )

    return results

# testing
if __name__ == "__main__":
    url = input("Enter receipt URL: ").strip()

    cards = scrape_receipt(url)

    print(f"\nFound {len(cards)} cards\n")

    for i, card in enumerate(cards, 1):
        print(f"{i}. {card}")