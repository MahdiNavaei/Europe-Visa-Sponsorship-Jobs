"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { CandidateInput } from "@/lib/types";

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: api.getStats, staleTime: 60_000 });
}

export function useCountries() {
  return useQuery({ queryKey: ["countries"], queryFn: api.getCountries, staleTime: 300_000 });
}

export function useJobs(params: URLSearchParams) {
  return useQuery({
    queryKey: ["jobs", params.toString()],
    queryFn: () => api.listJobs(params),
    staleTime: 30_000,
  });
}

export function useJob(id: number) {
  return useQuery({ queryKey: ["job", id], queryFn: () => api.getJob(id), enabled: Number.isFinite(id) });
}

export function useCompanies(country?: string) {
  return useQuery({ queryKey: ["companies", country], queryFn: () => api.listCompanies(country), staleTime: 60_000 });
}

export function useCandidate(id: number | null) {
  return useQuery({ queryKey: ["candidate", id], queryFn: () => api.getCandidate(id as number), enabled: id !== null });
}

export function useRecommendations(id: number | null, params: URLSearchParams) {
  return useQuery({
    queryKey: ["recommendations", id, params.toString()],
    queryFn: () => api.getRecommendations(id as number, params),
    enabled: id !== null,
    staleTime: 30_000,
  });
}

export function useCreateCandidate() {
  return useMutation({ mutationFn: (input: CandidateInput) => api.createCandidate(input) });
}
