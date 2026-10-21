"""Decode model JSON surrounded by fences, commentary, or extra JSON objects."""

import json


def extract_json_object(text: str) -> dict:
    """Return the first decodable object, ignoring any text after its closing brace.

    raw_decode understands quoted braces and escapes, unlike a greedy brace regex.
    Missing/truncated JSON still raises ValueError so callers can use a safe fallback.
    """
    decoder = json.JSONDecoder()
    for offset, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text, offset)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No valid JSON object in model response")
