export const YEAR_KEY = "year.fraternal";
export const DEFAULT_YEAR = "2026\u201327";

const YEAR_PATTERN = /^(\d{4})[-\u2013](\d{2})$/;

export const FIXED_CHROME = {
  "about.eyebrow": "When we gather",
  "about.title": "About Our Council",
  "events.eyebrow": "On the calendar",
  "blood.eyebrow": "Charity in practice",
  "blood.title": "Blood Drive",
  "links.eyebrow": "Brothers only",
  "links.title": "Members Quick Links",
  "links.intro": "Dues open in a new tab. Council lists stay here.",
};

export function normalizeFraternalYear(value) {
  const match = YEAR_PATTERN.exec(String(value || "").trim());
  if (!match) return "";
  const start = Number(match[1]);
  const end = Number(match[2]);
  if (start < 1900 || start > 2100) return "";
  if (end !== (start + 1) % 100) return "";
  return `${match[1]}\u2013${String(end).padStart(2, "0")}`;
}

export function fraternalPhrases(year) {
  const label = year || DEFAULT_YEAR;
  return {
    "officers.eyebrow": `Fraternal year ${label}`,
    "officers.intro": `Congratulations to the brothers serving Council 10930 in ${label}.`,
    "directors.eyebrow": `Fraternal year ${label}`,
    "directors.intro": `Program directors for the ${label} fraternal year.`,
  };
}

export function withFraternalYear(map, raw) {
  const year = normalizeFraternalYear(raw);
  if (!year) return null;
  const next = { ...map, [YEAR_KEY]: year };
  for (const [key, value] of Object.entries(next)) {
    if (typeof value === "string" && /\d{4}[-\u2013]\d{2}/.test(value)) {
      next[key] = value.replace(/\d{4}[-\u2013]\d{2}/g, year);
    }
  }
  return { ...next, ...fraternalPhrases(year), ...FIXED_CHROME };
}
