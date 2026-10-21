"""Alert records and portable CSV output."""
import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class Alert:
    rule: str
    source_ip: str
    username: str
    event_count: int
    window_start: str
    window_end: str
    alert_timestamp: str
    severity: str
    explanation: str


def write_alerts(path: Path, alerts: list[Alert]) -> None:
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=[field.name for field in fields(Alert)])
        writer.writeheader()
        writer.writerows(asdict(alert) for alert in alerts)
