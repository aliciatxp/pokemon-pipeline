"""
currency.py  –  Fetches the Mastercard JPY → SGD conversion rate.

Strategy:
  1. Try the Mastercard public converter endpoint (same one their website uses).
  2. Fall back to frankfurter.app (free, no key required) if Mastercard is unavailable.

The Mastercard public endpoint is an unofficial but stable CORS-accessible JSON endpoint
used by mastercard.us/en-us/personal/get-support/convert-currency.html
"""

import requests
from datetime import date, timedelta


# ── Mastercard public endpoint ─────────────────────────────────────────────────

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
    """
    Hit Mastercard's settlement rate endpoint.
    transaction_date: YYYY-MM-DD
    Returns the JPY→SGD rate or None on failure.
    """
    params = {
        "fxDate":             transaction_date,
        "transCurr":          "JPY",
        "crdhldBillCurr":     "SGD",
        "bankFee":            "0",      # 0% bank fee — add your card's fee if known
        "transAmt":           "1",
    }
    try:
        resp = requests.get(MC_URL, params=params, headers=MC_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Response shape: {"data": {"conversionRate": 0.00892, ...}}
        rate = data.get("data", {}).get("conversionRate")
        if rate:
            return float(rate)
    except Exception:
        pass
    return None


def _fetch_frankfurter_rate() -> tuple[float, str]:
    """
    Fallback: frankfurter.app free API (ECB-based rates, updated daily).
    Returns (rate, date_str).
    """
    url = "https://api.frankfurter.app/latest?from=JPY&to=SGD"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    rate = data["rates"]["SGD"]
    return float(rate), data["date"]


def get_mastercard_jpy_sgd_rate() -> tuple[float, str, str]:
    """
    Returns (rate, date_str, source_label).

    Tries today's Mastercard rate, then yesterday's (rates are published with a lag),
    then falls back to Frankfurter.
    """
    today = date.today()

    for delta in [0, 1, 2]:
        check_date = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
        rate = _fetch_mastercard_rate(check_date)
        if rate:
            return rate, check_date, "Mastercard"

    # Fallback
    rate, rate_date = _fetch_frankfurter_rate()
    return rate, rate_date, "Frankfurter (ECB fallback)"
