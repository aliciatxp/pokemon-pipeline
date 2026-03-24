"""
currency.py  –  Fetches JPY → SGD conversion rate for Mastercard or Visa.

Bank fee: 3.25% applied on top of the base network rate (fixed).

Mastercard: uses their public settlement rate endpoint (same one their website uses).
Visa:       uses ECB mid-market rate (frankfurter.app) as the base — Visa's public
            calculator is JavaScript-rendered with no scrapeable API endpoint, but
            their rates track ECB mid-market very closely.

Fallback for both: frankfurter.app if the primary source fails.
"""

import requests
from datetime import date, timedelta
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BANK_FEE_PCT = 3.25   # fixed, applied to both card networks


# ── Mastercard ─────────────────────────────────────────────────────────────────

MC_URL = "https://www.mastercard.us/settlement/currencyrate/conversion-rate"
MC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.mastercard.us/en-us/personal/get-support/convert-currency.html",
    "Accept": "application/json, text/plain, */*",
}


def _fetch_mastercard_rate(transaction_date: str) -> float | None:
    params = {
        "fxDate":         transaction_date,
        "transCurr":      "JPY",
        "crdhldBillCurr": "SGD",
        "bankFee":        "0",
        "transAmt":       "1",
    }
    try:
        resp = requests.get(MC_URL, params=params, headers=MC_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rate = data.get("data", {}).get("conversionRate")
        if rate:
            return float(rate)
    except Exception:
        pass
    return None


# ── Frankfurter (ECB mid-market) ───────────────────────────────────────────────

def _fetch_frankfurter_rate() -> tuple[float, str]:
    url = "https://api.frankfurter.app/latest?from=JPY&to=SGD"
    resp = requests.get(url, timeout=60, verify=False)
    resp.raise_for_status()
    data = resp.json()
    return float(data["rates"]["SGD"]), data["date"]


# ── Public interface ───────────────────────────────────────────────────────────

def get_rate(card: str = "mastercard") -> tuple[float, str, str]:
    """
    Returns (rate_with_fee, date_str, source_label).

    The rate already includes the 3.25% bank fee, so it can be applied
    directly to JPY amounts to get the final SGD cost.

    card: "mastercard" or "visa"
    """
    card = card.lower().strip()
    today = date.today()
    base_rate = None
    rate_date = None
    source = None

    if card == "mastercard":
        for delta in [0, 1, 2]:
            check_date = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
            r = _fetch_mastercard_rate(check_date)
            if r:
                base_rate = r
                rate_date = check_date
                source = "Mastercard"
                break

    elif card == "visa":
        # Visa's public calculator has no scrapeable API endpoint.
        # ECB mid-market (frankfurter) is used as the base rate —
        # this closely tracks Visa's actual network rate before bank fee.
        source = "Visa (ECB mid-market base)"

    else:
        raise ValueError(f"Unknown card network: '{card}'. Use 'mastercard' or 'visa'.")

    # Fallback for Mastercard failure, or primary source for Visa
    if base_rate is None:
        base_rate, rate_date = _fetch_frankfurter_rate()
        if card == "mastercard":
            source = "Frankfurter (ECB fallback)"
        else:
            rate_date = rate_date  # already set above

    if card == "visa" and rate_date is None:
        base_rate, rate_date = _fetch_frankfurter_rate()

    # Apply 3.25% bank fee
    rate_with_fee = round(base_rate * (1 + BANK_FEE_PCT / 100), 8)

    return rate_with_fee, rate_date, source