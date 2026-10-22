import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_CONFIG,
  validateConfig,
  validateFile,
  filterAlerts,
  alertsToCSV,
} from "../src/lib.js";

test("settings require positive safe whole numbers in every field", () => {
  assert.equal(validateConfig(DEFAULT_CONFIG), true);
  for (const value of [
    "",
    0,
    -1,
    1.5,
    true,
    "1e3",
    "1.5",
    Number.MAX_SAFE_INTEGER + 1,
  ]) {
    assert.equal(
      validateConfig({ ...DEFAULT_CONFIG, failure_threshold: value }),
      false,
    );
  }
  assert.equal(
    validateConfig({ ...DEFAULT_CONFIG, failure_threshold: "6" }),
    true,
  );
});

test("upload feedback rejects missing, wrong type, empty and oversized files", () => {
  assert.ok(validateFile(null));
  assert.ok(validateFile({ name: "file.exe", size: 10 }));
  assert.ok(validateFile({ name: "file.csv", size: 0 }));
  assert.ok(validateFile({ name: "file.csv", size: 1048577 }));
  assert.equal(validateFile({ name: "FILE.CSV", size: 1048576 }), "");
});

test("severity and rule filters combine without mutating results", () => {
  const alerts = [
    { severity: "high", rule: "a" },
    { severity: "medium", rule: "b" },
  ];
  assert.equal(filterAlerts(alerts, "all", "all").length, 2);
  assert.deepEqual(filterAlerts(alerts, "high", "a"), [alerts[0]]);
  assert.deepEqual(filterAlerts(alerts, "high", "b"), []);
  assert.equal(alerts.length, 2);
});

test("CSV export quotes commas, quotes and newlines, and neutralizes formulas", () => {
  const csv = alertsToCSV([
    {
      username: "=DANGEROUS()",
      explanation: 'a,"quoted"\nline',
      source_ip: "192.0.2.1",
    },
  ]);
  assert.ok(csv.includes('"\'=DANGEROUS()"'));
  assert.ok(csv.includes('"a,""quoted""\nline"'));
  assert.ok(csv.endsWith("\r\n"));
  assert.equal(alertsToCSV([]).split("\r\n").length, 2);
});
