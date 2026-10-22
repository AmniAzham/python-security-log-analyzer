export default function About() {
  return (
    <div className="about-grid">
      <section className="panel">
        <span className="eyebrow">BUILT TO LEARN</span>
        <h2>From individual events to useful signals.</h2>
        <p>
          AuthWatch is a Python Security Log Analyzer presented as a React
          dashboard. It demonstrates a small SOC workflow: validate logs, detect
          patterns, triage alerts, and export findings.
        </p>
        <p>
          React displays results; FastAPI calls the original Python parser and
          detector. All timestamps are normalized to UTC. The sample contains
          fictional accounts and documentation-only IP addresses.
        </p>
        <h3>What an analyst does next</h3>
        <p>
          Check the original evidence, establish whether the source is a shared
          network, review the account’s usual behavior, and correlate MFA and
          device context. An alert starts an investigation; it does not settle
          it.
        </p>
      </section>
      <section className="panel">
        <span className="eyebrow">KNOW THE BOUNDARIES</span>
        <h2>Educational signals, human judgment.</h2>
        <p>
          Rule-based alerts can be false positives: forgotten passwords and
          shared gateways can look suspicious. This tool cannot establish
          compromise or detect every distributed, slow, or non-login attack.
        </p>
        <h3>Privacy & ethical use</h3>
        <p>
          Use synthetic logs or data you have explicit permission to process. Do
          not upload passwords, tokens, or personal data. The API processes CSV
          bytes temporarily in memory; it has no database, accounts, or raw-log
          storage. Results remain in this page’s memory until you clear them or
          reload.
        </p>
        <p>
          For deployment, the API needs separate Python hosting, HTTPS, an
          explicit CORS origin allowlist, and infrastructure controls. CORS is
          not authentication or a rate limiter.
        </p>
      </section>
    </div>
  );
}
