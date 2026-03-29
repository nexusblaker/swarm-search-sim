export function formatTimestamp(value?: number | null) {
  if (!value) {
    return "n/a";
  }
  return new Date(value * 1000).toLocaleString();
}

export function safeString(value: unknown) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}
