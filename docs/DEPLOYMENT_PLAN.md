# AuthWatch free-tier deployment plan — preparation only

## Recommended architecture

Use Firebase **Hosting** for the React static build and Render for the existing FastAPI backend. Keep Python, the CLI, and all three detection rules. No database, Firestore, Firebase SDK, login system, custom domain, or service-account key is needed.

Visitors open the Firebase HTTPS URL. The browser sends CSV bytes or a sample-analysis request to the Render HTTPS API. Python returns events, warnings, duplicates, activity buckets, settings, and alerts. Filtering and CSV export run in the browser.

Two hosting services are necessary because Firebase static Hosting cannot execute this Python API. The Python service must ship `backend/`, `src/`, and `data/sample_auth_logs.csv`, with the repository root as its working directory.

## Selected free-tier configuration and limits

**Selected setup: Firebase Spark + Render Free only.** No services have been created or deployed by this preparation. No account creation, billing activation, paid resources, commits, pushes, or deployment are authorized in this preparation step. The frontend uses Firebase's Spark/no-cost Hosting plan. Standard static Hosting does not require upgrading to Blaze just to serve these assets. An existing Firebase project may already have billing enabled; check its actual plan before using it.

This workspace's network proxy returned HTTP 403 for provider documentation requests, so the following figures are planning estimates from previously published terms, **not verified current prices**. Check the linked official pages and the creation screen before approving any resource.

| Component | Planning estimate | Limitation / billing consequence |
| --- | --- | --- |
| Firebase Hosting, Spark | No cost within quota; historically 10 GB storage and 360 MB/day transfer | Quota exhaustion can suspend serving/deploys until reset or remediation. Spark does not automatically become an unrestricted paid plan. Hosting overages are billable on Blaze. |
| Render Free Python web service | No instance charge; historically 750 instance-hours/workspace/month | Sleeps after about 15 minutes without traffic; waking can take roughly a minute. Workspace hours, bandwidth, and build allowances are shared/limited. Exhaustion can suspend service or restrict builds. Free availability/account verification is provider-dependent. |

Sources to review before approval:

- https://firebase.google.com/pricing
- https://firebase.google.com/docs/hosting/usage-quotas-pricing
- https://render.com/pricing
- https://render.com/docs/free

**Chosen plan:** Firebase Spark + Render Free, accepting cold starts. No paid fallback is authorized. If a free resource is unavailable, stop and report the limitation rather than selecting a paid option.

Do not enable paid tiers, billing accounts, add-ons, paid workspaces, custom domains, or autoscaling merely to finish setup. If either provider requires a payment method, quota upgrade, or verification, stop and review the exact requirement first. Budget alerts are notifications, not hard spending limits. Do not use artificial uptime pings to evade free-tier sleep.

## What is prepared in the repository

- Existing `firebase.json`: `frontend/dist` only, SPA fallback, and basic response headers. It does not run or proxy Python.
- New `render.yaml`: Python service, the `authwatch-web-app` branch, fixed Python version, dependency installation, full Python tests during builds, health endpoint, and a bounded Uvicorn concurrency setting. `plan: free` is the default; `autoDeploy: false` prevents routine automatic redeployment. Importing a Blueprint still creates/deploys a service, so do not import before approval. Render's live schema/account options must be checked at creation time; the YAML has not been validated against Render's API.
- New `scripts/build_web.py`: installs locked frontend packages, runs frontend utility tests, builds with an explicitly supplied public HTTPS API origin, and verifies the origin appears in the bundle. It cannot create resources or deploy. This prevents accidentally publishing a build that calls a visitor's localhost.
- Existing API: raw CSV bytes are processed in memory, with a 1 MiB upload limit, 5,000 valid unique-event limit, strict settings, explicit-origin CORS, and no database.

These preparation changes remain local until the owner approves committing/pushing them. They do not change the original analyzer.

## Exact sequence after future deployment approval

For the current review, do not run the resource-creation or deploy steps below. Commit and push of these preparation files also require separate approval.

### 1. Owner authorizes the plan and connects accounts

After separate authorization for account/resource setup, confirm Firebase Spark and Render Free are available, without enabling billing or selecting paid add-ons. Sign in to Firebase with your Google account and Render with your own account. Do not paste passwords, tokens, or service-account files into chat.

This Codex session has Git access, but no authenticated Firebase/Render deployment connector or interactive browser tool is available. Provider account creation, billing checks, GitHub authorization for Render, and OAuth approval must be completed by the owner in the provider UI. We can prepare files, build/test the app, and guide deployment from returned non-secret project identifiers and URLs. A browser-based Cloud Shell is an option for Firebase commands, so Windows local development is not required.

### 2. Select/create the Firebase project only after approval

In Firebase Console, select an appropriate existing project or use **Add project**. A project name is not the project ID; record the actual ID from Project settings. Keep the Spark plan and omit optional Analytics for this application. Do not enable App Hosting, Functions, Firestore, or authentication.

The intended default frontend origins will be:

```text
https://YOUR_PROJECT_ID.web.app
https://YOUR_PROJECT_ID.firebaseapp.com
```

Confirm the actual default Hosting site ID in the console: if it differs from the project ID, use that site's domains instead. The UI's final site URL is authoritative. The owner's actual Firebase domain and Render URL have not been supplied yet, so the values in this document are placeholders, not configured live domains. A new project's creation and any required account terms are owner actions, not something this preparation has performed.

### 3. Create the Render backend only after approval

The simplest UI route is **New → Web Service**, connect the existing GitHub repository, then use:

