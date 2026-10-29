"""Education state belongs to the authenticated Streamlit session, not the URL."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from professor_aria.education import curriculum, normalize_progress

SCRIPT = '''import streamlit as st
from professor_aria.education import render_education
def component(**kwargs):
    st.session_state.last_education_args = kwargs
    return st.session_state.get('education_event')
render_education(component, 'PT')
'''
PROGRESS = {"version": 1, "answers": {"ed": {"ed-medication": {"option": 1, "confidence": "high"}}}}


class EducationTests(unittest.TestCase):
    def test_question_bank_contains_only_valid_unique_cases_and_sources(self):
        bank = curriculum()
        self.assertEqual([len(p['questions']) for p in bank['patients']], [6, 3, 3, 3, 1, 1, 1])
        ids = set()
        for patient in bank['patients']:
            for question in patient['questions']:
                self.assertNotIn(question['id'], ids)
                ids.add(question['id'])
                self.assertEqual(len(question['options']), 4)
                self.assertIn(question['correct'], range(4))
                self.assertTrue(all(source in bank['sources'] for source in question['sources']))

    def test_progress_validation_cannot_accept_fabricated_scores_or_unknown_questions(self):
        raw = deepcopy(PROGRESS)
        raw['hours'] = 999
        raw['answers']['unknown'] = {'fake': {'option': 0}}
        raw['answers']['ed'].update({'fake': {'option': 0}, 'ed-afo': {'option': True},
                                    'ed-billing': {'option': -1}, 'ed-shoulder': {'option': 4}})
        self.assertEqual(normalize_progress(raw), PROGRESS)
        for value in [None, [], '', {'version': True, 'answers': {}}, {'version': 2, 'answers': {}}]:
            self.assertEqual(normalize_progress(value), {'version': 1, 'answers': {}})

    def test_submission_persists_and_replayed_event_does_not_overwrite_session(self):
        app = AppTest.from_string(SCRIPT)
        app.session_state['education_event'] = {'type': 'education_progress', 'requestId': 'submit-1',
                                               'progress': PROGRESS, 'patientId': 'ed'}
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['education_progress'], PROGRESS)
        self.assertEqual(app.session_state['last_education_args']['education_progress'], PROGRESS)
        app.session_state['education_event']['progress'] = {'version': 1, 'answers': {}}
        app.run()
        self.assertEqual(app.session_state['education_progress'], PROGRESS)
        app.session_state['education_event'] = None
        app.run()
        self.assertEqual(app.session_state['last_education_args']['education_progress'], PROGRESS)

    def test_reset_and_patient_selection_survive_rerun(self):
        app = AppTest.from_string(SCRIPT)
        app.session_state['education_progress'] = PROGRESS
        app.session_state['education_event'] = {'type': 'education_progress', 'requestId': 'reset-1',
                                               'progress': {'version': 1, 'answers': {}}, 'patientId': 'elena'}
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['last_education_args']['education_progress']['answers'], {})
        self.assertEqual(app.session_state['last_education_args']['education_patient'], 'elena')

    def test_malformed_event_does_not_erase_answers(self):
        for progress in [None, [], {'version': 2, 'answers': {}}, {'version': 1, 'answers': []}]:
            app = AppTest.from_string(SCRIPT)
            app.session_state['education_progress'] = PROGRESS
            app.session_state['education_event'] = {'type': 'education_progress', 'requestId': 'invalid', 'progress': progress}
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['education_progress'], PROGRESS)

    def test_specialty_selection_and_answers_survive_rerun(self):
        app = AppTest.from_string(SCRIPT).run()
        self.assertEqual(app.session_state['last_education_args']['education_specialty'], 'md')
        combined = deepcopy(PROGRESS)
        for specialty in ['md', 'ot', 'slp']:
            patient = next(p for p in curriculum()['patients'] if p['specialty'] == specialty)
            question = patient['questions'][0]
            combined['answers'][patient['id']] = {question['id']: {'option': question['correct'], 'confidence': None}}
            app.session_state['education_event'] = {'type': 'education_progress', 'requestId': specialty,
                'progress': combined, 'patientId': patient['id'], 'specialty': specialty}
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['last_education_args']['education_specialty'], specialty)
            self.assertEqual(app.session_state['last_education_args']['education_patient'], patient['id'])
            self.assertEqual(app.session_state['education_progress'], combined)
        app.session_state['education_event'] = None
        app.run()
        self.assertEqual(app.session_state['last_education_args']['education_progress'], combined)

    def test_navigation_routes_to_education_without_an_api_key(self):
        import aria_dashboard
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        app.session_state['authenticated'] = True
        app.session_state['user_role'] = 'PT'
        app.session_state['page'] = 'aria_dashboard'
        app.session_state['view'] = 'ARIA Education'
        app.session_state['education_progress'] = PROGRESS
        with patch('aria_dashboard._load_professor_engine', side_effect=AssertionError('Education must not call Claude')), \
             patch('professor_aria.education.render_education') as renderer:
            app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key='view').options, aria_dashboard.VIEWS)
        self.assertEqual(app.radio(key='view').value, 'ARIA Education')
        renderer.assert_called_once()


if __name__ == '__main__':
    unittest.main()
