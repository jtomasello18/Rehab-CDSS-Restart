"""Round-trip the reviewed SOAP snapshot from Scribe into the session-backed eCW chart."""

import html
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from professor_aria.ecw_encounters import ECW_ENCOUNTERS, MD_ENCOUNTER, MD_SYNC_MESSAGE, PENDING_TEXT
from professor_aria.vignette import ED_VANCE_ENCOUNTERS

SOAP = {
    'subjective': 'Reports fatigue after baclofen increase.\nPatient requests medication review.',
    'objective': 'BP 126/76 mmHg.\nGait: 0.35 m/s; BBS 38/56.',
    'assessment': '  Persistent right hemiparesis & fall risk.  ',
    'plan': 'Review baclofen tolerance.\n- Coordinate right AFO assessment.\n<script>alert("unsafe")</script>',
}


def mock_scribe(**kwargs):
    import streamlit as st
    st.session_state.last_scribe_args = kwargs
    return st.session_state.get('scribe_event')


class EcwWriteBackTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
        app.session_state['authenticated'] = True
        app.session_state['user_role'] = 'PT'
        app.session_state['page'] = 'legacy_ehr'
        return app

    def markup(self, app):
        return '\n'.join(element.value for element in app.markdown)

    def sign(self, app, soap=SOAP, request='sign-md'):
        app.session_state['scribe_event'] = {'type': 'signed', 'requestId': request,
            'soap': soap, 'discipline': 'MD Neuro Follow-up', 'draftSource': 'manual'}
        with patch('figma_component.render', side_effect=mock_scribe):
            app.run()
        self.assertFalse(app.exception)

    def test_pending_encounter_and_historical_pt_eval_are_separate(self):
        app = self.app().run()
        self.assertFalse(app.exception)
        choices = app.selectbox(key='ehr_encounter_selector')
        self.assertEqual(choices.options, [e['label'] for e in ECW_ENCOUNTERS])
        self.assertEqual(choices.value, MD_ENCOUNTER['label'])
        self.assertIn('In Progress (Unsigned)', ' '.join(c.value for c in app.caption))
        markup = self.markup(app)
        self.assertEqual(markup.count(PENDING_TEXT), 4)
        self.assertIn('BP 126/76 mmHg | HR 70 bpm', markup)
        self.assertNotIn('97116 therapeutic exercise', markup)
        choices.select(ED_VANCE_ENCOUNTERS[0]['label']).run()
        self.assertFalse(app.exception)
        self.assertIn('Berg Balance Scale: 38/56', self.markup(app))
        self.assertNotIn(PENDING_TEXT, self.markup(app))

    def test_generation_refinement_sign_return_chart_and_switch_back(self):
        app = self.app().run()
        with patch('figma_component.render', side_effect=mock_scribe):
            app.button(key='ehr_launch_aria').click().run()
        self.assertEqual(app.radio(key='view').value, 'ARIA Scribe')
        self.assertEqual(app.session_state['last_scribe_args']['discipline'], 'MD Neuro Follow-up')
        app.session_state['scribe_event'] = {'type': 'generate_soap', 'requestId': 'generate-md',
            'transcript': 'Clinical encounter shorthand', 'discipline': 'MD Neuro Follow-up'}
        with patch('figma_component.render', side_effect=mock_scribe), \
             patch('professor_aria.scribe.generate_soap', return_value={'soap': SOAP, 'error': None}) as generate:
            app.run()
        generate.assert_called_once_with('Clinical encounter shorthand', 'MD Neuro Follow-up')
        edited = {**SOAP, 'plan': SOAP['plan'] + '\nFollow up in four weeks.'}
        app.session_state['scribe_event'] = {'type': 'refine_soap', 'requestId': 'refine-md',
            'soap': SOAP, 'instruction': 'Clarify documented MDM', 'discipline': 'MD Neuro Follow-up'}
        with patch('figma_component.render', side_effect=mock_scribe), \
             patch('professor_aria.scribe.refine_soap', return_value={'soap': edited, 'error': None}):
            app.run()
        # The editor can contain clinician edits beyond the generated response.
        self.sign(app, edited)
        self.assertEqual(app.session_state['signed_md_note'], edited)
        self.assertEqual(app.session_state['last_scribe_args']['sync_result']['message'], MD_SYNC_MESSAGE)
        metadata = dict(app.session_state['signed_md_note_metadata'])
        self.sign(app, edited)  # Replayed component events cannot re-sign.
        self.assertEqual(app.session_state['signed_md_note_metadata'], metadata)
        self.assertEqual(app.session_state['ehr_selected_encounter'], MD_ENCOUNTER['label'])
        app.session_state['scribe_event'] = None
        app.button(key='aria_return_to_ecw').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='ehr_encounter_selector').value, MD_ENCOUNTER['label'])
        self.assertIn('Signed & Locked (Synced via ARIA Scribe)', ' '.join(c.value for c in app.caption))
        markup = self.markup(app)
        for value in edited.values():
            self.assertIn(html.escape(value), markup)
        self.assertNotIn('<script>alert', markup)
        self.assertNotIn(PENDING_TEXT, markup)
        self.assertIn('Electronically signed by S. Lin, MD on 11/02/2026', markup)
        self.assertIn('99214 (Level 4 Established Patient)', markup)
        app.selectbox(key='ehr_encounter_selector').select(ED_VANCE_ENCOUNTERS[0]['label']).run()
        self.assertIn('Berg Balance Scale: 38/56', self.markup(app))
        app.selectbox(key='ehr_encounter_selector').select(MD_ENCOUNTER['label']).run()
        self.assertIn(html.escape(edited['plan']), self.markup(app))

    def test_invalid_and_non_md_signatures_do_not_fill_pending_md_note(self):
        for discipline, soap in [('MD Neuro Follow-up', {**SOAP, 'plan': ''}), ('PT Skilled SOAP', SOAP)]:
            app = self.app()
            app.session_state['page'] = 'aria_dashboard'
            app.session_state['view'] = 'ARIA Scribe'
            app.session_state['scribe_event'] = {'type': 'signed', 'requestId': 'invalid',
                'soap': soap, 'discipline': discipline, 'draftSource': 'manual'}
            with patch('figma_component.render', side_effect=mock_scribe):
                app.run()
            self.assertFalse(app.exception)
            self.assertNotIn('signed_md_note', app.session_state)

    def test_locked_snapshot_survives_new_draft_and_rejects_overwrite(self):
        app = self.app()
        app.session_state['page'] = 'aria_dashboard'
        app.session_state['view'] = 'ARIA Scribe'
        self.sign(app)
        app.session_state['scribe_event'] = {'type': 'reset_scribe', 'requestId': 'reset', 'discipline': 'MD Neuro Follow-up'}
        with patch('figma_component.render', side_effect=mock_scribe):
            app.run()
        self.assertEqual(app.session_state['signed_md_note'], SOAP)
        self.sign(app, {**SOAP, 'assessment': 'Altered assessment'}, 'overwrite')
        self.assertEqual(app.session_state['signed_md_note'], SOAP)
        self.assertFalse(app.session_state['last_scribe_args']['sync_result']['success'])

    def test_scheduler_opens_new_encounter_and_preserves_session(self):
        app = self.app()
        app.session_state['page'] = 'schedule'
        app.run()
        markup = json.loads(app.get('bidi_component')[0].proto.json)
        self.assertIn('Monday, November 2, 2026', markup)
        app.button(key='open_selected_chart').click().run()
        self.assertEqual(app.session_state['page'], 'legacy_ehr')
        self.assertEqual(app.selectbox(key='ehr_encounter_selector').value, MD_ENCOUNTER['label'])
        self.assertTrue(app.session_state['authenticated'])


if __name__ == '__main__':
    unittest.main()
