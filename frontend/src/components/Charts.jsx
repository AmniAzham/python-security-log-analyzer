import { RULES, formatTime } from "../lib.js";

export default function Charts({ result }) {
  const activity = result?.activity ?? [];
  const peak = Math.max(
    1,
    ...activity.map((bucket) => bucket.success + bucket.failure),
  );
  const counts = Object.keys(RULES).map((key) => [
    key,
    result?.alerts.filter((alert) => alert.rule === key).length ?? 0,
  ]);
  const maxAlerts = Math.max(1, ...counts.map(([, count]) => count));
  return (
    <div className="chart-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Login activity</h2>
            <p>Valid unique events · hourly UTC buckets</p>
          </div>
          <span className="legend">
            <i className="dot blue" />
            Success <i className="dot amber" />
            Failure
          </span>
        </div>
        {activity.length ? (
          <div
            className="activity"
            role="img"
            aria-label={activity
              .map(
                (b) =>
                  `${formatTime(b.timestamp)}: ${b.success} successes, ${b.failure} failures`,
              )
              .join("; ")}
          >
            {activity.map((bucket) => (
              <div
                className="bar-column"
                key={bucket.timestamp}
                title={`${formatTime(bucket.timestamp)} · ${bucket.success} success · ${bucket.failure} failure`}
              >
                <span className="bar-total">
                  {bucket.success + bucket.failure}
                </span>
                <div className="bar-track">
                  <div
                    className="bar-stack"
                    style={{
                      height: `${((bucket.success + bucket.failure) / peak) * 100}%`,
                    }}
                  >
                    <div
                      className="failure-bar"
                      style={{ flex: bucket.failure }}
                    />
                    <div
                      className="success-bar"
                      style={{ flex: bucket.success }}
                    />
                  </div>
                </div>
                <small>
                  {bucket.timestamp.slice(0, 10)}
                  <br />
                  {bucket.timestamp.slice(11, 16)}
                </small>
              </div>
            ))}
          </div>
        ) : (
          <div className="chart-empty">
            Analyze a CSV to see activity over time.
          </div>
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Alerts by rule</h2>
            <p>All alerts in the current analysis</p>
          </div>
          <span className="eyebrow">RULE SIGNALS</span>
        </div>
        <div className="rule-chart">
          {counts.map(([key, count]) => (
            <div key={key}>
              <div className="rule-label">
                <span>{RULES[key]}</span>
                <strong>{count}</strong>
              </div>
              <div className="horizontal-track">
                <div style={{ width: `${(count / maxAlerts) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
