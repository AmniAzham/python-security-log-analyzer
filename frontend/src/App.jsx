import { useState } from "react";
import { DEFAULT_CONFIG } from "./lib.js";
import Charts from "./components/Charts.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import Alerts from "./components/Alerts.jsx";
import RuleSettings from "./components/RuleSettings.jsx";
import About from "./components/About.jsx";

const NAV = [
  ["overview", "Overview", "◫"],
  ["rules", "Detection rules", "≡"],
  ["about", "About this tool", "ⓘ"],
];
export default function App() {
  const [page, setPage] = useState("overview");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [config, setConfig] = useState({ ...DEFAULT_CONFIG });
  const [analysisId, setAnalysisId] = useState(0);
  function receive(data, loading) {
    setBusy(loading);
    // Clear stale results before a new request so a failed upload cannot appear successful.
    setResult(data);
    setAnalysisId((id) => id + 1);
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#overview"
          onClick={() => setPage("overview")}
        >
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          <span>
            AuthWatch<small>SECURITY LOG ANALYZER</small>
          </span>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {NAV.map(([key, label, icon]) => (
            <button
              key={key}
              className={page === key ? "active" : ""}
              aria-current={page === key ? "page" : undefined}
              onClick={() => setPage(key)}
            >
              <span aria-hidden="true">{icon}</span>
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="dot blue" />
          <strong>Portfolio edition</strong>
          <p>
            Defensive analysis.
            <br />
            Fictional data. Real learning.
          </p>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            WORKSPACE <span className="slash">/</span>{" "}
            {NAV.find(([key]) => key === page)[1]}
          </span>
          <span className="mode-pill">
            <i className="dot blue" />
            Educational mode
          </span>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <span className="eyebrow">AUTHENTICATION INTELLIGENCE</span>
              <h1>
                {page === "overview"
                  ? "Security overview"
                  : page === "rules"
                    ? "Detection rules"
                    : "About AuthWatch"}
              </h1>
              <p>
                {page === "overview"
                  ? "Understand login activity. Investigate what matters."
                  : page === "rules"
                    ? "Tune the signals behind your investigation."
                    : "A focused project for learning defensive security."}
              </p>
            </div>
            {page === "overview" && result && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() => {
                  setResult(null);
                  setError("");
                  setAnalysisId((id) => id + 1);
                }}
              >
                Clear results
              </button>
            )}
          </div>
          <div role="alert">
            {error && <div className="error-box">{error}</div>}
          </div>
          {page === "overview" && (
            <>
              <UploadPanel
                busy={busy}
                config={config}
                onResult={receive}
                setError={setError}
              />
              <div className="metrics" aria-live="polite">
                {[
                  [
                    "Events analyzed",
                    result?.events_analyzed,
                    "Valid, unique login events",
                  ],
                  ["Total alerts", result?.total_alerts, "Investigation leads"],
                  [
                    "Invalid rows",
                    result?.invalid_rows,
                    "Skipped with warnings",
                  ],
                  ["Duplicates", result?.duplicates, "Excluded from detection"],
                ].map(([label, count, note]) => (
                  <section className="metric" key={label}>
                    <span>{label}</span>
                    <strong>{count ?? "—"}</strong>
                    <small>{note}</small>
                  </section>
                ))}
              </div>
              {result && (
                <div className="analysis-meta">
                  <span>
                    Analyzed: <strong>{result.source}</strong> · UTC
                  </span>
                  <details>
                    <summary>Settings used for these results</summary>
                    <dl>
                      {Object.entries(result.config).map(([key, value]) => (
                        <div key={key}>
                          <dt>{key.replaceAll("_", " ")}</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  </details>
                </div>
              )}
              <Charts result={result} />
              {result?.warnings.length > 0 && (
                <details className="panel warnings">
                  <summary>
                    {result.warnings.length} data-quality warnings — review
                    skipped rows
                  </summary>
                  <ul>
                    {result.warnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </details>
              )}
              <Alerts key={analysisId} result={result} />
              <div className="disclaimer">
                <span aria-hidden="true">ⓘ</span> Alerts indicate patterns to
                investigate, not proof of an attack. Only analyze data you are
                authorized to use.
              </div>
            </>
          )}
          {page === "rules" && (
            <RuleSettings config={config} onSave={setConfig} busy={busy} />
          )}
          {page === "about" && <About />}
        </main>
        <footer>
          AuthWatch <span>Python engine · React interface · No database</span>
        </footer>
      </div>
    </div>
  );
}
