/**
 * Formats agent rationale strings into human-readable plain text.
 * If the string contains raw or truncated JSON, it extracts the violations,
 * title, severity, and explanation and formats them as plain English.
 */
export function formatRationale(rawText) {
  if (!rawText || typeof rawText !== "string") return rawText || "";
  const text = rawText.trim();

  // If it's already normal plain text and doesn't look like JSON, return as is
  if (!text.startsWith("{") && !text.includes('"violations"')) {
    return text;
  }

  // Attempt 1: Strict JSON parsing
  try {
    const clean = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "");
    const parsed = JSON.parse(clean);
    if (parsed && Array.isArray(parsed.violations)) {
      if (parsed.violations.length === 0) {
        return "No specific concerns were identified by this agent.";
      }
      const items = parsed.violations
        .slice(0, 3)
        .map((v) => {
          if (typeof v === "string") return v;
          const title = (v.title || "").trim();
          const sev = v.severity ? ` (${v.severity})` : "";
          const expl = (v.explanation || "").trim();
          if (title && expl) return `${title}${sev}: ${expl}`;
          if (title) return `${title}${sev}.`;
          return expl;
        })
        .filter(Boolean);

      let res = items.join(" ");
      if (parsed.violations.length > 3) {
        res += ` (${parsed.violations.length - 3} additional findings omitted for brevity.)`;
      }
      if (res) return res;
    }
  } catch (e) {
    // Truncated/malformed JSON - proceed to regex extraction
  }

  // Attempt 2: Regex extraction for truncated or partial JSON strings
  const titles = Array.from(text.matchAll(/"title"\s*:\s*"([^"]+)"/g), (m) => m[1]);
  const severities = Array.from(text.matchAll(/"severity"\s*:\s*"([^"]+)"/g), (m) => m[1]);
  const explanations = Array.from(text.matchAll(/"explanation"\s*:\s*"([^"]+)"/g), (m) => m[1]);

  const parts = [];
  const maxLen = Math.max(titles.length, explanations.length);
  for (let i = 0; i < maxLen; i++) {
    const t = titles[i] || "";
    const s = severities[i] ? ` (${severities[i]})` : "";
    const e = explanations[i] || "";
    if (t && e) parts.push(`${t}${s}: ${e}`);
    else if (t) parts.push(`${t}${s}.`);
    else if (e) parts.push(e);
  }

  if (parts.length > 0) {
    return parts.slice(0, 3).join(" ");
  }

  // Attempt 3: Clean out JSON punctuation if regex didn't extract fields
  const cleaned = text
    .replace(/```(?:json)?/gi, "")
    .replace(/[{}"\[\]]/g, " ")
    .replace(/\s*(agent|violations|severity|source_regulation|excerpt|explanation|recommendation)\s*:/gi, " ")
    .replace(/\s+/g, " ")
    .trim();

  return cleaned || "No specific concerns were identified by this agent.";
}

/**
 * Sanitizes and cleans summary text, replacing triage messages with standard
 * executive summary sentences.
 */
export function cleanSummary(summary, violations = []) {
  if (!summary || typeof summary !== "string") return "";
  if (
    summary.includes("triaged as low compliance-relevance") ||
    summary.includes("rule-engine findings reported")
  ) {
    const count = Array.isArray(violations) ? violations.length : 0;
    if (count === 0) {
      return "Compliance Council review: no violations found. Document is fully compliant.";
    }
    return `Compliance Council review: ${count} issue(s) found. Remediation recommended.`;
  }
  return summary;
}

