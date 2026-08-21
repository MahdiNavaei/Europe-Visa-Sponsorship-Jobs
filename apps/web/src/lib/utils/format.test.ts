import { describe, expect, it } from "vitest";
import { formatDate, formatNumber, formatScore, labelize } from "@/lib/utils/format";

describe("format helpers", () => {
  it("formats scores and labels consistently", () => {
    expect(formatScore(92.4)).toBe("92%");
    expect(formatScore(null)).toBe("—");
    expect(labelize("ai_ml")).toBe("AI / ML");
  });

  it("formats dates and numbers for English and Persian", () => {
    expect(formatNumber(1200, "en")).toBe("1,200");
    expect(formatNumber(1200, "fa")).toContain("۱٬۲۰۰");
    expect(formatDate("2026-01-01T00:00:00Z", "en")).toContain("Jan");
  });
});
