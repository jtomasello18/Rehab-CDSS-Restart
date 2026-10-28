import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from streamlit.testing.v1 import AppTest

from professor_aria import chart_copilot as copilot


def event(question="When did Baclofen change and how did gait respond?", request_id="query-1"):
    return {"action": "chart_copilot_query", "patientId": "482910", "requestId": request_id, "question": question}


class ChartCopilotTests(unittest.TestCase):
    def test_local_queries_return_dated_facts_and_sources(self):
        for question, expected, source in [
            ("When did Baclofen change and how did gait respond?", "0.35 m/s", "neuro-1006"),
            ("Timeline of 10MWT, BBS and TUG", "21.4 sec", "pt-1013"),
            ("Recent labs, renal function and MRI?", "0.98 mg/dL", "acute-0721"),
            ("What did OT and SLP note about fatigue and R UE?", "20 minutes", "ot-1010"),
            ("Allergies?", "hives", "chart-profile"),
            ("Insurance and visits used?", "12 of 20", "chart-profile"),
            ("Vitals on 09/29/2026", "134/82", "irf-0929"),
        ]:
            with self.subTest(question=question):
                result = copilot.local_answer(question)
                self.assertIn(expected, result["answer"])
                self.assertIn(source, result["sourceIds"])
                self.assertTrue(all(source_id in copilot.RECORDS for source_id in result["sourceIds"]))
        self.assertIn("not establish", copilot.local_answer("Baclofen and gait")['answer'])
        self.assertIn("not documented", copilot.local_answer("Troponin on 10/22/2026")['answer'])
        self.assertIn("reconciliation", copilot.local_answer("FMA and WAB trajectory")['answer'])

    def test_claude_receives_server_record_and_bounded_context(self):
        excerpt = copilot.RECORDS['labs-1006']['entries'][0]['text']
        payload = {'answer': '10/06/2026: ' + excerpt, 'sources': [{'id': 'labs-1006', 'quote': excerpt}]}
        context = MagicMock()
        client = context.__enter__.return_value
        client.messages.create.return_value = SimpleNamespace(stop_reason='end_turn', content=[SimpleNamespace(type='text', text='```json\n' + json.dumps(payload) + '\n```\n{}')])
        with patch.object(copilot, '_client', return_value=context):
            result = copilot.answer_chart('Renal labs?')
        self.assertEqual(result['mode'], 'claude')
        self.assertEqual(result['sourceIds'], ['labs-1006'])
        request = client.messages.create.call_args.kwargs
        self.assertEqual(request['timeout'], 10)
        self.assertEqual(json.loads(request['messages'][0]['content'])['chart']['patientId'], '482910')
        self.assertIn('Do not diagnose or prescribe', request['system'])

    def test_invalid_sources_or_quotes_are_rejected(self):
        for sources in [[{'id': 'fake', 'quote': 'The chart says something.'}],
                        [{'id': 'labs-1006', 'quote': 'Creatinine 9.0 mg/dL.'}], [], [None]]:
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                copilot.validate_response(json.dumps({'answer': 'Kidney failure confirmed.', 'sources': sources}))

    def test_missing_key_timeout_and_parse_failure_retain_chart_answer(self):
        for failure in [ValueError('missing key'), TimeoutError('private API detail')]:
            with patch.object(copilot, '_client', side_effect=failure):
                result = copilot.answer_chart('Baclofen and gait')
            self.assertEqual(result['mode'], 'local')
            self.assertIn('0.35 m/s', result['answer'])
            self.assertNotIn('private', str(result))
        context = MagicMock()
        context.__enter__.return_value.messages.create.return_value = SimpleNamespace(stop_reason='end_turn', content=[SimpleNamespace(type='text', text='broken JSON')])
        with patch.object(copilot, '_client', return_value=context):
            self.assertEqual(copilot.answer_chart('MRI')['mode'], 'local')

    def test_events_are_patient_scoped_deduplicated_and_clearable(self):
        state = {}
        with patch.object(copilot, 'answer_chart', return_value=copilot.local_answer('Baclofen')) as answer:
            self.assertTrue(copilot.handle_copilot_event(event(), state))
            self.assertFalse(copilot.handle_copilot_event(event(), state))
            self.assertFalse(copilot.handle_copilot_event(dict(event(request_id='wrong-patient'), patientId='123'), state))
            self.assertFalse(copilot.handle_copilot_event(event('x' * 2001, 'long'), state))
            answer.assert_called_once()
        self.assertEqual(len(state['copilot_history']), 2)
        clear = dict(event(request_id='clear'), action='chart_copilot_clear')
        self.assertTrue(copilot.handle_copilot_event(clear, state))
        self.assertEqual(state['copilot_history'], [])
        self.assertIsNone(state['copilot_result'])

    def test_clear_wins_over_an_in_flight_response(self):
        state = {}
        def answer(*_):
            copilot.handle_copilot_event(dict(event(request_id='clear'), action='chart_copilot_clear'), state)
            return copilot.local_answer('Baclofen')
        with patch.object(copilot, 'answer_chart', side_effect=answer):
            self.assertFalse(copilot.handle_copilot_event(event(), state))
        self.assertEqual(state['copilot_history'], [])
        self.assertIsNone(state['copilot_result'])

    def test_unsupported_patient_and_empty_query_do_not_call_claude(self):
        with patch.object(copilot, '_client') as client:
            self.assertEqual(copilot.answer_chart('MRN 12345 meds?')['sourceIds'], [])
            self.assertEqual(copilot.answer_chart('')['sourceIds'], [])
            client.assert_not_called()

    def test_streamlit_routes_query_result_history_and_clear(self):
        script = '''import streamlit as st
from aria_dashboard import render_professor_dashboard
def tracker(**kwargs):
    st.session_state.last_tracker_args = kwargs
    return st.session_state.get('test_event')
render_professor_dashboard(tracker)
'''
        app = AppTest.from_string(script)
        app.session_state['view'] = 'Patient Tracker'
        app.session_state['test_event'] = event()
        with patch('professor_aria.patient_tracker.tracker_evidence', return_value={'sources': {}}), \
                patch.object(copilot, 'answer_chart', return_value=copilot.local_answer('Baclofen')) as answer:
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state['last_tracker_args']['copilotHistory']), 2)
            self.assertEqual(app.session_state['last_tracker_args']['copilotResult']['requestId'], 'query-1')
            app.run()
            answer.assert_called_once()
            app.session_state['test_event'] = dict(event(request_id='clear'), action='chart_copilot_clear')
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['last_tracker_args']['copilotHistory'], [])
            self.assertIsNone(app.session_state['last_tracker_args']['copilotResult'])


if __name__ == '__main__':
    unittest.main()
