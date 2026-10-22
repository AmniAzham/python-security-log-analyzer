"""API tests: all data is synthetic and requests stay in process."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import app, allowed_origins, MAX_UPLOAD_BYTES


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sample = Path('data/sample_auth_logs.csv').read_bytes()

    def upload(self, content, config=None, **kwargs):
        return self.client.post('/api/analyze', content=content,
                                params={'config': json.dumps(config or {})},
                                headers={'Content-Type': 'text/csv'}, **kwargs)

    def test_sample_matches_uploaded_sample(self):
        sample = self.client.post('/api/sample')
        self.assertEqual(sample.status_code, 200)
        uploaded = self.upload(self.sample)
        self.assertEqual(sample.json(), uploaded.json())
        result = sample.json()
        self.assertEqual((result['events_analyzed'], result['total_alerts']), (19, 4))
        self.assertEqual(sum(bucket['success'] + bucket['failure'] for bucket in result['activity']), 19)
        self.assertEqual([alert['rule'] for alert in result['alerts']], [
            'repeated_failed_logins', 'multiple_account_targeting',
            'repeated_failed_logins', 'success_after_failures'])

    def test_custom_thresholds(self):
        response = self.upload(self.sample, {'failure_threshold': 6, 'account_threshold': 4, 'success_failure_threshold': 6})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_alerts'], 0)

    def test_strict_settings(self):
        for config in ({'failure_threshold': 0}, {'account_threshold': -1},
                       {'failure_threshold': True}, {'failure_threshold': 1.5},
                       {'failure_threshold': '5'}, {'path': '/etc/passwd'}, [], None):
            with self.subTest(config=config):
                response = self.client.post('/api/sample', params={'config': json.dumps(config)})
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.post('/api/sample', params={'config': '{broken'}).status_code, 422)

    def test_data_quality_and_duplicates(self):
        header, first, *_ = self.sample.splitlines()
        content = b'\n'.join([header, first, first, b'bad,alice,192.0.2.1,login,failure'])
        result = self.upload(content).json()
        self.assertEqual((result['events_analyzed'], result['duplicates'], result['invalid_rows']), (1, 1, 1))
        self.assertEqual(len(result['warnings']), 1)
        self.assertEqual(result['total_alerts'], 0)

    def test_bad_csv_and_encoding(self):
        for content in (b'', b'username\nalice', b'\xff', self.sample.splitlines()[0] + b'\n"unfinished'):
            with self.subTest(content=content):
                self.assertEqual(self.upload(content).status_code, 400)

    def test_header_only(self):
        response = self.upload(self.sample.splitlines()[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['alerts'], [])

    def test_size_limit_and_content_type(self):
        self.assertEqual(self.upload(b'x' * (MAX_UPLOAD_BYTES + 1)).status_code, 413)
        response = self.client.post('/api/analyze', json={'path': '/etc/passwd'})
        self.assertEqual(response.status_code, 415)

    def test_stream_size_limit_without_content_length(self):
        response = self.client.post('/api/analyze', content=iter([b'x' * MAX_UPLOAD_BYTES, b'x']),
                                    headers={'Content-Type': 'text/csv'})
        self.assertEqual(response.status_code, 413)

    def test_event_limit(self):
        with patch('backend.app.MAX_EVENTS', 1):
            self.assertEqual(self.upload(self.sample).status_code, 413)

    def test_upload_does_not_open_files(self):
        # MemoryCSV must satisfy the original parser without any disk access.
        with patch('pathlib.Path.open', side_effect=AssertionError('No upload disk writes')):
            self.assertEqual(self.upload(self.sample).status_code, 200)

    def test_underflow_and_huge_windows(self):
        content = b'timestamp,username,source_ip,event_type,status\n0001-01-01T00:00:00Z,a,192.0.2.1,login,failure'
        response = self.upload(content, {'failure_threshold': 1, 'failure_window_minutes': 10**30})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['alerts'][0]['window_start'], '0001-01-01T00:00:00+00:00')

    def test_cors_and_health(self):
        self.assertEqual(self.client.get('/api/health').json(), {'status': 'ok'})
        for origin, expected in (('http://localhost:5173', True), ('https://untrusted.example', False)):
            response = self.client.options('/api/analyze', headers={'Origin': origin, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type'})
            self.assertEqual('access-control-allow-origin' in response.headers, expected)

    def test_production_origins_are_explicit(self):
        for value in ('*', 'https://example.com/path', ''):
            with self.subTest(value=value), patch.dict('os.environ', {'FRONTEND_ORIGINS': value}):
                with self.assertRaises(ValueError):
                    allowed_origins()
        with patch.dict('os.environ', {'FRONTEND_ORIGINS': 'https://portfolio.web.app'}):
            self.assertEqual(allowed_origins(), ['https://portfolio.web.app'])
