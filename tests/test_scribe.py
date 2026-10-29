"""Claude SOAP parsing, guarded failures, and the Python/React event contract."""

import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from anthropic import APIError
from streamlit.testing.v1 import AppTest
from professor_aria import scribe

SOAP = {
    'subjective': 'Patient reports right foot catching at home.',
    'objective': 'Ambulated 50 ft with hemi-walker and standby assist.',
    'assessment': 'Documented foot clearance difficulty affects walking safety.',
    'plan': 'Request right AFO evaluation and reassess gait next visit.',
}
TRANSCRIPT = 'R foot catching at home. Walked 50ft w/ hemi-walker & SBA. Request AFO eval; reassess next visit.'


def response(text, stop_reason='end_turn'):
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)], stop_reason=stop_reason)


def mocked_client(text):
    context = MagicMock()
    client = context.__enter__.return_value
    client.messages.create.return_value = response(text)
    return context, client


class ScribeTests(unittest.TestCase):
    def test_json_fences_prose_and_extra_data_are_accepted(self):
        for text in [json.dumps(SOAP), '```json\n'+json.dumps(SOAP)+'\n```',
                     'Your note:\n'+json.dumps(SOAP)+'\nReview it.\n{}']:
            self.assertEqual(scribe.parse_soap_response(text), SOAP)
        quoted = dict(SOAP, subjective='Patient describes a "catch" {right foot}.')
        self.assertEqual(scribe.parse_soap_response(json.dumps(quoted)), quoted)

    def test_invalid_or_incomplete_sections_are_rejected(self):
        for data in ['', 'No JSON.', '{"subjective":', '{}',
                     json.dumps(dict(SOAP, subjective=None)),
                     json.dumps(dict(SOAP, objective=[])),
                     json.dumps(dict(SOAP, plan='  ')),
                     json.dumps(dict(SOAP, unexpected='extra'))]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                scribe.parse_soap_response(data)

    def test_generation_calls_claude_with_the_exact_transcript(self):
        context, client = mocked_client('```json\n'+json.dumps(SOAP)+'\n```')
        with patch.object(scribe, '_client', return_value=context):
            result = scribe.generate_soap(TRANSCRIPT)
        self.assertEqual(result, {'soap': SOAP, 'error': None})
        call = client.messages.create.call_args.kwargs
        self.assertIn('Never invent unmeasured tests', call['system'])
        self.assertEqual(json.loads(call['messages'][0]['content'])['transcript'], TRANSCRIPT)
        self.assertEqual(json.loads(call['messages'][0]['content'])['documentation_template'], 'physical therapy')
        self.assertGreater(call['max_tokens'], 0)
        self.assertEqual(call['timeout'], 12.0)

    def test_service_failure_hides_raw_exception_and_preserves_four_error_fields(self):
        context, client = mocked_client('unused')
        client.messages.create.side_effect = APIError('sensitive provider response', request=MagicMock(), body=None)
        with patch.object(scribe, '_client', return_value=context):
            result = scribe.generate_soap(TRANSCRIPT)
        self.assertTrue(result['error'])
        self.assertEqual(set(result['soap']), set(SOAP))
        self.assertTrue(all('No clinical draft was generated' in value for value in result['soap'].values()))
        self.assertNotIn('sensitive', json.dumps(result))
        self.assertNotIn(TRANSCRIPT, json.dumps(result))

    def test_invalid_response_and_truncation_return_errors(self):
        context, client = mocked_client('{"subjective":"only one section"}')
        with patch.object(scribe, '_client', return_value=context):
            self.assertTrue(scribe.generate_soap(TRANSCRIPT)['error'])
            client.messages.create.return_value = response(json.dumps(SOAP), 'max_tokens')
            self.assertIn('incomplete', scribe.generate_soap(TRANSCRIPT)['error'])

    def test_bad_input_does_not_make_an_api_call(self):
        with patch.object(scribe, '_client') as factory:
            for text, template in [('', 'PT Skilled SOAP'), (None, 'PT Skilled SOAP'),
                                   ('x'*24001, 'PT Skilled SOAP'), (TRANSCRIPT, 'invalid')]:
                self.assertTrue(scribe.generate_soap(text, template)['error'])
        factory.assert_not_called()

    def test_refinement_calls_claude_with_current_note_and_instruction(self):
        revised = dict(SOAP, assessment='Foot clearance deficits require reassessment of gait safety.')
        context, client = mocked_client('Here is the edit:\n```json\n'+json.dumps(revised)+'\n```')
        with patch.object(scribe, '_client', return_value=context):
            result = scribe.refine_soap(SOAP, 'Emphasize gait safety.', 'OT Functional SOAP')
        self.assertEqual(result, {'soap': revised, 'error': None})
        call = client.messages.create.call_args.kwargs
        payload = json.loads(call['messages'][0]['content'])
        self.assertEqual(payload['soap'], SOAP)
        self.assertEqual(payload['clinician_edit_instruction'], 'Emphasize gait safety.')
        self.assertEqual(payload['documentation_template'], 'occupational therapy')
        self.assertIn('Do not invent treatment activities, minutes, units', call['system'])
        self.assertEqual(call['timeout'], 12.0)

    def test_bad_refinement_input_does_not_call_claude(self):
        with patch.object(scribe, '_client') as factory:
            for note, instruction, template in [({}, 'Edit', 'PT Skilled SOAP'),
                    (SOAP, None, 'PT Skilled SOAP'), (SOAP, '', 'PT Skilled SOAP'),
                    (SOAP, 'x'*2001, 'PT Skilled SOAP'), (SOAP, 'Edit', 'bad'),
                    (dict(SOAP, objective='x'*40001), 'Edit', 'PT Skilled SOAP')]:
                self.assertTrue(scribe.refine_soap(note, instruction, template)['error'])
        factory.assert_not_called()

    def test_cpt_refinement_sends_format_and_source_fidelity_rules(self):
        revised = dict(SOAP, objective='- 97116: Documented gait training.',
                       plan='- 97116: Progress the documented gait goal.')
        context, client = mocked_client(json.dumps(revised))
        with patch.object(scribe, '_client', return_value=context):
            result = scribe.refine_soap(SOAP, 'Align with CPT 97116 & 97112')
        self.assertEqual(result['soap'], revised)
        call = client.messages.create.call_args.kwargs
        self.assertEqual(json.loads(call['messages'][0]['content'])['soap'], SOAP)
        self.assertIn(scribe.CPT_REFINEMENT_PROMPT, call['system'])
        self.assertIn('NEVER output meta-headers', call['system'])
        self.assertIn('Do NOT repeat general frequency/duration', call['system'])
        self.assertIn('omit the time', call['system'])
        self.assertIn('Do not introduce these example values', call['system'])

    def test_cloud_secret_key_is_resolved_only_on_the_server(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}), \
             patch('streamlit.secrets', {'ANTHROPIC_API_KEY': 'cloud-test-key'}), \
             patch.object(scribe, 'Anthropic') as client:
            scribe._client()
        client.assert_called_once_with(api_key='cloud-test-key', timeout=12.0, max_retries=0)

    def test_cloud_secret_overrides_stale_environment_key(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'stale-env-key'}), \
             patch('streamlit.secrets', {'ANTHROPIC_API_KEY': 'cloud-test-key'}), \
             patch.object(scribe, 'Anthropic') as client:
            scribe._client()
        self.assertEqual(client.call_args.kwargs['api_key'], 'cloud-test-key')


