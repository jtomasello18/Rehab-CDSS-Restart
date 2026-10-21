"""Read-back JSON recovery and source-preserving presentation fallback."""

import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
from streamlit.testing.v1 import AppTest
from professor_aria import intake
import aria_dashboard


def response(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


class IntakeParsingTests(unittest.TestCase):
    def test_conversational_fenced_response_ignores_trailing_extra_objects(self):
        data = {"diagnosis": "Left MCA ischemic stroke", "symptoms": ["Foot catching {right}"],
                "treatment_history": "Baclofen increased from 5mg TID to 10mg TID.",
                "query_intent": "treatment_recommendation"}
        text = "Here is the summary:\n```json\n" + json.dumps(data) + "\n```\nLet me know if needed.\n{}"
        with patch.object(intake.client.messages, "create", return_value=response(text)):
            self.assertEqual(intake.parse_clinician_note(aria_dashboard.ECW_CLINICAL_NOTE), data)

    def test_unusable_json_retains_exact_ed_chart_values_for_confirmation(self):
        for text in ("", "I cannot return JSON.", '{"diagnosis":"Stroke", "symptoms":[',
                     '{"diagnosis": ["Stroke"]}', '{"symptoms":"Falls"}', '{}', '{"error":"Invalid JSON"}'):
            with self.subTest(text=text), patch.object(intake.client.messages, "create", return_value=response(text)):
                result = intake.parse_clinician_note(aria_dashboard.ECW_CLINICAL_NOTE)
            self.assertNotIn("error", result)
            self.assertNotIn("raw_response", result)
            self.assertEqual(result["source_note"], aria_dashboard.ECW_CLINICAL_NOTE)
            self.assertIn("left MCA ischemic stroke", result["diagnosis"])
            for detail in ("38/56", "0.35 m/s", "21.4s", "Grade 2", "Grade 1+", "near-falls"):
                self.assertIn(detail, " ".join(result["symptoms"]))
            for detail in ("09/29/2026", "10/06/2026", "5mg TID", "10mg TID"):
                self.assertIn(detail, result["treatment_history"])
            self.assertTrue(result["extraction_note"])

    def test_fallback_for_another_note_never_inserts_ed_vance_data(self):
        note = "Patient reports low back pain. No medications documented."
        result = intake.parse_intake_response("Not JSON", note)
        self.assertEqual(result["source_note"], note)
        self.assertIsNone(result["diagnosis"])
        for value in ("stroke", "Baclofen", "38/56", "Ed Vance", "482910"):
            self.assertNotIn(value, json.dumps(result))

    def test_partial_intake_json_gets_typed_defaults_and_ignores_model_error_keys(self):
        result = intake.parse_intake_response('{"diagnosis":"stroke","query_intent":["invalid"],"error":"extra"}', "stroke")
        self.assertEqual(result, {"diagnosis": "stroke", "symptoms": [],
                                  "treatment_history": None, "query_intent": "general_question"})

    def test_connection_failure_also_preserves_note_based_readback(self):
        from anthropic import APIConnectionError
        error = APIConnectionError(request=SimpleNamespace(method="POST", url="https://api.anthropic.com/v1/messages"))
        with patch.object(intake.client.messages, "create", side_effect=error):
            result = intake.parse_clinician_note(aria_dashboard.ECW_CLINICAL_NOTE)
        self.assertNotIn("error", result)
        self.assertEqual(result["source_note"], aria_dashboard.ECW_CLINICAL_NOTE)

    def test_read_back_button_displays_fallback_and_keeps_confirmation_step(self):
        script = """from aria_dashboard import render_professor_dashboard
render_professor_dashboard(lambda **kwargs: None)
"""
        with patch.object(aria_dashboard, "parse_clinician_note", intake.parse_clinician_note), \
             patch.object(intake.client.messages, "create", return_value=response('```json\n{"diagnosis":"Stroke"')):
            app = AppTest.from_string(script).run()
            self.assertFalse(app.exception)
            app.button(key="read_CASE-0001").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.button(key="yes_CASE-0001").label, "Yes, that's correct")
        case = app.session_state["cases"]["CASE-0001"]
        self.assertFalse(case["confirmed"])
        self.assertEqual(case["parsed"]["source_note"], aria_dashboard.ECW_CLINICAL_NOTE)
        self.assertIn("38/56", " ".join(element.value for element in app.markdown))


if __name__ == "__main__":
    unittest.main()
