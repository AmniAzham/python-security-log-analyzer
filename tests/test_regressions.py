"""Regression coverage for output aliases and datetime range boundaries."""
import contextlib
from datetime import datetime, timedelta, timezone
import errno
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.detectors import DetectionConfig, detect
from src.log_parser import Event
from src.main import main


def event(seconds=0, username='alice', status='failure'):
    return Event(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds),
                 username, '192.0.2.10', 'login', status)


class OutputProtectionTests(unittest.TestCase):
    def run_analyzer(self, source, output):
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = main(['--input', str(source), '--output', str(output)])
        return code, stderr.getvalue()

    def make_input(self, directory):
        source = Path(directory) / 'input.csv'
        source.write_bytes(Path('data/sample_auth_logs.csv').read_bytes())
        return source

    def test_hard_link_output_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_input(directory)
            output = Path(directory) / 'alias.csv'
            try:
                os.link(source, output)
            except NotImplementedError:
                self.skipTest('Hard links are not implemented on this platform')
            except OSError as exc:
                unsupported = {errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}
                if exc.errno in unsupported or getattr(exc, 'winerror', None) in (1, 50):
                    self.skipTest(f'Hard links are unsupported: {exc}')
                raise
            before = source.read_bytes()
            code, message = self.run_analyzer(source, output)
            self.assertEqual(code, 1)
            self.assertIn('same file', message)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(output.read_bytes(), before)

    def test_identical_path_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_input(directory)
            before = source.read_bytes()
            code, message = self.run_analyzer(source, source)
            self.assertEqual(code, 1)
            self.assertIn('same file', message)
            self.assertEqual(source.read_bytes(), before)

    def test_missing_output_and_distinct_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_input(directory)
            before = source.read_bytes()
            output = Path(directory) / 'output.csv'
            for existing in (False, True):
                with self.subTest(existing=existing):
                    code, message = self.run_analyzer(source, output)
                    self.assertEqual(code, 0, message)
                    self.assertTrue(output.read_text().startswith('rule,'))
                    self.assertEqual(source.read_bytes(), before)

    def test_identity_check_errors_fail_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_input(directory)
            output = Path(directory) / 'output.csv'
            output.write_bytes(b'keep existing output')
            before = source.read_bytes()
            for error in (PermissionError('access denied'), OSError('unsupported file identity'),
                          NotImplementedError('file identity is unavailable')):
                with self.subTest(error=error), patch('src.main.os.path.samefile', side_effect=error):
                    code, message = self.run_analyzer(source, output)
                    self.assertEqual(code, 1)
                    self.assertIn('Cannot safely compare', message)
                    self.assertEqual(output.read_bytes(), b'keep existing output')
                    self.assertEqual(source.read_bytes(), before)


class DatetimeBoundaryTests(unittest.TestCase):
    earliest = datetime.min.replace(tzinfo=timezone.utc)

    def early_event(self, seconds=0, username='alice', status='failure'):
        original = event(seconds, username=username, status=status)
        return type(original)(self.earliest + timedelta(seconds=seconds), original.username,
                              original.source_ip, original.event_type, original.status)

    def test_earliest_datetime_can_trigger_alerts(self):
        config = DetectionConfig(failure_threshold=1, account_threshold=1)
        alerts = detect([self.early_event()], config)
        self.assertEqual({alert.rule for alert in alerts},
                         {'repeated_failed_logins', 'multiple_account_targeting'})
        for alert in alerts:
            self.assertEqual(alert.window_start, self.earliest.isoformat())
            self.assertEqual(alert.alert_timestamp, self.earliest.isoformat())
            self.assertEqual(alert.event_count, 1)

    def test_all_rules_keep_relevant_events_when_window_underflows(self):
        events = [self.early_event(i) for i in range(5)]
        events += [self.early_event(5, status='success'),
                   self.early_event(6, username='bob'), self.early_event(7, username='carol')]
        alerts = detect(events)
        self.assertEqual({alert.rule: alert.event_count for alert in alerts}, {
            'repeated_failed_logins': 5, 'success_after_failures': 5,
            'multiple_account_targeting': 8})
        for alert in alerts:
            self.assertEqual(alert.window_start, self.earliest.isoformat())

    def test_early_datetime_still_expires_old_events_at_boundary(self):
        for seconds, expected in ((600, 1), (601, 0)):
            with self.subTest(seconds=seconds):
                events = [self.early_event(i) for i in range(5)]
                events.append(self.early_event(seconds, status='success'))
                alerts = [alert for alert in detect(events) if alert.rule == 'success_after_failures']
                self.assertEqual(len(alerts), expected)

    def test_window_larger_than_timedelta_range(self):
        config = DetectionConfig(failure_window_minutes=10**30,
                                 account_window_minutes=10**30,
                                 success_window_minutes=10**30)
        events = [event(i) for i in range(5)] + [event(5, status='success'),
                  event(6, username='bob'), event(7, username='carol')]
        alerts = detect(events, config)
        self.assertEqual(len(alerts), 3)
        self.assertTrue(all(alert.window_start == self.earliest.isoformat() for alert in alerts))

    def test_earliest_timestamp_through_csv_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'early.csv'
            source.write_text('timestamp,username,source_ip,event_type,status\n'
                              '0001-01-01T00:00:00Z,alice,192.0.2.1,login,success\n')
            output = Path(directory) / 'alerts.csv'
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = main(['--input', str(source), '--output', str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(len(output.read_text().splitlines()), 1)
