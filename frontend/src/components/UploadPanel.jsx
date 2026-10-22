import { useRef, useState } from "react";
import { analyze } from "../api.js";
import { validateFile } from "../lib.js";

export default function UploadPanel({ busy, config, onResult, setError }) {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [source, setSource] = useState("");
  const input = useRef(null);
  function choose(candidate) {
    const error = validateFile(candidate);
    setError(error);
    setFile(error ? null : candidate);
  }
  async function run(sample) {
    if (!sample && validateFile(file)) {
      setError(validateFile(file));
      return;
    }
    onResult(null, true);
    setError("");
    try {
      const data = await analyze({ file, config, sample });
      setSource(sample ? "Fictional sample dataset" : file.name);
      onResult(
        { ...data, source: sample ? "Fictional sample dataset" : file.name },
        false,
      );
    } catch (error) {
      setError(error.message);
      onResult(null, false);
    }
  }
  return (
    <section className="panel upload-panel">
      <div>
        <span className="eyebrow">START AN INVESTIGATION</span>
        <h2>Bring your logs into focus.</h2>
        <p>
          Upload an authorized authentication CSV or explore the fictional
          sample.
        </p>
        <p className="small">
          Required: timestamp, username, source_ip, event_type, status.
          <br />
          UTF-8 CSV · up to 1 MiB / 5,000 valid unique events · processed in
          memory
        </p>
      </div>
      <div className="upload-actions">
        <div
          className={`drop-zone ${dragging ? "dragging" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            if (!busy) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            if (!busy) choose(event.dataTransfer.files[0]);
          }}
        >
          <span className="upload-icon" aria-hidden="true">
            ↑
          </span>
          <button
            className="file-button"
            disabled={busy}
            onClick={() => input.current.click()}
          >
            Choose CSV
          </button>
          <span>{file ? file.name : "or drag a file here"}</span>
          <input
            ref={input}
            type="file"
            accept=".csv,text/csv"
            aria-label="Authentication CSV"
            disabled={busy}
            onChange={(event) => choose(event.target.files[0])}
          />
        </div>
        <div className="button-row">
          <button
            className="primary"
            disabled={busy || !file}
            onClick={() => run(false)}
          >
            {busy ? "Analyzing…" : "Analyze CSV"}{" "}
            <span aria-hidden="true">→</span>
          </button>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => run(true)}
          >
            Load sample data
          </button>
        </div>
        <span className="small" role="status">
          {busy
            ? "Running Python detection rules…"
            : source
              ? `Last loaded: ${source}`
              : "No raw logs are saved by the API."}
        </span>
      </div>
    </section>
  );
}