```text
Repository: AmniAzham/python-security-log-analyzer
Branch: authwatch-web-app
Runtime: Python
Root directory: leave blank (repository root)
Build command: python -m pip install -r backend/requirements.txt && python -m unittest discover -s tests -v
Start command: python -m uvicorn backend.app:app --host 0.0.0.0 --port $PORT --no-access-log --limit-concurrency 8 --timeout-keep-alive 5
Health-check path: /api/health
Auto deploy: disabled/manual
Instance: Free only (no disk or paid add-ons)
```

Set these non-secret environment variables:

```text
PYTHON_VERSION=3.12.14
FRONTEND_ORIGINS=https://YOUR_HOSTING_SITE.web.app,https://YOUR_HOSTING_SITE.firebaseapp.com
```

Use exact origins without trailing slashes. Never set `FRONTEND_ORIGINS=*`. Render supplies `PORT`; do not hardcode a local port. Choose a nearby available region shown in the console; do not assume every region supports the selected plan.

Alternatively, after the configuration files are approved and pushed, import `render.yaml` as a Blueprint. Confirm the instance is Free and manually supply `FRONTEND_ORIGINS` before applying it. Do not create both the manual and Blueprint services.

Wait for a successful deployment. Record the actual assigned HTTPS address. A proposed service name is not a guaranteed URL.

### 4. Verify the live API before building the frontend

Request `GET https://ACTUAL_API_HOST/api/health`: expect `{"status":"ok"}`. Then request `POST https://ACTUAL_API_HOST/api/sample`: expect 19 events, four alerts, no warnings, and no duplicates. Check custom thresholds 6 / 4 / 6 return zero alerts. Use only the fictional repository CSV to check uploads.

A health-check response alone does not demonstrate analysis works. If a free instance is asleep, allow it to wake and check the actual response. Do not declare the application deployed successfully until analysis requests pass.

### 5. Build the React app with the real API URL

From the repository root in an environment with Python and Node 24 LTS:

```sh
python scripts/build_web.py --api-url https://ACTUAL_API_HOST
```

Replace the placeholder with the actual Render origin. In PowerShell, use `py` instead of `python` if needed. In this Codex environment we can do this build once you provide the non-secret live API URL. This is a build, not a deployment. Rebuilding is required whenever the public API URL changes.

### 6. Publish Firebase Hosting only after approval

Use Firebase CLI login in an interactive environment you control. GitHub code alone is not Firebase authentication. A Cloud Shell/browser terminal can clone the approved branch, install its frontend dependencies, run the checked build, and authenticate Firebase without configuring Windows.

From the repository root, using the Firebase project ID you verified:

```sh
npx --yes --package firebase-tools firebase login
npx --yes --package firebase-tools firebase deploy --only hosting --project YOUR_PROJECT_ID
```

The deploy command is the publication step and requires explicit approval. Do not run `firebase init` over the existing configuration. Copy the actual **Hosting URL** printed by a successful deployment; do not invent or promise a URL before provider confirmation.

### 7. End-to-end acceptance checks on the public site

- HTTPS page opens; no localhost requests or mixed-content errors in browser developer tools.
- Sample: **19 events / 4 alerts / 0 invalid rows / 0 duplicates**.
- Upload `data/sample_auth_logs.csv`: same result.
- Invalid CSV, invalid timestamps, duplicates, and oversized upload produce expected messages/counts.
- Rule thresholds 6 / 4 / 6: reanalysis produces zero alerts; restoring defaults returns four.
- Severity/rule filters, selected-alert details, and full CSV export work.
- Mobile view remains usable; refresh keeps the site accessible.
- If using Render Free, repeat after idle sleep and explain the wake-up delay to visitors.

Only after these checks should the actual Firebase HTTPS URL be added to the portfolio. Record the deployed Git commit and confirm Firebase Spark and Render Free remain selected.

## Privacy, resource limits, and rollback

Do not upload real security logs, passwords, API keys, personal data, or credentials. Use synthetic logs. CORS is not authentication, so direct public requests remain possible. The app limits each analysis but is not a production SIEM. Uvicorn concurrency limiting is not a per-user rate limit. Review provider request logging/retention and usage limits before public use; no body logging should be enabled.

No Firebase SDK keys are needed for static Hosting. The API URL and frontend origins are public configuration, not secrets. Do not put credentials in `VITE_*`, YAML, Git, or chat. Authorize services through their own secure account flows.

If validation fails, do not add the URL to the portfolio. Inspect build/runtime logs without copying uploaded contents, correct the API URL or CORS origin, then rebuild/redeploy only with authorization. If a provider asks for an upgrade, payment method, billing activation, or paid add-on, stop; no paid fallback is authorized. Keep database and persistent-disk add-ons disabled.

## Preparation review results

Local verification completed without creating hosting resources:

- 41 Python tests passed, including original CLI regressions and API validation.
- Four frontend utility tests and four Chromium browser tests passed. Browser checks exercised uploads, Python analysis, alert filters/details, rule edits, CSV export, errors/loading, and mobile navigation.
- The checked production build succeeded with `https://authwatch-build-check.example.com`, a **test placeholder only**, not a working API. The resulting ignored `frontend/dist` must be rebuilt using the real deployed API origin before publishing.
- A fresh API process configured with two example Firebase HTTPS origins accepted those exact origins and rejected unrelated/lookalike domains and localhost. No credentials were enabled for CORS.
- Repository file review found no credential-pattern matches. The only included CSV is the fictional 19-event sample using documentation-only IP addresses. Dependency folders, private environment files, caches, generated reports, and build output are excluded by Git ignore rules.

Still pending: actual Firebase Hosting site domains, actual Render API URL, provider-side Free-plan/Blueprint availability checks, account authorization, and post-deployment HTTPS/CORS/end-to-end checks. These are not local code-test failures; they cannot be confirmed before an authorized resource setup/deployment. No live URL is being claimed by this review.
