export const MODEL_OPTIONS = [
  { id: "gemini-3.8-flash", label: "Gemini 3.8 Flash", provider: "gemini" },
  { id: "gemini-3.7-flash", label: "Gemini 3.7 Flash", provider: "gemini" },
  { id: "gemini-3.6-flash", label: "Gemini 3.6 Flash", provider: "gemini" },
  { id: "gemini-3.5-flash", label: "Gemini 3.5 Flash", provider: "gemini" },
  { id: "gemini-3.5-flash-lite", label: "Gemini 3.5 Flash-Lite", provider: "gemini" },
  { id: "openai/gpt-oss-120b", label: "Groq GPT-OSS 120B", provider: "groq" },
  { id: "openai/gpt-oss-20b", label: "Groq GPT-OSS 20B", provider: "groq" },
] as const;

export const DEFAULT_MODEL = MODEL_OPTIONS[0].id;

export function isAvailableModel(id: string): boolean {
  return MODEL_OPTIONS.some((model) => model.id === id);
}
