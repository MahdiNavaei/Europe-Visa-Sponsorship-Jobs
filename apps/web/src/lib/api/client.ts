import type {
  Candidate,
  CandidateInput,
  CandidateJobState,
  CandidateJobStateInput,
  Company,
  CompanyIntelligence,
  Job,
  JobDetail,
  PageResult,
  Recommendation,
  RecommendationExplanation,
  Stats,
} from "@/lib/types";

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;
const API_URL = (configuredApiUrl === undefined ? "http://localhost:8000" : configuredApiUrl).replace(/\/$/, "");

async function fetchResponse(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(error.detail ?? `Request failed (${response.status})`);
  }
  return response;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetchResponse(path, init);
  return response.json() as Promise<T>;
}

async function requestPage<T>(path: string): Promise<PageResult<T>> {
  const response = await fetchResponse(path);
  const items = (await response.json()) as T[];
  const header = response.headers.get("X-Total-Count");
  const total = header === null ? items.length : Number(header);
  return { items, total: Number.isFinite(total) ? total : items.length };
}

export const api = {
  listJobs: async (params: URLSearchParams = new URLSearchParams()) =>
    (await requestPage<Job>(`/api/v1/jobs?${params.toString()}`)).items,
  listJobsPage: (params: URLSearchParams = new URLSearchParams()) =>
    requestPage<Job>(`/api/v1/jobs?${params.toString()}`),
  getJob: (id: number) => request<JobDetail>(`/api/v1/jobs/${id}`),
  listCompanies: (country?: string) =>
    request<Company[]>(`/api/v1/companies${country ? `?country=${encodeURIComponent(country)}` : ""}`),
  getCompany: (id: number) => request<CompanyIntelligence>(`/api/v1/companies/${id}`),
  getStats: () => request<Stats>("/api/v1/stats"),
  getCountries: () => request<{ countries: string[] }>("/api/v1/countries"),
  createCandidate: (input: CandidateInput) =>
    request<Candidate>("/api/v1/candidates", { method: "POST", body: JSON.stringify(input) }),
  updateCandidate: (id: number, input: CandidateInput) =>
    request<Candidate>(`/api/v1/candidates/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  getCandidate: (id: number) => request<Candidate>(`/api/v1/candidates/${id}`),
  listJobStates: (candidateId: number) => request<CandidateJobState[]>(`/api/v1/candidates/${candidateId}/job-states`),
  getJobState: (candidateId: number, jobId: number) =>
    request<CandidateJobState | null>(`/api/v1/candidates/${candidateId}/jobs/${jobId}/state`),
  updateJobState: (candidateId: number, jobId: number, input: CandidateJobStateInput) =>
    request<CandidateJobState>(`/api/v1/candidates/${candidateId}/jobs/${jobId}/state`, { method: "PUT", body: JSON.stringify(input) }),
  deleteJobState: async (candidateId: number, jobId: number) => {
    await fetchResponse(`/api/v1/candidates/${candidateId}/jobs/${jobId}/state`, { method: "DELETE" });
  },
  getRecommendations: async (id: number, params: URLSearchParams = new URLSearchParams()) =>
    (await requestPage<Recommendation>(`/api/v1/recommendations/${id}?${params.toString()}`)).items,
  getRecommendationsPage: (id: number, params: URLSearchParams = new URLSearchParams()) =>
    requestPage<Recommendation>(`/api/v1/recommendations/${id}?${params.toString()}`),
  getJobRecommendation: (candidateId: number, jobId: number) =>
    request<Recommendation>(`/api/v1/recommendations/${candidateId}/jobs/${jobId}`),
  explainRecommendations: (id: number, params: URLSearchParams = new URLSearchParams()) =>
    request<RecommendationExplanation>(`/api/v1/recommendations/${id}/explain?${params.toString()}`),
};
