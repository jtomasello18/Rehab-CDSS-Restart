import json
import re

from dotenv import load_dotenv
from anthropic import Anthropic, APIError

if __package__:
    from .json_utils import extract_json_object
else:
    from json_utils import extract_json_object

load_dotenv()
client = Anthropic()

INTAKE_FIELDS = {"diagnosis", "symptoms", "treatment_history", "query_intent"}
QUERY_INTENTS = {"treatment_recommendation", "literature_lookup", "general_question"}


def note_based_fallback(raw_input: str) -> dict:
    """Keep the submitted chart available for confirmation without inventing facts.

    Extractive fragments retain dates, doses and measurements, including Ed's
    multi-encounter history. Unrecognized diagnoses stay null; the complete
    original note is always preserved for the clinician to review.
    """
    fragments = [part.strip() for part in re.split(r"(?<=[.!?])\s+|[\r\n]+", raw_input) if part.strip()]
    diagnosis = next((part for part in fragments if re.search(
        r"\bdiagnos(?:is|ed)\b|\b(?:ischemic|ischaemic|hemorrhagic|haemorrhagic)\s+stroke\b|\bMCA\s+stroke\b",
        part, re.I,
    )), None)
    symptoms = [part for part in fragments if re.search(
        r"\b(?:falls?|near-falls?|fatigue|foot|pain|weakness|spasticity|tone|balance|gait|Berg|10MWT|TUG|Ashworth)\b",
        part, re.I,
    )]
    history = [part for part in fragments if re.search(
        r"\b(?:medications?|baclofen|clopidogrel|atorvastatin|treatment|therapy|rehabilitation|PT|OT|SLP|TID)\b",
        part, re.I,
    )]
    return {
        "diagnosis": diagnosis,
        "symptoms": symptoms,
        "treatment_history": " ".join(history) or None,
        "query_intent": "general_question",
        "extraction_note": "Local note-based read-back: review the original chart and confirm the selected details before proceeding.",
        "source_note": raw_input,
    }


def parse_intake_response(response_text: str, raw_input: str) -> dict:
    """Accept fenced/conversational JSON, normalize its shape, or retain the note."""
    try:
        # raw_decode handles fences, surrounding prose, multiple JSON objects,
        # and braces inside quoted clinical text without a greedy brace regex.
        parsed = extract_json_object(response_text)
        if not INTAKE_FIELDS.intersection(parsed):
            return note_based_fallback(raw_input)
        for field in ("diagnosis", "treatment_history"):
            if parsed.get(field) is not None and not isinstance(parsed[field], str):
                return note_based_fallback(raw_input)
        symptoms = parsed.get("symptoms", [])
        if not isinstance(symptoms, list) or any(not isinstance(item, str) for item in symptoms):
            return note_based_fallback(raw_input)
        intent = parsed.get("query_intent")
        result = {
            "diagnosis": parsed.get("diagnosis"),
            "symptoms": symptoms,
            "treatment_history": parsed.get("treatment_history"),
            "query_intent": intent if isinstance(intent, str) and intent in QUERY_INTENTS else "general_question",
        }
        if not any((result["diagnosis"], symptoms, result["treatment_history"])):
            return note_based_fallback(raw_input)
        return result
    except (ValueError, TypeError):
        return note_based_fallback(raw_input)


def extract_text(response) -> str:
    return "\n".join(block.text for block in response.content if block.type == "text").strip()

def parse_clinician_note(raw_input: str) -> dict:
    """
    Sends a clinician's free-text note to Claude and returns
    structured data extracted from it.
    """
    prompt = f"""You are a clinical intake assistant. Extract structured information from the clinician note below.

Return ONLY valid JSON, with exactly these fields:
- "diagnosis": string or null if not mentioned
- "symptoms": list of strings (empty list if none mentioned)
- "treatment_history": string or null if not mentioned
- "query_intent": one of "treatment_recommendation", "literature_lookup", "general_question"

Clinician note:
\"\"\"{raw_input}\"\"\"

Return ONLY the JSON object, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1600,
            messages=[{"role": "user", "content": prompt}],
        )
    except APIError:
        return note_based_fallback(raw_input)

    return parse_intake_response(extract_text(response), raw_input)


if __name__ == "__main__":
    test_note = "Patient presents with lower back pain and reduced range of motion. History of physical therapy for 6 weeks with minimal improvement. Looking for alternative treatment options."
    result = parse_clinician_note(test_note)
    print(json.dumps(result, indent=2))
