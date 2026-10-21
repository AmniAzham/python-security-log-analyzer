import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.detectors import DetectionConfig, detect
from src.log_parser import Event, parse_logs

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def event(seconds=0, username='alice', source_ip='192.0.2.10', status='failure'):
    return Event(BASE + timedelta(seconds=seconds), username, source_ip, 'login', status)


def rule(events, name, config=None):
    return [alert for alert in detect(events, config) if alert.rule == name]


class DetectionTests(unittest.TestCase):
    def test_failure_threshold_and_count(self):
        self.assertEqual(rule([event(i) for i in range(4)], 'repeated_failed_logins'), [])
        alerts = rule([event(i) for i in range(6)], 'repeated_failed_logins')
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].event_count, 5)
        self.assertEqual(alerts[0].severity, 'medium')

    def test_failure_window_inclusive(self):
        self.assertEqual(len(rule([event(i) for i in (0, 1, 2, 3, 300)], 'repeated_failed_logins')), 1)
        self.assertEqual(rule([event(i) for i in (0, 1, 2, 3, 301)], 'repeated_failed_logins'), [])

    def test_account_threshold(self):
        self.assertEqual(rule([event(i, name) for i, name in enumerate(('a', 'b', 'a'))], 'multiple_account_targeting'), [])
        alerts = rule([event(i, name, status='success') for i, name in enumerate(('a', 'b', 'c'))], 'multiple_account_targeting')
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].event_count, 3)

    def test_account_window(self):
        for last, count in ((600, 1), (601, 0)):
            with self.subTest(last=last):
                self.assertEqual(len(rule([event(0, 'a'), event(1, 'b'), event(last, 'c')], 'multiple_account_targeting')), count)

    def test_success_threshold_and_window(self):
        for last, count in ((600, 1), (601, 0)):
            with self.subTest(last=last):
                alerts = rule([event(i) for i in range(5)] + [event(last, status='success')], 'success_after_failures')
                self.assertEqual(len(alerts), count)
                if alerts:
                    self.assertEqual(alerts[0].username, 'alice')
                    self.assertEqual(alerts[0].event_count, 5)
                    self.assertEqual(alerts[0].severity, 'high')
        self.assertEqual(rule([event(i) for i in range(4)] + [event(5, status='success')], 'success_after_failures'), [])

    def test_success_requires_same_pair(self):
        failures = [event(i) for i in range(5)]
        for success in (event(6, username='bob', status='success'), event(6, source_ip='192.0.2.11', status='success')):
            self.assertEqual(rule(failures + [success], 'success_after_failures'), [])

    def test_success_consumes_failures(self):
        events = [event(i) for i in range(5)] + [event(5, status='success'), event(6, status='success')]
        self.assertEqual(len(rule(events, 'success_after_failures')), 1)

    def test_duplicates_do_not_inflate_counts(self):
        self.assertEqual(detect([event()] * 20), [])

    def test_normal_activity(self):
        self.assertEqual(detect([event(0, status='success'), event(100), event(1000)]), [])
        self.assertEqual(detect([]), [])

    def test_unsorted_events(self):
        events = [event(i) for i in range(5)] + [event(5, status='success')]
        self.assertEqual(detect(events), detect(list(reversed(events))))

    def test_equal_timestamps_preserve_input_order(self):
        failures = [event(i, source_ip='192.0.2.10') for i in range(5)]
        self.assertEqual(len(rule(failures + [event(4, status='success')], 'success_after_failures')), 1)
        self.assertEqual(rule(failures[:4] + [event(4, status='success'), failures[4]], 'success_after_failures'), [])

    def test_burst_can_rearm_after_quiet_period(self):
        self.assertEqual(len(rule([event(i) for i in range(5)] + [event(1000+i) for i in range(5)], 'repeated_failed_logins')), 2)

    def test_custom_configuration(self):
        config = DetectionConfig(failure_threshold=2, failure_window_minutes=1)
        self.assertEqual(len(rule([event(0), event(60)], 'repeated_failed_logins', config)), 1)
        self.assertEqual(rule([event(0), event(61)], 'repeated_failed_logins', config), [])
        with self.assertRaises(ValueError):
            DetectionConfig(account_threshold=0)


class ParserTests(unittest.TestCase):
    def parse(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'logs.csv'
            path.write_text(content, encoding='utf-8')
            return parse_logs(path)

    header = 'timestamp,username,source_ip,event_type,status\n'

    def test_empty_and_missing_or_duplicate_headers(self):
        for content in ('', 'timestamp,username\n', self.header.replace('status', 'username')):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.parse(content)
        self.assertEqual(self.parse(self.header).events, [])

    def test_invalid_rows_are_skipped(self):
        rows = [
            'bad,alice,192.0.2.10,login,failure',
            '2026-01-01T00:00:00Z,,192.0.2.10,login,failure',
            '2026-01-01T00:00:00Z,alice,invalid,login,failure',
            '2026-01-01T00:00:00Z,alice,192.0.2.10,login,unknown',
            '2026-01-01T00:00:00Z,alice,192.0.2.10,logout,failure',
            '2026-01-01T00:00:00Z,alice',
            '2026-01-01T00:00:00Z,alice,192.0.2.10,login,failure,extra',
            '2026-01-01T00:00:00Z,alice,192.0.2.10,login,success',
        ]
        result = self.parse(self.header + '\n'.join(rows))
        self.assertEqual(len(result.warnings), 7)
        self.assertEqual(len(result.events), 1)

    def test_normalization_and_duplicates(self):
        rows = ['2026-01-01T00:00:00Z,alice,192.0.2.10,login,failure',
                '2026-01-01T08:00:00+08:00,alice,192.0.2.10,login,failure',
                '2026-01-01T00:00:00,alice,192.0.2.10,login,failure']
        result = self.parse(self.header + '\n'.join(rows))
        self.assertEqual(result.events, [event()])
        self.assertEqual(result.duplicates, 2)

    def test_broken_quoting(self):
        with self.assertRaisesRegex(ValueError, 'Malformed CSV'):
            self.parse(self.header + '"unfinished')


class IntegrationTests(unittest.TestCase):
    def test_sample_and_csv_export(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'alerts.csv'
            completed = subprocess.run([sys.executable, '-m', 'src.main', '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn('Processed 19 valid unique events', completed.stdout)
            self.assertIn('Generated 4 alerts', completed.stdout)
            with output.open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 4)
            self.assertEqual([row['rule'] for row in rows].count('repeated_failed_logins'), 2)
            self.assertEqual({row['source_ip'] for row in rows}, {'192.0.2.10', '198.51.100.20', '203.0.113.30'})

    def test_cli_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            for arguments in (['--input', str(Path(directory) / 'missing.csv')],
                              ['--input', 'data/sample_auth_logs.csv', '--output', 'data/sample_auth_logs.csv'],
                              ['--failure-threshold', '0'],
                              ['--output', str(Path(directory) / 'missing' / 'alerts.csv')]):
                with self.subTest(arguments=arguments):
                    completed = subprocess.run([sys.executable, '-m', 'src.main', *arguments], capture_output=True, text=True)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn('error', completed.stderr.lower())


if __name__ == '__main__':
    unittest.main()
