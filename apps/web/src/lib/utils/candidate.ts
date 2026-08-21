"use client";

import { useSyncExternalStore } from "react";

function readCandidateId() {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem("career-radar-candidate");
  const id = value ? Number(value) : NaN;
  return Number.isFinite(id) ? id : null;
}

export function useCandidateId() {
  return useSyncExternalStore(() => () => undefined, readCandidateId, () => null);
}
