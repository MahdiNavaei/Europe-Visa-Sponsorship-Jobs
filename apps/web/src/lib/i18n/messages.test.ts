import { describe, expect, it } from "vitest";
import { messages } from "@/lib/i18n/messages";

describe("critical i18n labels", () => {
  it("does not expose raw detail translation keys", () => {
    for (const locale of ["en", "fa"] as const) {
      expect(messages[locale].detail.jobSignal).not.toMatch(/^detail\./);
      expect(messages[locale].detail.companySignal).not.toMatch(/^detail\./);
      expect(messages[locale].detail.finalEligibility).not.toMatch(/^detail\./);
    }
  });
});
