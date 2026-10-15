/**
 * Escape text for safe interpolation into HTML text nodes and quoted attribute
 * values (& < > " '). Use for every user-controlled value that is built into an
 * HTML string (e.g. the driver PDF print window); React JSX already escapes.
 */
export function escapeHtml(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
