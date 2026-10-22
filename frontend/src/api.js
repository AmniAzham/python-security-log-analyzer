const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function analyze({ file, config, sample }) {
  const query = new URLSearchParams({ config: JSON.stringify(config) });
  let response;
  try {
    response = await fetch(
      `${API_BASE}/api/${sample ? "sample" : "analyze"}?${query}`,
      {
        method: "POST",
        ...(sample
          ? {}
          : { headers: { "Content-Type": "text/csv" }, body: file }),
        credentials: "omit",
      },
    );
  } catch {
    throw new Error(
      "Cannot reach the API. Start the Python backend and check its frontend origin setting.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `Analysis failed (HTTP ${response.status}). Check the CSV and rule settings.`,
    );
  }
  return response.json();
}
