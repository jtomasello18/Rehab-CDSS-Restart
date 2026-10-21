"""The multidisciplinary tracker must cite active PDFs and route to the library."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hashlib

from streamlit.testing.v1 import AppTest
from professor_aria import knowledge_base as kb
from professor_aria.patient_tracker import tracker_evidence
from test_knowledge_base import pdf_bytes
from professor_aria.vignette import ED_VANCE_NOTE, ED_VANCE_ENCOUNTERS
import aria_dashboard


class PatientTrackerTests(unittest.TestCase):
    def test_current_measure_extraction_uses_outpatient_scores_after_irf_baseline(self):
        measures = {item["measure"]: item["result"] for item in aria_dashboard.extract_metrics(ED_VANCE_NOTE)}
        self.assertEqual(measures["Berg Balance Scale (BBS)"], "38/56")
        self.assertEqual(measures["10-Meter Walk Test (10MWT)"], "0.35 m/s")
        self.assertEqual(measures["Fugl-Meyer Upper Extremity (FMA-UE)"], "22/66")
        self.assertEqual(measures["Timed Up and Go (TUG)"], "21.4 s")
        current = ED_VANCE_ENCOUNTERS[0]
        self.assertEqual(current["weeks_post_stroke"], 12)
        self.assertIn("Grade 2", current["tone"])
        self.assertIn("Grade 1+", current["tone"])
        self.assertIn("Hemi-walker", current["mobility"])
        self.assertIn("50 ft", current["mobility"])
        self.assertIn("IRF Discharge", ED_VANCE_ENCOUNTERS[-1]["label"])

    def test_old_seed_refreshes_without_overwriting_clinician_edited_notes(self):
        script = """import streamlit as st
from aria_dashboard import blank_case, ensure_state
case=blank_case('CASE-0001','Ed Vance')
case['note']=st.session_state.input_note
case['confirmed']=True
st.session_state.cases={'CASE-0001':case}
st.session_state.note_CASE_0001='unrelated draft'
ensure_state()
"""
        old_seed = "Previous presentation seed"
        with patch.object(aria_dashboard, "_LEGACY_NOTE_HASH", hashlib.sha256(old_seed.encode()).hexdigest()):
            for note in (old_seed, "Clinician-edited chart. Keep this text."):
                app = AppTest.from_string(script)
                app.session_state["input_note"] = note
                app.run()
                self.assertFalse(app.exception)
                case = app.session_state["cases"]["CASE-0001"]
                self.assertEqual(case["note"], ED_VANCE_NOTE if note == old_seed else note)
                self.assertEqual(case["confirmed"], note != old_seed)

    def test_only_real_pdf_pages_are_matched_and_removal_refreshes_all_specialties(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(kb, "DEFAULT_ROOT", Path(folder)):
            self.assertTrue(all(not sources for sources in tracker_evidence()["sources"].values()))
            document = kb.ingest_pdf("Rehabilitation CPG.pdf", pdf_bytes([
                "Stroke gait walking balance falls orthosis rehabilitation fatigue.",
                "Stroke baclofen spasticity sedation botulinum toxin CYP2C19.",
                "Stroke upper limb elbow shoulder subluxation feeding occupational therapy.",
                "Stroke aphasia naming communication cognitive fatigue speech swallowing.",
            ]))
            evidence = tracker_evidence()
            self.assertEqual(set(evidence["sources"]), {"pt", "physician", "ot", "slp"})
            for sources in evidence["sources"].values():
                self.assertTrue(sources)
                for source in sources:
                    self.assertEqual(source["filename"], "Rehabilitation CPG.pdf")
                    self.assertEqual(source["text"], document["pages_text"][source["page_number"]])
            kb.remove_document(document["document_id"])
            self.assertTrue(all(not sources for sources in tracker_evidence()["sources"].values()))

    def test_library_navigation_consumes_component_event_once(self):
        script = """import streamlit as st
from aria_dashboard import render_professor_dashboard
def tracker(**kwargs):
    st.session_state.last_tracker_args = kwargs
    return {'action': 'open_evidence_bridge', 'requestId': 'click-1'}
render_professor_dashboard(tracker)
"""
        with tempfile.TemporaryDirectory() as folder, patch.object(kb, "DEFAULT_ROOT", Path(folder)):
            app = AppTest.from_string(script)
            app.session_state["view"] = "Patient Tracker"
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["view"], "Evidence Bridge")
            self.assertIn("trackerEvidence", app.session_state["last_tracker_args"])
            self.assertEqual(app.session_state["tracker_last_request"], "click-1")
            app.session_state["_goto_view"] = "Patient Tracker"
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["view"], "Patient Tracker")


if __name__ == "__main__":
    unittest.main()
