import type { EligibilityStatus, JobFamily } from "@/lib/types";

export function formatScore(value: number | null | undefined, locale = "en") {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat(locale === "fa" ? "fa-IR" : "en-US", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value / 100);
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
  const special: Record<string, string> = {
    ai_ml: "AI / ML",
    devops_cloud: "DevOps / Cloud",
    qa_automation: "QA Automation",
    data_science: "Data Science",
    data_engineering: "Data Engineering",
    software_engineering: "Software Engineering",
  };
  return special[value] ?? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

const jobFamiliesFa: Record<JobFamily, string> = {
  software_engineering: "مهندسی نرم‌افزار",
  backend: "بک‌اند",
  frontend: "فرانت‌اند",
  fullstack: "فول‌استک",
  mobile: "موبایل",
  ai_ml: "هوش مصنوعی / یادگیری ماشین",
  data_science: "علم داده",
  data_engineering: "مهندسی داده",
  mlops: "MLOps",
  devops_cloud: "DevOps / کلاد",
  qa_automation: "تست و اتوماسیون",
  other: "سایر",
};

const countriesFa: Record<string, string> = {
  Germany: "آلمان",
  Netherlands: "هلند",
  Sweden: "سوئد",
  Denmark: "دانمارک",
  Finland: "فنلاند",
  Ireland: "ایرلند",
  "United Kingdom": "بریتانیا",
};

export function formatJobFamily(value: JobFamily, locale = "en") {
  return locale === "fa" ? jobFamiliesFa[value] : labelize(value);
}

export function formatCountry(value: string | null | undefined, locale = "en") {
  if (!value) return locale === "fa" ? "کشور نامشخص" : "Country unknown";
  return locale === "fa" ? countriesFa[value] ?? value : value;
}

export function formatStatus(value: EligibilityStatus | null, locale = "en") {
  if (!value) return "—";
  if (locale !== "fa") return labelize(value);
  return value === "eligible" ? "واجد شرایط" : value === "unknown" ? "نامشخص" : "رد شده";
}
