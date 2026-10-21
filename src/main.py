"""Run from the repository root: python -m src.main --help."""
import argparse
from collections import Counter
import os
from pathlib import Path
import sys

from .alerts import write_alerts
from .detectors import DetectionConfig, detect
from .log_parser import parse_logs


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def ensure_distinct_files(input_path: Path, output_path: Path) -> None:
    """Fail closed if an existing output's identity cannot be checked."""
    if input_path.resolve() == output_path.resolve():
        raise ValueError('Input and output must not refer to the same file')
    try:
        output_path.stat()
    except FileNotFoundError:
        # A new output has no file identity to compare yet.
        return
    except OSError as exc:
        raise ValueError(f'Cannot safely check output file identity: {exc}') from exc
    try:
        same_file = os.path.samefile(input_path, output_path)
    except (OSError, NotImplementedError) as exc:
        raise ValueError(f'Cannot safely compare input and output files: {exc}') from exc
    if same_file:
        raise ValueError('Input and output must not refer to the same file (including hard links)')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Analyze synthetic authentication CSV logs.')
    parser.add_argument('--input', type=Path, default=Path('data/sample_auth_logs.csv'))
    parser.add_argument('--output', type=Path, default=Path('alerts.csv'))
    for name, default in vars(DetectionConfig()).items():
        parser.add_argument('--' + name.replace('_', '-'), type=positive_int, default=default)
    args = parser.parse_args(argv)
    try:
        result = parse_logs(args.input)
        config = DetectionConfig(**{name: getattr(args, name) for name in vars(DetectionConfig())})
        alerts = detect(result.events, config)
        ensure_distinct_files(args.input, args.output)
        write_alerts(args.output, alerts)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    for warning in result.warnings:
        print(f'Warning: {warning}', file=sys.stderr)
    print(f'Processed {len(result.events)} valid unique events; skipped {len(result.warnings)} invalid rows and {result.duplicates} duplicates.')
    print(f'Generated {len(alerts)} alerts -> {args.output}')
    for rule, count in sorted(Counter(alert.rule for alert in alerts).items()):
        print(f'  {rule}: {count}')
    for alert in alerts:
        print(f'[{alert.severity.upper()}] {alert.alert_timestamp} {alert.rule} ip={alert.source_ip} user={alert.username or "-"} events={alert.event_count}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