SCRIPT = '''import streamlit as st
from aria_dashboard import render_scribe
def component(**kwargs):
    st.session_state.last_scribe_args = kwargs
    return st.session_state.get('scribe_event')
render_scribe(component)
'''


class ScribeBridgeTests(unittest.TestCase):
    def app(self, role='PT'):
        app = AppTest.from_string(SCRIPT)
        app.session_state['user_role'] = role
        return app

    def event(self, request='draft-1'):
        return {'type': 'generate_soap', 'requestId': request, 'transcript': TRANSCRIPT, 'discipline': 'PT Skilled SOAP'}

    def test_component_generation_maps_result_once_across_reruns(self):
        app = self.app()
        app.session_state['scribe_event'] = self.event()
        with patch.object(scribe, 'generate_soap', return_value={'soap': SOAP, 'error': None}) as generate:
            app.run()
            app.run()
        self.assertFalse(app.exception)
        generate.assert_called_once_with(TRANSCRIPT, 'PT Skilled SOAP')
        args = app.session_state['last_scribe_args']
        self.assertEqual(args['key'], 'aria_charting')
        self.assertEqual(args['soap'], SOAP)
        self.assertEqual(args['transcript'], TRANSCRIPT)
        self.assertEqual(args['generation']['requestId'], 'draft-1')
        self.assertIsNone(args['generation']['error'])
        self.assertEqual(args['generation']['generated_at'], args['generated_at'])
        self.assertTrue(args['generated_at'])
        self.assertFalse(app.session_state['charting_signed'])

    def test_new_specialty_clears_previous_encounter_without_an_api_call(self):
        app = self.app()
        app.session_state['charting_soap_note'] = SOAP
        app.session_state['charting_transcript'] = TRANSCRIPT
        app.session_state['charting_signed'] = True
        app.session_state['charting_generation'] = {'requestId': 'old', 'error': None}
        app.session_state['charting_generated_at'] = 'old'
        app.session_state['scribe_event'] = {'type': 'reset_scribe', 'requestId': 'reset-ot', 'discipline': 'OT Functional SOAP'}
        with patch.object(scribe, 'generate_soap') as generate, patch.object(scribe, 'refine_soap') as refine:
            app.run()
            app.run()
        self.assertFalse(app.exception)
        generate.assert_not_called()
        refine.assert_not_called()
        args = app.session_state['last_scribe_args']
        self.assertEqual(args['soap'], {field: '' for field in SOAP})
        self.assertEqual(args['transcript'], '')
        self.assertEqual(args['discipline'], 'OT Functional SOAP')
        self.assertIsNone(args['generation'])
        self.assertIsNone(args['generated_at'])
        self.assertFalse(args['signed'])

    def test_viewer_cannot_reset_the_provider_encounter(self):
        app = self.app('Viewer')
        app.session_state['charting_soap_note'] = SOAP
        app.session_state['scribe_event'] = {'type': 'reset_scribe', 'requestId': 'unauthorized-reset', 'discipline': 'OT Functional SOAP'}
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['charting_soap_note'], SOAP)

    def test_failed_draft_can_retry_without_repeating_the_failed_request(self):
        app = self.app()
        app.session_state['scribe_event'] = self.event()
        failed = scribe._failure('Please retry.')
        with patch.object(scribe, 'generate_soap', return_value=failed) as generate:
            app.run()
            app.run()
        generate.assert_called_once()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['charting_generation']['error'], 'Please retry.')
        app.session_state['scribe_event'] = self.event('draft-2')
        with patch.object(scribe, 'generate_soap', return_value={'soap': SOAP, 'error': None}) as retry:
            app.run()
        retry.assert_called_once()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state['charting_generation']['error'])
        self.assertEqual(app.session_state['charting_soap_note'], SOAP)

    def test_refinement_is_processed_once_and_preserves_specialty(self):
        app = self.app()
        app.session_state['scribe_event'] = {'type': 'refine_soap', 'requestId': 'refine-1',
            'soap': SOAP, 'instruction': 'Emphasize safety', 'discipline': 'OT Functional SOAP', 'transcript': TRANSCRIPT}
        revised = dict(SOAP, plan='Reassess walking safety at the next encounter.')
        with patch.object(scribe, 'refine_soap', return_value={'soap': revised, 'error': None}) as refine:
            app.run()
            app.run()
        refine.assert_called_once_with(SOAP, 'Emphasize safety', 'OT Functional SOAP')
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['last_scribe_args']['soap'], revised)
        self.assertEqual(app.session_state['last_scribe_args']['discipline'], 'OT Functional SOAP')

    def test_failed_refinement_retains_clinician_note_across_reruns(self):
        app = self.app()
        app.session_state['scribe_event'] = {'type': 'refine_soap', 'requestId': 'refine-fail',
            'soap': SOAP, 'instruction': 'Emphasize safety', 'discipline': 'PT Skilled SOAP'}
        with patch.object(scribe, 'refine_soap', return_value=scribe._failure('Timed out')):
            app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['last_scribe_args']['soap'], SOAP)
        self.assertEqual(app.session_state['last_scribe_args']['draft_source'], 'manual')
        self.assertEqual(app.session_state['last_scribe_args']['generation']['error'], 'Timed out')

    def test_unexpected_backend_failure_still_returns_a_completion_timestamp(self):
        app = self.app()
        app.session_state['scribe_event'] = self.event()
        with patch.object(scribe, 'generate_soap', side_effect=RuntimeError('unexpected failure')):
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['charting_generation']['error'])
        self.assertTrue(app.session_state['last_scribe_args']['generated_at'])

    def test_same_text_new_request_always_gets_a_new_timestamp(self):
        app = self.app()
        with patch.object(scribe, 'generate_soap', return_value={'soap': SOAP, 'error': None}):
            app.session_state['scribe_event'] = self.event('first')
            app.run()
            initial = app.session_state['last_scribe_args']['generated_at']
            app.session_state['scribe_event'] = self.event('second')
            app.run()
        self.assertNotEqual(initial, app.session_state['last_scribe_args']['generated_at'])

    def test_viewer_and_invalid_requests_never_call_claude(self):
        for role, event in [('Viewer', self.event()), ('PT', dict(self.event(), requestId=None))]:
            app = self.app(role)
            app.session_state['scribe_event'] = event
            with patch.object(scribe, 'generate_soap') as generate:
                app.run()
            self.assertFalse(app.exception)
            generate.assert_not_called()

    def test_signing_validates_sections_and_rejects_error_drafts(self):
        app = self.app()
        app.session_state['scribe_event'] = {'type': 'signed', 'requestId': 'sign-1', 'soap': SOAP}
        app.session_state['charting_generation'] = {'requestId': 'draft-1', 'error': 'Failed'}
        app.run()
        self.assertNotIn('charting_signed', app.session_state)
        app.session_state['charting_generation'] = None
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['charting_signed'])
        self.assertEqual(app.session_state['charting_soap_note'], SOAP)

    def test_reviewed_local_draft_can_be_saved_after_cloud_failure(self):
        app = self.app()
        app.session_state['charting_generation'] = {'requestId': 'draft-1', 'error': 'Timed out'}
        app.session_state['scribe_event'] = {'type': 'signed', 'requestId': 'sign-local', 'soap': SOAP, 'draftSource': 'local'}
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['charting_signed'])
        self.assertEqual(app.session_state['charting_draft_source'], 'local')
        self.assertEqual(app.session_state['charting_soap_note'], SOAP)

    def test_legacy_navigation_name_migrates_to_aria_scribe(self):
        from aria_dashboard import VIEWS
        self.assertEqual(VIEWS, ['Patient Tracker', 'Measures & Trends', 'Evidence Bridge', 'EHR Sync', 'Evidence & Guidance', 'ARIA Scribe', 'ARIA Education'])
        app = AppTest.from_string('from aria_dashboard import ensure_state\nensure_state()')
        app.session_state['view'] = 'ARIA Chart'
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['view'], 'ARIA Scribe')


if __name__ == '__main__':
    unittest.main()
