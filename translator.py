"""
translator.py  –  Translates Japanese Pokemon card names using Google Gemini (free tier).
"""

import os
import json
import google.generativeai as genai

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GOOGLE_AI_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_AI_API_KEY not set in .env")
        genai.configure(api_key=api_key)
        _client = genai.GenerativeModel("gemini-2.0-flash")
    return _client

def translate_card_name(jp_name: str) -> str:
    return translate_card_names([jp_name]).get(jp_name, jp_name)

def translate_card_names(jp_names: list[str]) -> dict[str, str]:
    if not jp_names:
        return {}

    client = _get_client()
    unique = list(dict.fromkeys(jp_names))

    prompt = (
        "You are a Pokemon card expert. Translate the following Japanese Pokemon card names "
        "to their official English names. Return ONLY a JSON object mapping each Japanese name "
        "to its English name. Use official English Pokemon card names. "
        "For tag team cards like セレビィ＆フシギバナ use 'Celebi & Venusaur'. "
        "For trainer cards, items, stadiums — translate to their official English card name. "
        "No explanation, just JSON.\n\n"
        f"{json.dumps(unique, ensure_ascii=False, indent=2)}"
    )

    response = client.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()

    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  ⚠️  Translation parse error. Raw: {raw[:100]}")
        mapping = {}

    return {name: mapping.get(name, name) for name in jp_names}
