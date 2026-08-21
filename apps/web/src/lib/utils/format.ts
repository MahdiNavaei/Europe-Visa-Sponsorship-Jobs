export function formatScore(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : `${Math.round(value)}%`;
}

export function formatDate(value: string | null | undefined, locale = "en") {
  if (!value) return "—";
  return new Intl.DateTimeFormat(locale === "fa" ? "fa-IR" : "en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function formatNumber(value: number | null | undefined, locale = "en") {
  return new Intl.NumberFormat(locale === "fa" ? "fa-IR" : "en-US").format(value ?? 0);
}

export function labelize(value: string | null | undefined) {
  if (!value) return "—";
  const special: Record<string, string> = { ai_ml: "AI / ML", devops_cloud: "DevOps / Cloud", qa_automation: "QA Automation", data_science: "Data Science", data_engineering: "Data Engineering", software_engineering: "Software Engineering" };
  return special[value] ?? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
