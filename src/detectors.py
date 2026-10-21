"""Inclusive sliding windows; emit burst alerts on threshold crossings."""
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from .alerts import Alert
from .log_parser import Event


def window_start(timestamp: datetime, minutes: int) -> datetime:
    """Clamp an unrepresentable lower bound to the earliest supported time.

    No supported event can precede that bound, so retaining all earlier events
    preserves inclusive-window membership even for extremely large windows.
    """
    try:
        return timestamp - timedelta(minutes=minutes)
    except OverflowError:
        return datetime.min.replace(tzinfo=timestamp.tzinfo)


@dataclass(frozen=True)
class DetectionConfig:
    failure_threshold: int = 5
    failure_window_minutes: int = 5
    account_threshold: int = 3
    account_window_minutes: int = 10
    success_failure_threshold: int = 5
    success_window_minutes: int = 10

    def __post_init__(self) -> None:
        if any(type(value) is not int or value < 1 for value in vars(self).values()):
            raise ValueError('All thresholds and window minutes must be positive integers')


def detect(events: list[Event], config: DetectionConfig | None = None) -> list[Alert]:
    config = config or DetectionConfig()
    failures: dict[str, deque[Event]] = defaultdict(deque)
    accounts: dict[str, deque[Event]] = defaultdict(deque)
    pair_failures: dict[tuple[str, str], deque[Event]] = defaultdict(deque)
    alerts: list[Alert] = []

    def trim(window: deque[Event], event: Event, minutes: int) -> None:
        cutoff = window_start(event.timestamp, minutes)
        while window and window[0].timestamp < cutoff:
            window.popleft()

    def emit(rule: str, event: Event, count: int, minutes: int,
             severity: str, explanation: str, username: str = '') -> None:
        alerts.append(Alert(rule, event.source_ip, username, count,
                            window_start(event.timestamp, minutes).isoformat(),
                            event.timestamp.isoformat(), event.timestamp.isoformat(),
                            severity, explanation))

    # Exact duplicate normalized events cannot inflate counts. Stable sorting preserves
    # CSV order when timestamps tie: a failure after a success is not preceding it.
    for event in sorted(dict.fromkeys(events), key=lambda item: item.timestamp):
        account_window = accounts[event.source_ip]
        trim(account_window, event, config.account_window_minutes)
        before = len({item.username for item in account_window})
        account_window.append(event)
        distinct = len({item.username for item in account_window})
        if before < config.account_threshold <= distinct:
            emit('multiple_account_targeting', event, len(account_window),
                 config.account_window_minutes, 'medium',
                 f'{distinct} distinct usernames attempted from one IP; review shared-IP activity')

        pair_window = pair_failures[(event.source_ip, event.username)]
        trim(pair_window, event, config.success_window_minutes)
        if event.status == 'failure':
            failure_window = failures[event.source_ip]
            trim(failure_window, event, config.failure_window_minutes)
            before = len(failure_window)
            failure_window.append(event)
            pair_window.append(event)
            if before < config.failure_threshold <= len(failure_window):
                emit('repeated_failed_logins', event, len(failure_window),
                     config.failure_window_minutes, 'medium',
                     'Failed login burst from one IP; possible guessing or user error')
        elif event.status == 'success':
            if len(pair_window) >= config.success_failure_threshold:
                emit('success_after_failures', event, len(pair_window),
                     config.success_window_minutes, 'high',
                     'Successful login after repeated failures for the same IP and username; investigate',
                     event.username)
            # Failures are consumed by the next success, preventing repeated alerts
            # on subsequent successful logins without new failures.
            pair_window.clear()
    return alerts
