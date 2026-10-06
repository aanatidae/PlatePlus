/** Convert FastAPI errors to text without coercing objects or exposing request inputs. */
export function formatApiError(body: unknown, fallback = "Request failed."): string {
  function message(value: unknown): string | null {
    if (typeof value === "string") return value.trim() && value !== "[object Object]" ? value : null;
    if (Array.isArray(value)) {
      const messages = value.map(message).filter((item): item is string => Boolean(item));
      return messages.length ? [...new Set(messages)].join("; ") : null;
    }
    if (value && typeof value === "object") {
      const error = value as Record<string, unknown>;
      if (error.detail !== undefined) return message(error.detail);
      const text = message(error.msg ?? error.message);
      if (!text) return null;
      const loc = Array.isArray(error.loc) ? error.loc : [];
      const labels: Record<string, string> = { minimum_percentage: "minimum percentage", maximum_percentage: "maximum percentage", multiplier: "multiplier" };
      const scenarios = ["Low", "Moderate", "High", "Severe"];
      const index = loc.indexOf("rules");
      const row = index >= 0 && typeof loc[index + 1] === "number" ? scenarios[loc[index + 1] as number] : undefined;
      const field = labels[String(loc[loc.length - 1])];
      return `${row ? `${row} ` : ""}${field ? `${field}: ` : ""}${text.replace(/^Value error, /, "")}`;
    }
    return null;
  }
  return message(body) ?? fallback;
}

export async function requireOk(response: Response, fallback: string): Promise<void> {
  if (!response.ok) throw new Error(formatApiError(await response.json().catch(() => null), fallback));
}
