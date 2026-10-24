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
        self.assertEqual(VIEWS, ['EHR Sync & Intake', 'Evidence Bridge', 'Evidence & Guidance', 'Patient Tracker', 'Measures & Trends', 'ARIA Scribe'])
        app = AppTest.from_string('from aria_dashboard import ensure_state\nensure_state()')
        app.session_state['view'] = 'ARIA Chart'
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['view'], 'ARIA Scribe')


if __name__ == '__main__':
    unittest.main()
