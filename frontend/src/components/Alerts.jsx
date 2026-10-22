import { useState } from "react";
import { RULES, downloadAlerts, filterAlerts, formatTime } from "../lib.js";

export default function Alerts({ result }) {
  const [severity, setSeverity] = useState("all");
  const [rule, setRule] = useState("all");
  const [selected, setSelected] = useState(null);
  const rows = filterAlerts(result?.alerts ?? [], severity, rule);
  return (
    <section className="panel alerts-panel">
      <div className="panel-heading">
        <div>
          <h2>
            Security alerts{" "}
            <span className="count">{result?.total_alerts ?? 0}</span>
          </h2>
          <p>Review the evidence before drawing conclusions.</p>
        </div>
        <button
          className="secondary"
          disabled={!result}
          onClick={() => downloadAlerts(result.alerts)}
        >
          ↓ Export all alerts
        </button>
      </div>
      <div className="filters">
        <label>
          Severity
          <select
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
          >
            <option value="all">All severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>
        </label>
        <label>
          Detection rule
          <select
            value={rule}
            onChange={(event) => setRule(event.target.value)}
          >
            <option value="all">All rules</option>
            {Object.entries(RULES).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <span className="small">
          Showing {rows.length} of {result?.total_alerts ?? 0} alerts
        </span>
      </div>
      {rows.length ? (
        <div className="table-scroll">
          <table>
            <caption className="sr-only">
              Alerts for the current analysis. Use Review to inspect an alert.
            </caption>
            <thead>
              <tr>
                {[
                  "Timestamp (UTC)",
                  "Detection rule",
                  "Source IP",
                  "Username",
                  "Events",
                  "Severity",
                  "Explanation",
                  "Details",
                ].map((text) => (
                  <th key={text} scope="col">
                    {text}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((alert, index) => (
                <tr key={`${alert.rule}-${alert.alert_timestamp}-${index}`}>
                  <td className="mono">
                    {formatTime(alert.alert_timestamp).replace(" UTC", "")}
                  </td>
                  <td>{RULES[alert.rule]}</td>
                  <td className="mono">{alert.source_ip}</td>
                  <td>{alert.username || "All accounts"}</td>
                  <td>{alert.event_count}</td>
                  <td>
                    <span className={`badge ${alert.severity}`}>
                      {alert.severity}
                    </span>
                  </td>
                  <td className="explanation">{alert.explanation}</td>
                  <td>
                    <button
                      className="review-button"
                      onClick={() => setSelected(alert)}
                      aria-label={`Review ${RULES[alert.rule]} at ${alert.alert_timestamp}`}
                    >
                      Review →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <span aria-hidden="true">◇</span>
          <h3>
            {!result
              ? "Your investigation starts here"
              : result.total_alerts
                ? "No alerts match these filters"
                : "No rules triggered"}
          </h3>
          <p>
            {!result
              ? "Load the sample or upload a CSV to explore security signals."
              : result.total_alerts
                ? "Try another severity or detection rule."
                : "No configured thresholds were reached. This does not prove the activity is safe."}
          </p>
        </div>
      )}
      {selected && (
        <div
          className="alert-detail"
          role="region"
          aria-label="Selected alert details"
        >
          <div className="panel-heading">
            <h3>{RULES[selected.rule]}</h3>
            <button className="secondary" onClick={() => setSelected(null)}>
              Close details
            </button>
          </div>
          <p>{selected.explanation}</p>
          <dl>
            <div>
              <dt>Source IP / username</dt>
              <dd>
                {selected.source_ip} /{" "}
                {selected.username || "Multiple or all accounts"}
              </dd>
            </div>
            <div>
              <dt>Relevant events / severity</dt>
              <dd>
                {selected.event_count} / {selected.severity}
              </dd>
            </div>
            <div>
              <dt>Window begins</dt>
              <dd>{formatTime(selected.window_start)}</dd>
            </div>
            <div>
              <dt>Window ends / alert time</dt>
              <dd>{formatTime(selected.window_end)}</dd>
            </div>
          </dl>
          <p className="small">
            Investigation: confirm the source records, check account and device
            context, and correlate MFA or session activity. Follow your
            organization’s escalation process.
          </p>
        </div>
      )}
    </section>
  );
}
