"""Validate synthetic CSV authentication events without exposing raw bad rows."""
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import ip_address
from pathlib import Path

REQUIRED_COLUMNS = ('timestamp', 'username', 'source_ip', 'event_type', 'status')


@dataclass(frozen=True)
class Event:
    timestamp: datetime
    username: str
    source_ip: str
    event_type: str
    status: str


@dataclass
class ParseResult:
    events: list[Event]
    warnings: list[str]
    duplicates: int = 0


def parse_logs(path: Path) -> ParseResult:
    """Skip invalid rows; reject invalid headers. Treat naive timestamps as UTC."""
    result = ParseResult([], [])
    seen: set[Event] = set()
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream, strict=True)
        headers = reader.fieldnames
        if not headers:
            raise ValueError('CSV is empty or has no header')
        if len(set(headers)) != len(headers) or not set(REQUIRED_COLUMNS) <= set(headers):
            raise ValueError('CSV must have unique headers including: ' + ', '.join(REQUIRED_COLUMNS))
        try:
            for row in reader:
                line = reader.line_num
                try:
                    if None in row or any(not row.get(key, '').strip() for key in REQUIRED_COLUMNS):
                        raise ValueError('missing required value or incorrect column count')
                    values = {key: row[key].strip() for key in REQUIRED_COLUMNS}
                    timestamp = datetime.fromisoformat(values['timestamp'].replace('Z', '+00:00'))
                    timestamp = timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)
                    source_ip = str(ip_address(values['source_ip']))
                    if values['event_type'] != 'login':
                        raise ValueError('event_type must be login')
                    if values['status'] not in ('success', 'failure'):
                        raise ValueError('status must be success or failure')
                    event = Event(timestamp, values['username'], source_ip, 'login', values['status'])
                except (ValueError, AttributeError, TypeError):
                    result.warnings.append(f'Line {line}: invalid timestamp, IP, event type, status, or required field; row skipped')
                    continue
                if event in seen:
                    result.duplicates += 1
                    continue
                seen.add(event)
                result.events.append(event)
        except csv.Error as exc:
            # Broken quoting can consume subsequent records; do not guess where they start.
            raise ValueError(f'Malformed CSV near line {reader.line_num}: {exc}') from exc
    result.events.sort(key=lambda event: event.timestamp)
    return result
