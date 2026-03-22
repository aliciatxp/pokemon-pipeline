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

CARD_NUMBER_RE = re.compile(r"\d{3}/\d{3}|\d{2,3}/\d{2,3}")

SET_CODE_RE = re.compile(
    r"(SV\d+[A-Za-z]*)|"    # SV1a, SV2a, SV11B
    r"(S\d+[A-Za-z]*)|"     # S1a, S12a
    r"(SM\d+\+?)|"          # SM10, SM4+
    r"(MBG)|"
    r"(M\d+[A-Za-z]?)|"     # M1S, M2a, M3  ← now matches M3 (no trailing letter required)
    r"(SI)|"
    r"(neoPROMO)|"
    r"(PROMO)|"
    r"(SWSH\d+[A-Za-z]*)",  # SWSH era
    re.IGNORECASE,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_card_number(text: str) -> str | None:
    m = CARD_NUMBER_RE.search(text)
    return m.group(0) if m else None


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
         '状態S'     → 'S'
    """
    if not condition_raw:
        return ""
    m = re.search(r"状態\s*([A-Z][+-]?)", condition_raw)
    if m:
        return m.group(1)
    # Fallback: grab any standalone grade-like token
    m = re.search(r"\b([A-Z][+-]?)\b", condition_raw)
    return m.group(1) if m else condition_raw.strip("【】 ")


# ── Main parse function ────────────────────────────────────────────────────────

def parse_raw_name(raw_name: str) -> dict:
    """
    Parse a raw Japanese card listing name into structured fields.
    Also returns mechanic_suffix so the translator can append it to the EN name.

    Example input:  "メガガルーラex SR M1S 089/063"
    Example output: {
        "raw_name_jp":      "メガガルーラex SR M1S 089/063",
        "pokemon_name_jp":  "メガガルーラ",      ← base name, no suffix
        "mechanic_suffix":  "ex",               ← suffix preserved separately
        "rarity":           "SR",
        "set_code":         "M1S",
        "card_number":      "089/063",
    }
    """
    text = raw_name.strip()

    card_number = extract_card_number(text)
    set_code    = extract_set_code(text)
    tokens      = text.split()
    rarity      = extract_rarity(tokens)

    cut        = find_cut_position(text, rarity, set_code, card_number)
    name_chunk = text[:cut].strip()

    mechanic_suffix = extract_mechanic_suffix(name_chunk) if name_chunk else None
    pokemon_name_jp = strip_mechanic_suffix(name_chunk)   if name_chunk else None

    return {
        "raw_name_jp":     raw_name,
        "pokemon_name_jp": pokemon_name_jp or None,
        "mechanic_suffix": mechanic_suffix,
        "rarity":          rarity,
        "set_code":        set_code,
        "card_number":     card_number,
    }