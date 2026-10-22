export const MAX_UPLOAD_BYTES = 1024 * 1024;
export const DEFAULT_CONFIG = Object.freeze({
  failure_threshold: 5,
  failure_window_minutes: 5,
  account_threshold: 3,
  account_window_minutes: 10,
  success_failure_threshold: 5,
  success_window_minutes: 10,
});
export const RULES = {
  repeated_failed_logins: "Repeated failed logins",
  multiple_account_targeting: "Multiple-account targeting",
  success_after_failures: "Success after failures",
};
export const CSV_FIELDS = [
  "rule",
  "source_ip",
  "username",
  "event_count",
  "window_start",
  "window_end",
  "alert_timestamp",
  "severity",
  "explanation",
];

export function validateConfig(config) {
  return Object.keys(DEFAULT_CONFIG).every(
    (key) =>
      /^\d+$/.test(String(config[key])) &&
      Number.isSafeInteger(Number(config[key])) &&
      Number(config[key]) > 0,
  );
}

export function validateFile(file) {
  if (!file) return "Choose a CSV file first.";
  if (!file.name.toLowerCase().endsWith(".csv"))
    return "Choose a file ending in .csv.";
  if (file.size === 0)
    return "This file is empty. Include a CSV header and events.";
  if (file.size > MAX_UPLOAD_BYTES)
    return "This file exceeds the 1 MiB upload limit.";
  return "";
}

export function filterAlerts(alerts, severity, rule) {
  return alerts.filter(
    (alert) =>
      (severity === "all" || alert.severity === severity) &&
      (rule === "all" || alert.rule === rule),
  );
}

export function alertsToCSV(alerts) {
  // Quote all cells and neutralize spreadsheet formulas in user-controlled text.
  const cell = (value) => {
    let text = String(value ?? "");
    if (/^[\s\u0000-\u001f]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text))
      text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  return (
    [
      CSV_FIELDS,
      ...alerts.map((alert) => CSV_FIELDS.map((field) => alert[field])),
    ]
      .map((row) => row.map(cell).join(","))
      .join("\r\n") + "\r\n"
  );
}

export function downloadAlerts(alerts) {
  const url = URL.createObjectURL(
    new Blob(["\uFEFF", alertsToCSV(alerts)], {
      type: "text/csv;charset=utf-8",
    }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "alerts.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function formatTime(timestamp) {
  return timestamp.replace("T", " ").replace("+00:00", " UTC");
}
