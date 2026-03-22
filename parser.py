"""
parser.py  –  Parses a raw Japanese Pokemon card name into structured fields.
"""

import re

# ── Constants ──────────────────────────────────────────────────────────────────

RARITY_TOKENS = {
    "SAR", "CSR", "SR", "UR", "AR", "RRR", "RR", "R", "U", "C",
    "K", "PR", "CHR", "HR", "SSR", "S", "A",
}

# Order matters — longer/more specific suffixes first
MECHANIC_SUFFIXES = ("VMAX", "VSTAR", "GX", "EX", "ex", "LV.X", "LEGEND", "V")

# Matches both standard (023/102) and promo (023/XY-P, 116/SM-P, 389/SV-P) formats
CARD_NUMBER_RE = re.compile(r"(\d{3})/([A-Z]+-P|\d{3}|\d{2,3})")

# Maps promo suffix → clean set code
PROMO_SET_MAP = {
    "SV-P":  "SV-P",
    "SM-P":  "SM-P",
    "XY-P":  "XY-P",
    "BW-P":  "BW-P",
    "DP-P":  "DP-P",
    "PCG-P": "PCG-P",
    "ADV-P": "ADV-P",
}

SET_CODE_RE = re.compile(
    r"(SV\d+[A-Za-z]*)|"    # SV1a, SV2a, SV11B
    r"(S\d+[A-Za-z]*)|"     # S1a, S12a, SM8b, SM11a
    r"(SM\d+[A-Za-z]?)|"    # SM10, SM4+, SM8, SM9b
    r"(MBG)|"
    r"(M\d+[A-Za-z]?)|"     # M1S, M2a, M3
    r"(SI)|"
    r"(neoPROMO)|"
    r"(SWSH\d+[A-Za-z]*)|"  # SWSH era
    r"(PROMO)",              # generic PROMO fallback (resolved via card number below)
    re.IGNORECASE,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_card_number_and_set(text: str) -> tuple[str | None, str | None]:
    """
    Extract card number and resolve promo set codes from formats like:
      023/XY-P  →  number="023",  promo_set="XY-P"
      116/SM-P  →  number="116",  promo_set="SM-P"
      341/190   →  number="341",  promo_set=None
    Returns (card_number_str, promo_set_code_or_None)
    """
    m = CARD_NUMBER_RE.search(text)
    if not m:
        return None, None

    num_part  = m.group(1)   # e.g. "023", "116", "341"
    denom_part = m.group(2)  # e.g. "XY-P", "190"

    if denom_part in PROMO_SET_MAP:
        # Promo card: number is just the numerator, set code from suffix
        return num_part, PROMO_SET_MAP[denom_part]
    else:
        # Standard card: keep full fraction as card number
        return f"{num_part}/{denom_part}", None


def extract_set_code(text: str) -> str | None:
    m = SET_CODE_RE.search(text)
    return m.group(0) if m else None


def extract_rarity(tokens: list[str]) -> str | None:
    for t in tokens:
        cleaned = t.strip("【】[]()/")
        if cleaned in RARITY_TOKENS:
            return cleaned
    return None


def extract_mechanic_suffix(name: str) -> str | None:
    """Return the mechanic suffix present at the end of a name, or None."""
    name = name.replace("\u3000", " ").strip()
    name = re.sub(r"\(.*?\)", "", name).strip()
    for suf in MECHANIC_SUFFIXES:
        pattern = rf"[\s\u3000]{re.escape(suf)}$"
        if re.search(pattern, name, re.IGNORECASE) or name.endswith(suf):
            return suf
    return None


def strip_mechanic_suffix(name: str) -> str:
    """Remove trailing mechanic keyword from a name, returning base name only."""
    name = name.replace("\u3000", " ").strip()
    name = re.sub(r"\(.*?\)", "", name).strip()
    for suf in MECHANIC_SUFFIXES:
        pattern = rf"[\s\u3000]{re.escape(suf)}$"
        if re.search(pattern, name, re.IGNORECASE) or name.endswith(suf):
            name = re.sub(rf"[\s\u3000]?{re.escape(suf)}$", "", name, flags=re.IGNORECASE)
            break
    return name.strip("＆& ").strip()


def find_cut_position(text: str, *markers: str | None) -> int:
    """Return the index of the first marker found in text."""
    cut = len(text)
    for marker in markers:
        if not marker:
            continue
        idx = text.find(marker)
        if idx != -1 and idx < cut:
            cut = idx
    return cut


def extract_condition_letter(condition_raw: str) -> str:
    """
    Extract just the grade letter from a Japanese condition string.
    e.g. '【状態A-】' → 'A-'
         '【状態B】'  → 'B'
    Also handles condition embedded at start of raw_name.
    """
    if not condition_raw:
        return ""
    m = re.search(r"状態\s*([A-Z][+-]?)", condition_raw)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z][+-]?)\b", condition_raw)
    return m.group(1) if m else condition_raw.strip("【】 ")


def extract_leading_condition(raw_name: str) -> tuple[str, str]:
    """
    Some listings put the condition BEFORE the name:
      '【状態A-】アローラキュウコン PROMO 389/SM-P'
    Returns (condition_letter, name_with_condition_stripped).
    If no leading condition, returns ("", original_text).
    """
    m = re.match(r"^【状態([A-Z][+-]?)】\s*", raw_name.strip())
    if m:
        condition = m.group(1)
        remainder = raw_name[m.end():].strip()
        return condition, remainder
    return "", raw_name


# ── Main parse function ────────────────────────────────────────────────────────

def parse_raw_name(raw_name: str) -> dict:
    """
    Parse a raw Japanese card listing name into structured fields.
    Handles both standard and promo card number formats.
    Also handles condition-prefix entries like '【状態A-】アローラキュウコン PROMO 389/SM-P'.
    """
    # Handle condition embedded at start of name
    leading_condition, text = extract_leading_condition(raw_name.strip())

    card_number, promo_set = extract_card_number_and_set(text)

    # For promo cards the set code comes from the card number suffix;
    # for standard cards, parse it from the text normally
    if promo_set:
        set_code = promo_set
    else:
        set_code = extract_set_code(text)
        # Strip generic "PROMO" — real set resolved via card number
        if set_code and set_code.upper() == "PROMO":
            set_code = None

    tokens = text.split()
    rarity = extract_rarity(tokens)

    cut        = find_cut_position(text, rarity, set_code, card_number,
                                   "PROMO" if not promo_set else None)
    name_chunk = text[:cut].strip()

    mechanic_suffix = extract_mechanic_suffix(name_chunk) if name_chunk else None
    pokemon_name_jp = strip_mechanic_suffix(name_chunk)   if name_chunk else None

    return {
        "raw_name_jp":      raw_name,
        "pokemon_name_jp":  pokemon_name_jp or None,
        "mechanic_suffix":  mechanic_suffix,
        "leading_condition": leading_condition or None,
        "rarity":           rarity,
        "set_code":         set_code,
        "card_number":      card_number,   # "023" for promos, "341/190" for standard
    }