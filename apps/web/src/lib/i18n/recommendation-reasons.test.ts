import { describe, expect, it } from "vitest";
import { localizeRecommendationReason } from "@/lib/i18n/recommendation-reasons";

describe("localizeRecommendationReason", () => {
  const translate = (key: string, values?: Record<string, string>) => ({
    preferredCountry: `کشور ترجیحی: ${values?.country}`,
    sponsorshipPassed: "از دروازه صلاحیت اسپانسرشیپ عبور کرد.",
    unavailableReason: "جزئیات در شواهد اصلی آگهی قابل بررسی است.",
  }[key] ?? key);

  it("localizes deterministic recommendation explanations without changing English", () => {
    expect(localizeRecommendationReason("The job is in preferred country Germany.", "fa", translate)).toBe("کشور ترجیحی: Germany");
    expect(localizeRecommendationReason("The job passed the strict sponsorship eligibility gate.", "fa", translate)).toBe("از دروازه صلاحیت اسپانسرشیپ عبور کرد.");
    expect(localizeRecommendationReason("The job passed the strict sponsorship eligibility gate.", "en", translate)).toContain("strict sponsorship");
  });
});
