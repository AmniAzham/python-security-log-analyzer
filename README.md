# Python Security Log Analyzer

A beginner SOC portfolio project that reads synthetic authentication logs, detects suspicious login patterns with three time-based rules, and exports alerts to CSV. Alerts are investigation leads, not proof of an attack.

## Learning objectives

Practice interpreting authentication events, validating data, applying sliding windows, generating actionable alerts, and checking detection logic with deterministic offline tests. The project uses Python 3, standard-library `csv`, `datetime`, `ipaddress`, `argparse`, and `unittest`; no pandas, external dependencies, network services, or credentials are required.

Authentication logs record a sign-in attempt: its time, account, source address, and outcome. A SOC analyst groups these records to recognize patterns that would be hard to see in individual events.

## Architecture

```text
python-security-log-analyzer/
├── README.md
├── requirements.txt             # Documents the dependency-free runtime
├── .gitignore
├── data/sample_auth_logs.csv    # Fictional, reproducible examples
├── src/
│   ├── __init__.py
│   ├── log_parser.py            # CSV validation, UTC normalization, deduplication
│   ├── detectors.py             # Configuration and three sliding-window rules
│   ├── alerts.py                # Alert record and CSV writer
│   └── main.py                  # Arguments, errors, summary, exit status
└── tests/
    ├── __init__.py
    └── test_detectors.py        # Unit and CLI integration tests
```

The parser produces typed `Event` objects and data-quality warnings. The detector receives those events and returns typed `Alert` objects, without reading or writing files. The CLI connects parsing, detection, and export. Separating these jobs makes each piece easier to explain and test.

## Prerequisites and installation

Python **3.10 or later**. Commands below run from the repository root. No package download is needed.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, use `py -m venv .venv`, then `.venv\Scripts\Activate.ps1` in PowerShell. With the virtual environment active, the remaining `python` commands are the same.

## Run the analyzer and tests

```sh
python -m src.main --input data/sample_auth_logs.csv --output alerts.csv
python -m unittest discover -s tests -v
python -m src.main --help
```

Use an existing output directory. The analyzer overwrites its output CSV; choose a disposable output path. It rejects matching input/output files, including hard links, and aborts if an existing output's identity cannot be safely checked. Generated `alerts.csv` is ignored by Git. Exit status is 0 after a completed analysis, 1 for file/CSV failures, and 2 for invalid CLI arguments. Row warnings do not fail an otherwise readable file; review the skipped-row count before trusting the results. Header-only input is valid and produces a header-only alerts file. A completely empty file fails because its schema cannot be verified.

Thresholds and windows are independently configurable positive integers:

```sh
python -m src.main --failure-threshold 5 --failure-window-minutes 5 --account-threshold 3 --account-window-minutes 10 --success-failure-threshold 5 --success-window-minutes 10
```

These are the defaults. Smaller thresholds increase sensitivity and usually increase false positives.

## Input CSV format

```csv
timestamp,username,source_ip,event_type,status
2026-01-01T00:00:00Z,learner_a,192.0.2.1,login,success
2026-01-01T00:00:30Z,learner_b,192.0.2.2,login,failure
```

All five columns are required and headers must be unique. Extra named columns are ignored. Required values are trimmed. `event_type` must be `login`; `status` must be `success` or `failure` (case-sensitive). Source addresses must be valid IPv4 or IPv6 literals. Timestamps use Python's ISO 8601 parser: explicit offsets are converted to UTC; timestamps without an offset are assumed UTC. Prefer full timestamps with `Z` or an explicit offset to avoid ambiguity. CSV with a UTF-8 BOM is supported.

Missing values, invalid addresses/timestamps/statuses, unsupported event types, and rows with incorrect column counts are skipped with line-numbered warnings. They are **data-quality problems, not attack alerts**. Broken CSV quoting stops processing with an error because the next record boundary may be unknowable. Structurally invalid headers also fail immediately.

Events are sorted chronologically. Exact duplicates of all five normalized fields are removed. Events at the same timestamp retain their original CSV order; a failure listed after a success cannot support that success. Duplicate removal may collapse legitimate identical events when timestamp resolution is coarse; real logs need unique event IDs.

## Detection logic

For each event at time `t`, retain only relevant events in the inclusive interval `[t - window, t]`. For example, a failure at 12:00 is included when examining 12:05 with a five-minute window, but excluded at 12:05:01. This is a sliding window: its edges move with every event. Unlike fixed five-minute buckets, it can detect a burst spanning a bucket boundary.

If a window would begin before Python's earliest supported datetime (year 1), its lower bound is clamped to that earliest time for both filtering and alert output. No supported event can occur before that bound, so relevant events are retained. This also handles configured windows too large to represent as a `timedelta`.

| Rule | Default trigger | Why investigate? | Severity |
| --- | --- | --- | --- |
| `repeated_failed_logins` | At least 5 failures from one IP in 5 minutes, across usernames | Possible password guessing, a broken client, or a forgotten password | Medium: suspicious attempts without evidence of access |
| `multiple_account_targeting` | At least 3 distinct usernames attempted from one IP in 10 minutes; successes and failures both count | Possible account enumeration or broad targeting; shared IP activity can look similar | Medium: breadth of activity without evidence of compromise |
| `success_after_failures` | A success with at least 5 preceding failures for the same IP **and** username in 10 minutes | Possible access following password guessing, or a legitimate user correcting a password | High: access occurred after a suspicious sequence and deserves faster review |

The two burst rules emit one alert on crossing from below threshold to at/above threshold. Continuous above-threshold activity does not emit another alert on every row. A rule can alert again once its active window falls below threshold and activity crosses it again. This suppression reduces noise but does not provide ongoing incident updates.

