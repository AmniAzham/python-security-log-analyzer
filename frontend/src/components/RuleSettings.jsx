import { useState } from "react";
import { DEFAULT_CONFIG, validateConfig } from "../lib.js";

const RULE_FORMS = [
  [
    "Repeated failed logins",
    "Spot concentrated login failures from a single source IP.",
    "failure_threshold",
    "failure_window_minutes",
    "failed attempts",
  ],
  [
    "Multiple-account targeting",
    "Find one source IP attempting several distinct usernames. Both outcomes count.",
    "account_threshold",
    "account_window_minutes",
    "distinct usernames",
  ],
  [
    "Success after failures",
    "Prioritize a success after failures for the same source IP and username.",
    "success_failure_threshold",
    "success_window_minutes",
    "preceding failures",
  ],
];

export default function RuleSettings({ config, onSave, busy }) {
  // Draft input state is separate from the saved settings used for API requests.
  const [draft, setDraft] = useState(config);
  const [notice, setNotice] = useState("");
  const valid = validateConfig(draft);
  function save(event) {
    event.preventDefault();
    if (!valid) return;
    onSave(
      Object.fromEntries(
        Object.entries(draft).map(([key, value]) => [key, Number(value)]),
      ),
    );
    setNotice(
      "Rules applied. Run a new analysis to use these settings; previous results keep their original settings.",
    );
  }
  return (
    <form onSubmit={save}>
      <div className="section-intro">
        <h2>Transparent rules. Adjustable thresholds.</h2>
        <p>
          Every rule uses an inclusive sliding time window. Values must be
          positive whole numbers.
        </p>
      </div>
      <div className="settings-grid">
        {RULE_FORMS.map(
          ([title, description, threshold, window, unit], index) => (
            <section className="panel" key={threshold}>
              <span className="eyebrow">RULE 0{index + 1}</span>
              <h3>{title}</h3>
              <p>{description}</p>
              <label>
                Threshold ({unit})
                <input
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={draft[threshold]}
                  onChange={(event) => {
                    setDraft({ ...draft, [threshold]: event.target.value });
                    setNotice("");
                  }}
                />
              </label>
              <label>
                Time window (minutes)
                <input
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={draft[window]}
                  onChange={(event) => {
                    setDraft({ ...draft, [window]: event.target.value });
                    setNotice("");
                  }}
                />
              </label>
            </section>
          ),
        )}
      </div>
      <div className="settings-footer">
        <button className="primary" disabled={!valid || busy}>
          Apply rules
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setDraft({ ...DEFAULT_CONFIG });
            setNotice(
              "Defaults restored in the form. Select Apply rules to save them.",
            );
          }}
        >
          Restore defaults
        </button>
        <span role="status">
          {notice ||
            (!valid
              ? "Enter a positive whole number for every field."
              : "Settings last for this browser session only.")}
        </span>
      </div>
    </form>
  );
}
