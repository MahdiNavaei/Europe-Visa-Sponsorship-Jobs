"use client";

import { useSyncExternalStore } from "react";

const STORAGE_KEY = "career-radar-candidate";
const CHANGE_EVENT = "career-radar-candidate-change";

function readCandidateId() {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(STORAGE_KEY);
  const id = value ? Number(value) : NaN;
  return Number.isFinite(id) && id > 0 ? id : null;
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

export function setCandidateId(id: number) {
  window.localStorage.setItem(STORAGE_KEY, String(id));
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function clearCandidateId() {
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

export function useCandidateId() {
  return useSyncExternalStore(subscribe, readCandidateId, () => null);
}
