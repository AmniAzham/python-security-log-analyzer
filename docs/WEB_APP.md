# Web application guide

This first web version adds a React interface and FastAPI adapter around the original Python analyzer. It does not replace the CLI or detection rules.

## Stage 1: understand the parts

```text
Browser: React + Vite
  ├─ CSV file or fictional sample selection
  ├─ rule settings and filters
  └─ charts, alert details, and local CSV export
           │ HTTP request / JSON response
           ▼
Python: backend/app.py (FastAPI)
  ├─ validates settings, upload size, and media type
  ├─ parses CSV bytes in memory
  └─ calls src/log_parser.py → src/detectors.py → src/alerts.py records
```

The browser never implements detections. The same Python functions power CLI and API results. The original `src/` files and original tests are unchanged.

| Location | Responsibility |
| --- | --- |
| `src/` | Existing Python parser, detector, alert model/writer, and CLI |
| `backend/app.py` | HTTP interface, CORS, limits, memory-only upload adapter, JSON results |
| `backend/requirements.txt` | Pinned direct API and API-test dependencies |
| `frontend/src/App.jsx` | Navigation and shared analysis/settings state |
| `frontend/src/components/` | Upload, charts, alerts/details, rules, and About components |
| `frontend/src/api.js` | Browser-to-API requests and helpful errors |
| `frontend/src/lib.js` | File/settings validation, filters, CSV serialization |
| `frontend/src/styles.css` | Responsive navy dashboard, focus indicators, charts |
| `frontend/tests/` | Offline JavaScript utility tests using Node's test runner |
| `frontend/e2e/` | Browser tests against a running local frontend and API |
| `tests/test_backend.py` | In-process API endpoint and validation tests |
| `firebase.json` | Static frontend hosting and SPA fallback; no Python hosting |

## Stage 2: run locally on Windows

Install Python 3.10+ and Node.js 24 LTS (which includes npm). Open PowerShell in the repository root, the folder containing `README.md`. No Firebase account is needed locally. Keep both terminals running.

**Terminal 1 — Python API:**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

**Terminal 2 — React frontend, starting in the repository root:**

```powershell
cd frontend
npm ci
npm run dev
```

Open the local address printed by Vite in your own browser. The frontend defaults to port 5173 and calls the API on port 8000. Select **Load sample data**. Expect 19 events, 4 alerts, 0 invalid rows, and 0 duplicates.

`Ctrl+C` stops each server. These commands do not deploy anything. No virtual environment activation or PowerShell execution-policy change is needed. If Windows blocks `npm.ps1`, run `npm.cmd ci` and `npm.cmd run dev` instead.

If the API uses another address, copy `frontend/.env.example` to `frontend/.env.local`, change `VITE_API_BASE_URL`, and restart Vite. This address is public configuration, not a secret. To change the frontend origin, configure the API allowlist before starting it:

```powershell
$env:FRONTEND_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
```

Do not add `*`. Origins have a scheme and optional port, with no path or trailing slash. Both programs need restarting when their startup configuration changes. If a port is occupied, stop your old process or deliberately choose another port and update both sides accordingly.

## Stage 3: learn React from this project

A **component** is a function that returns a piece of the interface. `Charts`, `UploadPanel`, `Alerts`, and `RuleSettings` keep the dashboard understandable. Each lives in its own file under `frontend/src/components/`. `App.jsx` connects them and owns the shared analysis state.

**Props** are inputs supplied by a parent component. For example, `<Charts result={result} />` gives `Charts` the current API response. Child components receive data rather than fetching their own competing copies.

**State** is data React remembers between renders. `useState` in `App` stores the current page, saved rule settings, loading status, errors, and analysis result. The alert table has its own severity/rule filter state. `RuleSettings` keeps a draft separately, so typing into a box does not change the active settings until **Apply rules** is selected.

An **event handler** runs after an interaction. Clicking **Load sample data** calls `run(true)`. Choosing a CSV validates its name and size. Applying rules validates positive safe integers and sends numbers, not numeric strings. Server validation remains authoritative; browser validation is only convenient feedback.

An **API request** sends work to Python. `api.js` uses `fetch()` with POST. An upload sends raw CSV bytes, not a local path and not multipart form data. The API responds with JSON; `setResult` stores that response, and React redraws cards, charts, and the alert table. New requests clear old results first so errors cannot leave a misleading old success on screen.

Filters only change displayed alerts. They do not rerun detection or change the overview counts. **Export all alerts** exports the full current result, including alerts hidden by filters. Opening **Review** displays the exact search window and investigation guidance. Navigation preserves analysis results; **Clear results** or reloading clears them. Settings are session-only and reset on reload.

The charts use CSS bars and accessible text labels, without a chart-library dependency. Hourly activity uses valid unique events and UTC buckets; missing hours are not drawn as empty buckets. Read each bar's full date/time label rather than assuming equal spacing between observed hours.

## Stage 4: understand the API and privacy limits

- `GET /api/health`: readiness response `{"status":"ok"}`.
- `POST /api/sample`: analyze the fixed fictional sample shipped in `data/`.
- `POST /api/analyze`: analyze raw UTF-8 CSV bytes with `Content-Type: text/csv`. No filenames or filesystem paths are accepted as input locations.
- Both analysis endpoints accept an optional `config` query parameter containing a JSON object. Omitted fields use defaults; unknown fields, booleans, decimals, zero, negatives, and numeric strings are rejected. Example: `{"failure_threshold":6}`.
- JSON includes `events_analyzed`, `total_alerts`, `invalid_rows`, `duplicates`, `warnings`, `alerts`, hourly `activity`, and the actual `config` used.
- Status 400: bad encoding, headers, or broken CSV structure. Status 413: upload over 1 MiB or more than 5,000 valid unique events. Status 415: unsupported media type. Status 422: invalid settings. Invalid individual rows generate warnings rather than security alerts.

