"""Stateless API. Raw CSV request bodies avoid multipart disk spooling."""
from collections import defaultdict
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool

from src.detectors import DetectionConfig, detect
from src.log_parser import parse_logs

MAX_UPLOAD_BYTES = 1024 * 1024
MAX_EVENTS = 5000
SAMPLE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'sample_auth_logs.csv'
PositiveInteger = Annotated[int, Field(strict=True, gt=0)]


class RuleSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    failure_threshold: PositiveInteger = 5
    failure_window_minutes: PositiveInteger = 5
    account_threshold: PositiveInteger = 3
    account_window_minutes: PositiveInteger = 10
    success_failure_threshold: PositiveInteger = 5
    success_window_minutes: PositiveInteger = 10


def allowed_origins() -> list[str]:
    origins = os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    cleaned = [origin.strip() for origin in origins if origin.strip()]
    for origin in cleaned:
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError('FRONTEND_ORIGINS must contain exact HTTP(S) origins without paths or credentials')
    if not cleaned:
        raise ValueError('At least one explicit frontend origin is required')
    return cleaned


app = FastAPI(title='Security Log Analyzer API', version='1.0.0')
# Retain exactly the startup settings installed in middleware. Re-reading the
# environment in health() could misleadingly report different active settings.
app.state.cors_origins = allowed_origins()
app.state.revision = os.getenv('RENDER_GIT_COMMIT', 'unknown')
app.add_middleware(CORSMiddleware, allow_origins=app.state.cors_origins,
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type'],
                   allow_credentials=False)


class MemoryCSV:
    """Supply the parser's .open() interface without writing an uploaded file.

    The original parser only needs a text stream, so the CLI stays unchanged.
    """
    def __init__(self, text: str):
        self.text = text

    def open(self, **_kwargs) -> io.StringIO:
        return io.StringIO(self.text, newline='')


def settings_from_query(config: str) -> RuleSettings:
    try:
        return RuleSettings.model_validate(json.loads(config))
    except (ValueError, ValidationError, RecursionError):
        # Do not echo invalid configuration values into an error response.
        raise HTTPException(422, 'Rule settings must be a JSON object with known positive integer fields') from None


def analyze_bytes(content: bytes, settings: RuleSettings) -> dict:
    try:
        text = content.decode('utf-8-sig')
        result = parse_logs(MemoryCSV(text))
    except (UnicodeError, ValueError, OverflowError):
        raise HTTPException(400, 'Invalid CSV: use UTF-8, unique required headers, and properly quoted rows') from None
    if len(result.events) > MAX_EVENTS:
        raise HTTPException(413, f'Limit is {MAX_EVENTS} valid unique events per analysis')
    alerts = detect(result.events, DetectionConfig(**settings.model_dump()))
    activity = defaultdict(lambda: {'success': 0, 'failure': 0})
    for event in result.events:
        hour = event.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        activity[hour][event.status] += 1
    return {
        'events_analyzed': len(result.events), 'total_alerts': len(alerts),
        'invalid_rows': len(result.warnings), 'duplicates': result.duplicates,
        'warnings': result.warnings, 'alerts': [asdict(alert) for alert in alerts],
        'activity': [{'timestamp': timestamp, **counts} for timestamp, counts in sorted(activity.items())],
        'config': settings.model_dump(),
    }


@app.get('/api/health')
def health(details: bool = False) -> dict:
    result = {'status': 'ok'}
    if details:
        # These are public deployment identifiers, never credentials or CSV data.
        result.update(revision=app.state.revision, cors_origins=app.state.cors_origins)
    return result


@app.post('/api/analyze')
async def analyze(request: Request, config: str = Query(default='{}', max_length=2048)) -> dict:
    settings = settings_from_query(config)
    content_type = request.headers.get('content-type', '').split(';')[0].strip().lower()
    if content_type not in ('text/csv', 'text/plain', 'application/octet-stream'):
        raise HTTPException(415, 'Send CSV bytes with Content-Type: text/csv (not multipart form data)')
    # Bound the actual stream, not only the untrusted Content-Length header.
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, 'CSV upload exceeds the 1 MiB limit')
        content.extend(chunk)
    return await run_in_threadpool(analyze_bytes, bytes(content), settings)


@app.post('/api/sample')
async def sample(config: str = Query(default='{}', max_length=2048)) -> dict:
    settings = settings_from_query(config)
    # This fixed repository path is never taken from client input.
    return await run_in_threadpool(analyze_bytes, SAMPLE_PATH.read_bytes(), settings)
