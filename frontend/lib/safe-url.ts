/** Allow web/email links and local paths; reject executable or disguised schemes. */
export function safeUrl(url: string): string {
  const value = url.trim();
  if (/[\u0000-\u001f\u007f\\]/.test(value)) return "#";
  if (/^https?:\/\//i.test(value) || /^mailto:/i.test(value)) return value;
  if (value.startsWith("/") && !value.startsWith("//")) return value;
  if (/^www\./i.test(value)) return `https://${value}`;
  if (value.startsWith("#")) return value;
  return "#";
}
