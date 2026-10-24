/** Keep failed requests and empty placeholders out of saved/exported answers. */
export function isAppFailureText(content: string): boolean {
  const text = content.trim();
  return text === "Answer could not be completed and verified. Please retry or choose another configured model."
    || text === "The answer did not pass the source support check and was withheld. Try a narrower question or inspect the source document."
    || /^An answer was generated but the source-support check could not finish\.[\s\S]{0,600}$/.test(text);
}

export function lastOriginalQuestion(messages: { role: string; content: string }[]): string | null {
  return [...messages].reverse().find(m => m.role === "user" && m.content.trim() && !isAppFailureText(m.content))?.content.trim() || null;
}

export function isSavedChatMessage(message: { role: string; content: string }): boolean {
  if (!message.content.trim()) return false;
  if (message.role !== "assistant") return true;
  const text = message.content.trim();
  return !isAppFailureText(text)
    && text !== "⚠️ An error occurred while retrieving or generating an answer. Please verify backend connectivity."
    && !text.startsWith("⚠️ Failed to query public knowledge book:");
}