The upload endpoint reads a bounded request stream into memory. `MemoryCSV` provides the existing parser's `.open()` interface using `StringIO`; it never writes raw uploads to a temporary file. No multipart parser is used, avoiding automatic upload spooling. Original alert dataclasses are converted to JSON; the existing CLI writer stays unchanged. CSV export happens in the browser and prefixes formula-like cells for spreadsheet safety. The original CLI export retains its original behavior.

No database, Firestore, login, analytics, or server-side upload/result history is implemented. The API has no password or API-key requirement. Do not upload credentials or personal data. CORS restricts which browser origins can read responses; it does not prevent direct API calls. Public hosting needs infrastructure request-size limits, rate/concurrency limits, HTTPS, request timeouts, and controlled logging. This first version is intended for small educational analyses, not production SOC ingestion. A byte limit bounds parsing but does not replace service-level resource controls.

`--no-access-log` avoids request access logs in the documented server command. Never enable request-body logging in a reverse proxy or hosting provider. Infrastructure may still retain request metadata: review its policy before using any authorized sensitive data. Inputs and results exist in process memory while being processed; this is not a guarantee of cryptographic memory erasure.

`.env*`, `.venv`, `node_modules`, build outputs, Firebase local state, and common service-account filenames are ignored. `.env.example` is a safe public template. Never put secrets in `VITE_*`: Vite embeds those values in downloadable JavaScript. Never commit service-account credentials.

## Stage 5: automated and manual verification

From the repository root, with API dependencies installed:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m src.main --input data/sample_auth_logs.csv --output alerts.csv
```

The full Python suite includes the original 28 tests and 13 API tests. The core CLI remains dependency-free; if you only want its tests, use `python -m unittest tests.test_detectors tests.test_regressions -v` without installing backend packages.

From `frontend/`:

```powershell
npm test
npm run build
```

For optional real-browser checks, keep the frontend and API running in the first two terminals, then use a third terminal in `frontend/`:

```powershell
npx playwright install chromium
npm run test:e2e
```

Browser installation needs Internet access once. After that, these tests use only local services and fictional data. The test suite covers sample results, charts, filters, alert details, CSV downloads, rule changes, uploads, warnings, empty/error/loading states, and mobile navigation. On machines with a managed Chromium installation, `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` can point to that executable instead.

Manual checklist:

- Load sample data: cards show **19 / 4 / 0 / 0** and four alert rows.
- Check activity bars and rule counts: repeated failures **2**, account targeting **1**, success after failures **1**.
- Filter High: only the success-after-failures alert remains. Combine with another rule: a clear empty state appears.
- Select Review: confirm IP, username, event count, severity, window, and explanation. Close the details.
- Export all alerts: CSV has a header and four records even when the table is filtered.
- On Detection rules, try zero or a decimal: applying is blocked. Apply thresholds **6 / 4 / 6**, return to Overview, and load sample again: **19 events / 0 alerts**. Previous results keep their original settings until reanalysis.
- Restore defaults, select Apply rules, and reanalyze: four alerts return.
- Upload `data/sample_auth_logs.csv`: matches the sample button. Try a header-only CSV: zero events without a crash.
- Upload a duplicate and an invalid timestamp: inspect duplicate/invalid-row counts and warning messages.
- Try a `.txt`, empty, oversized, or structurally broken file: useful feedback appears.
- Stop the API and retry: a connection error appears and old results are cleared.
- Use keyboard Tab/Enter and a narrow mobile window. Navigation, upload, filters, and details remain usable; wide tables scroll within their panel.
- Clear results: no alerts remain visible. Refresh: saved settings reset to defaults.

## Stage 6: deployment preparation (not deployed)

Firebase Hosting serves **only the static React build**. It cannot run this Python backend. No Firebase SDK, service account, Firestore, or user authentication is needed for this version.

Deploy the Python service separately to a provider that supports a Python ASGI app (for example Cloud Run or a managed Python web service). Configure its repository root as the working directory, include `backend/`, `src/`, and `data/sample_auth_logs.csv`, install `backend/requirements.txt`, and start `uvicorn backend.app:app --host 0.0.0.0 --port <provider-port> --no-access-log`. Replace the port placeholder according to your provider's instructions. Set `FRONTEND_ORIGINS` to your **exact** hosting origins, for example `https://YOUR_PROJECT_ID.web.app,https://YOUR_PROJECT_ID.firebaseapp.com`. Add any custom frontend domain explicitly. Use HTTPS.

After obtaining the API's public HTTPS URL, set it before building the frontend. From PowerShell in the repository root:

```powershell
$env:VITE_API_BASE_URL = "https://YOUR_API_HOST"
npm --prefix frontend ci
npm --prefix frontend run build
```

`firebase.json` points to `frontend/dist`, adds an SPA fallback, and sets basic response headers. It deliberately has no Python rewrite or database configuration. You do not need to run `firebase init`, which could overwrite the supplied configuration.

**When you choose to deploy**, authenticate your own Firebase CLI and select your own project. These commands are documentation only; nothing has been deployed by this task:

```powershell
npx --yes --package firebase-tools firebase login
npx --yes --package firebase-tools firebase deploy --only hosting --project YOUR_PROJECT_ID
```

Replace `YOUR_PROJECT_ID` first. No project identifier or credential is supplied by this repository. A frontend build is not a deployment, and local checks do not prove the deployed CORS, TLS, hosting, or API configuration works. After an authorized deployment, test the deployed sample request and browser workflow again. Changing `VITE_API_BASE_URL` requires a new build; changing `FRONTEND_ORIGINS` requires restarting/redeploying the API.
