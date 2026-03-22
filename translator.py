"""
translator.py  –  Translates Japanese Pokemon card names using Google Gemini (free tier).
All names for a receipt are sent in a single batch API call.
"""

import os
import json
from google import genai

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_AI_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_AI_API_KEY not set. Check your .env file.")
        _client = genai.Client(api_key=api_key)
    return _client


def translate_card_names(jp_names: list[str]) -> dict[str, str]:
    """
    Translate a list of Japanese Pokemon card names to English in one API call.
    Returns a dict mapping jp_name → en_name.
    Falls back to the original name if translation fails.
    """
    if not jp_names:
        return {}

    client = _get_client()
    unique = list(dict.fromkeys(jp_names))  # deduplicate, preserve order

    prompt = (
        "You are a Pokemon card expert. Translate the following Japanese Pokemon card names "
        "to their official English names. Return ONLY a JSON object mapping each Japanese name "
        "to its English name. Use official English Pokemon card names. "
        "For tag team cards like セレビィ＆フシギバナ use 'Celebi & Venusaur'. "
        "For trainer cards, items, and stadiums translate to their official English card name. "
        "No explanation, just the JSON object.\n\n"
        f"{json.dumps(unique, ensure_ascii=False, indent=2)}"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()

    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  ⚠️  Translation parse error, using original names. Raw: {raw[:200]}")
        mapping = {}

    # Return mapping for all input names (including duplicates), fall back to original
    return {name: mapping.get(name, name) for name in jp_names}