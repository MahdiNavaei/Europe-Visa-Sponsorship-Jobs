import { beforeEach, describe, expect, it } from "vitest";
import { clearCandidateId, getCandidateId, getCandidateToken, setCandidateId } from "@/lib/utils/candidate";

describe("candidate browser credential storage", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        get length() { return values.size; },
        clear: () => values.clear(),
        getItem: (key: string) => values.get(key) ?? null,
        key: (index: number) => [...values.keys()][index] ?? null,
        removeItem: (key: string) => values.delete(key),
        setItem: (key: string, value: string) => values.set(key, value),
      },
    });
  });

  it("stores the candidate token with its matching id", () => {
    setCandidateId(42, "a".repeat(43));
    expect(getCandidateId()).toBe(42);
    expect(getCandidateToken()).toBe("a".repeat(43));
    clearCandidateId();
    expect(getCandidateId()).toBeNull();
    expect(getCandidateToken()).toBeNull();
  });

  it("reads legacy numeric ids without inventing a token", () => {
    window.localStorage.setItem("career-radar-candidate", "7");
    expect(getCandidateId()).toBe(7);
    expect(getCandidateToken()).toBeNull();
  });

  it("rejects malformed records", () => {
    window.localStorage.setItem("career-radar-candidate", '{"id":"nope","token":123}');
    expect(getCandidateId()).toBeNull();
    expect(getCandidateToken()).toBeNull();
  });
});
