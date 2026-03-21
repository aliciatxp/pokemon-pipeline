"""
parser.py  –  Parses a raw Japanese Pokemon card name into structured fields.
"""

import re

# ── Constants ──────────────────────────────────────────────────────────────────

RARITY_TOKENS = {
    "SAR", "CSR", "SR", "UR", "AR", "RRR", "RR", "R", "U", "C",
    "K", "PR", "CHR", "HR", "SSR", "S", "A",
}

MECHANIC_SUFFIXES = ("ex", "EX", "V", "VMAX", "VSTAR", "GX", "LV.X", "LEGEND")

CARD_NUMBER_RE = re.compile(r"\d{3}/\d{3}|\d{2,3}/\d{2,3}")

SET_CODE_RE = re.compile(
    r"(SV\d+[A-Za-z]*)|"    # SV1a, SV2a, SV11B
    r"(S\d+[A-Za-z]*)|"     # S1a, S12a
    r"(SM\d+\+?)|"          # SM10, SM4+
    r"(MBG)|"
    r"(M\d+[A-Za-z])|"      # M1S, M2a
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


def strip_mechanic_suffix(name: str) -> str:
    """Remove trailing mechanic keywords like ex, GX, VMAX from a name."""
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


# ── Main parse function ────────────────────────────────────────────────────────

def parse_raw_name(raw_name: str) -> dict:
    """
    Parse a raw Japanese card listing name into structured fields.

    Example input:  "セレビィ＆フシギバナGX RR SM9 001/095 【K】"
    Example output: {
        "raw_name_jp":    "セレビィ＆フシギバナGX RR SM9 001/095 【K】",
        "pokemon_name_jp":"セレビィ＆フシギバナ",
        "rarity":         "RR",
        "set_code":       "SM9",
        "card_number":    "001/095",
    }
    """
    text = raw_name.strip()

    card_number = extract_card_number(text)
    set_code    = extract_set_code(text)
    tokens      = text.split()
    rarity      = extract_rarity(tokens)

    # Find where the name chunk ends (first rarity/set/number token)
    cut = find_cut_position(text, rarity, set_code, card_number)
    name_chunk = text[:cut].strip()

    pokemon_name_jp = strip_mechanic_suffix(name_chunk) if name_chunk else None

    return {
        "raw_name_jp":    raw_name,
        "pokemon_name_jp": pokemon_name_jp or None,
        "rarity":          rarity,
        "set_code":        set_code,
        "card_number":     card_number,
    }