For the success rule, the failure count excludes the successful event. After each success, the pair's prior failures are cleared, so another success requires new failures before it can alert. That reset does not clear the IP-level failure window. A single sequence can legitimately trigger both repeated failures and a subsequent success alert.

## Expected synthetic results

The sample uses fictional usernames and IPs from documentation-only ranges `192.0.2.0/24`, `198.51.100.0/24`, and `203.0.113.0/24`. No real users or authentication systems are involved.

| Activity | Expected outcome |
| --- | --- |
| Normal logins and isolated failures before 01:00 UTC | No alerts |
| Five failures for `target_a` from `192.0.2.10`, 01:00–01:04 | Repeated failures at 01:04 |
| Three usernames from `198.51.100.20`, 02:00–02:02 | Multiple-account targeting at 02:02 |
| Five failures for `target_b` from `203.0.113.30`, 03:00–03:04 | Repeated failures at 03:04 |
| Success for `target_b` from the same IP at 03:05 | Success after failures at 03:05 |

Verified terminal output:

```text
Processed 19 valid unique events; skipped 0 invalid rows and 0 duplicates.
Generated 4 alerts -> alerts.csv
  multiple_account_targeting: 1
  repeated_failed_logins: 2
  success_after_failures: 1
[MEDIUM] 2026-01-01T01:04:00+00:00 repeated_failed_logins ip=192.0.2.10 user=- events=5
[MEDIUM] 2026-01-01T02:02:00+00:00 multiple_account_targeting ip=198.51.100.20 user=- events=3
[MEDIUM] 2026-01-01T03:04:00+00:00 repeated_failed_logins ip=203.0.113.30 user=- events=5
[HIGH] 2026-01-01T03:05:00+00:00 success_after_failures ip=203.0.113.30 user=target_b events=5
```

Every exported alert contains its rule, source IP, username when applicable, relevant event count, configured window start/end, event-time alert timestamp, severity, and explanation. Example CSV record:

```csv
rule,source_ip,username,event_count,window_start,window_end,alert_timestamp,severity,explanation
success_after_failures,203.0.113.30,target_b,5,2026-01-01T02:55:00+00:00,2026-01-01T03:05:00+00:00,2026-01-01T03:05:00+00:00,high,Successful login after repeated failures for the same IP and username; investigate
```

The window columns describe the configured search interval, not the first and last observed event. For account targeting, `event_count` counts all attempts in the active interval; the explanation separately reports the distinct-username count.

## Testing and review

The offline `unittest` suite checks each rule independently, threshold and inclusive time boundaries, expired events, normal activity, pair isolation, repeated-success suppression, rearming, unsorted events, equal-time ordering, custom configuration, duplicates, timezone normalization, empty input, malformed rows/quoting, sample CSV export, and CLI errors. It invokes the actual CLI as a subprocess as well as testing functions. Tests do not require downloads or external services.

### SOC internship interviewer review

Be ready to explain why an IP alone is not a person: NAT, proxies, corporate gateways, and shared labs can put many legitimate accounts behind one address. A successful login after failures could simply be a password correction. Severity is a triage suggestion, not a verdict.

For an alert, an analyst would check the original records and time range, confirm timestamps and log completeness, identify the affected account and source context, correlate MFA/device/session evidence, compare with the user's normal activity, and check for suspicious actions after the login. Follow the organization's escalation procedure; do not automatically block an IP or disable an account based on this tool alone.

Review identified these deliberate limitations and improvement opportunities:

- This is an in-memory batch analyzer, not a streaming SIEM. It sorts and deduplicates the entire file, retains per-key history, and scans usernames within account windows. Large files need bounded state and incremental processing.
- It does not detect malware, phishing, privilege escalation, stolen sessions, low-and-slow attacks below thresholds, or distributed attacks spread across IPs.
- It lacks account/device context, MFA signals, geolocation, threat intelligence, incident correlation, and persistent state across runs. Rerunning a file repeats its alerts.
- Equal-time records depend on input order, and deduplication lacks authoritative event IDs. Clock skew, ambiguous naive timestamps, and missing logs can change results.
- Accepted input is a simplified synthetic schema, not native Windows, Linux, or cloud-provider logs. Unknown event types are intentionally skipped.
- Arbitrary CSV text is retained in alerts. Use a plain-text CSV viewer for untrusted input; spreadsheet applications may interpret formula-like cells. No spreadsheet sanitization is provided.
- Output writing is not transactional; an I/O failure can leave a partial output. Do not use important existing files as output.

Tests establish the documented synthetic behavior, not detection effectiveness against real adversaries. Useful future tests include large-volume performance, IPv6 normalization cases, property-based boundary checks, and fault-injected output failures.

## What I learned and what I would improve next

Use this as a reflection guide; adjust it to match what you can personally explain:

- Authentication outcomes become useful signals when grouped by IP, account, and time rather than counted across an entire file.
- Sliding-window boundaries, event ordering, and duplicate policy are detection decisions that need explicit tests.
- Data-quality warnings must be separated from security claims.
- A readable alert needs evidence and context, and still requires analyst investigation.
- Separating parsing, detection, and output makes the code easier to maintain and defend in an interview.

Next I would add stable event IDs, provider-specific adapters, streaming with bounded state, configurable rule exclusions based on measured baselines, and analyst feedback to evaluate false positives. I would validate each improvement using synthetic scenarios before considering any authorized real-log use.

## Ethical use

This project is defensive and educational. Use the included fictional data or data you are explicitly authorized to process. Do not collect real credentials or personal information, scan external systems, or perform login attacks. Store any authorized security logs according to your organization's privacy and retention policies.
