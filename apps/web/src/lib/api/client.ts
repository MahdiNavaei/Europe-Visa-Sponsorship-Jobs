import type {
  Candidate,
  CandidateInput,
  Company,
  Job,
  JobDetail,
  Recommendation,
  RecommendationExplanation,
  Stats,
} from "@/lib/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(error.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listJobs: (params: URLSearchParams = new URLSearchParams()) =>
    request<Job[]>(`/api/v1/jobs?${params.toString()}`),
  getJob: (id: number) => request<JobDetail>(`/api/v1/jobs/${id}`),
  listCompanies: (country?: string) =>
    request<Company[]>(`/api/v1/companies${country ? `?country=${encodeURIComponent(country)}` : ""}`),
  getStats: () => request<Stats>("/api/v1/stats"),
  getCountries: () => request<{ countries: string[] }>("/api/v1/countries"),
  createCandidate: (input: CandidateInput) =>
    request<Candidate>("/api/v1/candidates", { method: "POST", body: JSON.stringify(input) }),
  getCandidate: (id: number) => request<Candidate>(`/api/v1/candidates/${id}`),
  getRecommendations: (id: number, params: URLSearchParams = new URLSearchParams()) =>
    request<Recommendation[]>(`/api/v1/recommendations/${id}?${params.toString()}`),
  explainRecommendations: (id: number, params: URLSearchParams = new URLSearchParams()) =>
    request<RecommendationExplanation>(`/api/v1/recommendations/${id}/explain?${params.toString()}`),
};
