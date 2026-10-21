"""Protect every root-app route and clear clinical state on sign out."""

from pathlib import Path
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'app.py'


class ClinicalGatewayTests(unittest.TestCase):
    def app(self):
        return AppTest.from_file(str(APP))

    def assert_locked(self, app):
        self.assertFalse(app.exception)
        self.assertTrue(any(item.value == 'ARIA Secure Clinical Gateway' for item in app.subheader))
        self.assertEqual([item.label for item in app.text_input], ['Username', 'Password'])
        self.assertEqual([item.label for item in app.button], ['Sign In'])
        self.assertNotIn('ecw-grid', '\n'.join(item.value for item in app.markdown))
        self.assertFalse(app.session_state.get('authenticated', False))

    def test_all_routes_require_authentication(self):
        for page in ['gateway', 'login', 'schedule', 'legacy_ehr', 'aria_dashboard']:
            with self.subTest(page=page):
                app = self.app()
                app.session_state['page'] = page
                with patch('aria_dashboard.render_professor_dashboard') as dashboard:
                    app.run()
                dashboard.assert_not_called()
                self.assert_locked(app)

    def test_url_parameters_cannot_bypass_login(self):
        app = self.app()
        app.query_params.update({'ed_vance': '1', 'role': 'MD', 'authenticated': 'true'})
        app.run()
        self.assert_locked(app)
        self.assertNotIn('user_role', app.session_state)

    def test_invalid_credentials_do_not_unlock_any_view(self):
        for username, password in [('', ''), ('ARIAprovider', 'incorrect'), ('ariaprovider', 'incorrect'), ('臨床', 'incorrect')]:
            with self.subTest(username=username):
                app = self.app().run()
                app.text_input(key='gateway_username').set_value(username)
                app.text_input(key='gateway_password').set_value(password)
                app.button(key='gateway_sign_in').click().run()
                self.assert_locked(app)
                self.assertEqual([item.value for item in app.error], ['Invalid clinical credentials. Access denied.'])

    def test_authenticated_navigation_and_reruns_keep_the_session(self):
        app = self.app()
        app.session_state['authenticated'] = True
        app.session_state['user_role'] = 'PT'
        app.run()
        self.assertEqual(app.session_state['page'], 'schedule')
        app.button(key='open_selected_chart').click().run()
        self.assertEqual(app.session_state['page'], 'legacy_ehr')
        with patch('aria_dashboard.render_professor_dashboard', side_effect=lambda *args, **kwargs: st.write('Protected ARIA view')):
            app.button(key='ehr_launch_aria').click().run()
            self.assertEqual(app.session_state['page'], 'aria_dashboard')
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['authenticated'])
        self.assertEqual(app.session_state['user_role'], 'PT')
        app.button(key='aria_return_to_ecw').click().run()
        app.button(key='ehr_back_to_schedule').click().run()
        self.assertEqual(app.session_state['page'], 'schedule')
        self.assertTrue(app.session_state['authenticated'])

    def test_gateway_sign_in_opens_schedule_without_a_second_login_form(self):
        app = self.app().run()
        app.text_input(key='gateway_username').set_value('ARIAprovider')
        app.text_input(key='gateway_password').set_value('test-only-password')
        # Exercise the successful-login route without storing the shared
        # production password in the test repository.
        with patch('hmac.compare_digest', side_effect=[True, True]):
            app.button(key='gateway_sign_in').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state['authenticated'])
        self.assertEqual(app.session_state['user_role'], 'PT')
        self.assertEqual(app.session_state['page'], 'schedule')
        self.assertFalse(app.text_input)
        self.assertNotIn('Sign In', [button.label for button in app.button])
        self.assertIn('ecw-grid', '\n'.join(item.value for item in app.markdown))

    def test_old_authenticated_login_routes_go_straight_to_schedule_as_pt(self):
        for page in ['login', 'ecw_login', 'gateway']:
            with self.subTest(page=page):
                app = self.app()
                app.session_state['authenticated'] = True
                app.session_state['user_role'] = 'Viewer'
                app.session_state['page'] = page
                app.run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['page'], 'schedule')
                self.assertEqual(app.session_state['user_role'], 'PT')
                self.assertFalse(app.text_input)
                self.assertNotIn('Sign In', [button.label for button in app.button])

    def test_sign_out_clears_session_and_blocks_reentry(self):
        app = self.app()
        app.session_state['authenticated'] = True
        app.session_state['user_role'] = 'PT'
        app.session_state['page'] = 'legacy_ehr'
        app.session_state['cases'] = {'example': {'note': 'Private session draft'}}
        app.session_state['bridge_history'] = ['Private session response']
        app.run()
        app.button(key='gateway_sign_out').click().run()
        self.assert_locked(app)
        self.assertEqual(app.session_state['page'], 'gateway')
        for key in ['user_role', 'cases', 'bridge_history']:
            self.assertNotIn(key, app.session_state)
        self.assertFalse(app.query_params)
        app.session_state['page'] = 'legacy_ehr'
        app.query_params['ed_vance'] = '1'
        app.run()
        self.assert_locked(app)

    def test_authenticated_deep_link_cannot_override_role(self):
        app = self.app()
        app.session_state['authenticated'] = True
        app.session_state['user_role'] = 'PT'
        app.query_params.update({'ed_vance': '1', 'role': 'MD'})
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['page'], 'legacy_ehr')
        self.assertEqual(app.session_state['user_role'], 'PT')
        self.assertFalse(app.query_params)


if __name__ == '__main__':
    unittest.main()
