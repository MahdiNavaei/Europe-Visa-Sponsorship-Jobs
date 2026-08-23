"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { CandidateInput, CandidateJobStateInput } from "@/lib/types";

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: api.getStats, staleTime: 60_000 });
}

export function useCoverage() {
  return useQuery({ queryKey: ["coverage"], queryFn: api.getCoverage, staleTime: 60_000 });
}

export function useSourceHealth() {
  return useQuery({ queryKey: ["source-health"], queryFn: api.getSourceHealth, staleTime: 60_000 });
}

export function useCountries() {
  return useQuery({ queryKey: ["countries"], queryFn: api.getCountries, staleTime: 300_000 });
}

export function useJobs(params: URLSearchParams) {
  return useQuery({ queryKey: ["jobs", params.toString()], queryFn: () => api.listJobs(params), staleTime: 30_000 });
}

export function useJobsPage(params: URLSearchParams, enabled = true) {
  return useQuery({ queryKey: ["jobs-page", params.toString()], queryFn: () => api.listJobsPage(params), staleTime: 30_000, enabled });
}

export function useJob(id: number) {
  return useQuery({ queryKey: ["job", id], queryFn: () => api.getJob(id), enabled: Number.isFinite(id) && id > 0 });
}

export function useCompanies(country?: string) {
  return useQuery({ queryKey: ["companies", country], queryFn: () => api.listCompanies(country), staleTime: 60_000 });
}

export function useCompany(id: number) {
  return useQuery({ queryKey: ["company", id], queryFn: () => api.getCompany(id), enabled: Number.isFinite(id) && id > 0 });
}

export function useCandidate(id: number | null) {
  return useQuery({ queryKey: ["candidate", id], queryFn: () => api.getCandidate(id as number), enabled: id !== null });
}

export function useJobStates(candidateId: number | null) {
  return useQuery({
    queryKey: ["job-states", candidateId],
    queryFn: () => api.listJobStates(candidateId as number),
    enabled: candidateId !== null,
    staleTime: 15_000,
  });
}

export function useJobState(candidateId: number | null, jobId: number) {
  return useQuery({
    queryKey: ["job-state", candidateId, jobId],
    queryFn: () => api.getJobState(candidateId as number, jobId),
    enabled: candidateId !== null && Number.isFinite(jobId) && jobId > 0,
    staleTime: 15_000,
  });
}

export function useUpdateJobState() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ candidateId, jobId, input }: { candidateId: number; jobId: number; input: CandidateJobStateInput }) => api.updateJobState(candidateId, jobId, input),
    onSuccess: (state) => {
      queryClient.setQueryData(["job-state", state.candidate_id, state.job_id], state);
      void queryClient.invalidateQueries({ queryKey: ["job-states", state.candidate_id] });
    },
  });
}

export function useDeleteJobState() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ candidateId, jobId }: { candidateId: number; jobId: number }) => api.deleteJobState(candidateId, jobId).then(() => ({ candidateId, jobId })),
    onSuccess: ({ candidateId, jobId }) => {
      queryClient.setQueryData(["job-state", candidateId, jobId], null);
      void queryClient.invalidateQueries({ queryKey: ["job-states", candidateId] });
    },
  });
}

export function useRecommendations(id: number | null, params: URLSearchParams) {
  return useQuery({ queryKey: ["recommendations", id, params.toString()], queryFn: () => api.getRecommendations(id as number, params), enabled: id !== null, staleTime: 30_000 });
}

export function useRecommendationsPage(id: number | null, params: URLSearchParams) {
  return useQuery({ queryKey: ["recommendations-page", id, params.toString()], queryFn: () => api.getRecommendationsPage(id as number, params), enabled: id !== null, staleTime: 30_000 });
}

export function useJobRecommendation(candidateId: number | null, jobId: number) {
  return useQuery({ queryKey: ["job-recommendation", candidateId, jobId], queryFn: () => api.getJobRecommendation(candidateId as number, jobId), enabled: candidateId !== null && Number.isFinite(jobId) && jobId > 0, staleTime: 30_000 });
}

export function useRecommendationExplanation(candidateId: number | null, params: URLSearchParams) {
  return useQuery({ queryKey: ["recommendation-explanation", candidateId, params.toString()], queryFn: () => api.explainRecommendations(candidateId as number, params), enabled: candidateId !== null, staleTime: 30_000 });
}

export function useCreateCandidate() {
  return useMutation({ mutationFn: (input: CandidateInput) => api.createCandidate(input) });
}

export function useUpdateCandidate() {
  return useMutation({ mutationFn: ({ id, input }: { id: number; input: CandidateInput }) => api.updateCandidate(id, input) });
}
