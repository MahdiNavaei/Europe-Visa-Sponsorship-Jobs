"use client";

import { useSyncExternalStore } from "react";

const STORAGE_KEY = "career-radar-candidate";
const CHANGE_EVENT = "career-radar-candidate-change";

export function getCandidateId() {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(STORAGE_KEY);
  if (!value) return null;
  let stored: unknown = value;
  try { stored = JSON.parse(value); } catch { /* Legacy numeric value. */ }
  const id = typeof stored === "object" && stored !== null && "id" in stored
    ? Number((stored as { id: unknown }).id)
    : Number(stored);
  return Number.isFinite(id) && id > 0 ? id : null;
}

export function getCandidateToken() {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(STORAGE_KEY);
  if (!value) return null;
  try {
    const stored = JSON.parse(value) as { token?: unknown };
    return typeof stored.token === "string" && stored.token.length >= 32 ? stored.token : null;
  } catch {
    return null;
  }
}

function subscribe(callback: () => void) {
  const handler = () => callback();
  window.addEventListener("storage", handler);
  window.addEventListener(CHANGE_EVENT, handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener(CHANGE_EVENT, handler);
  };
}

export function setCandidateId(id: number, token?: string) {
  window.localStorage.setItem(STORAGE_KEY, token ? JSON.stringify({ id, token }) : String(id));
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function clearCandidateId() {
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function useCandidateId() {
  return useSyncExternalStore(subscribe, getCandidateId, () => null);
}
