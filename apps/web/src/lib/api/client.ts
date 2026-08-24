import type {
  Candidate,
  CandidateCreated,
  CandidateExport,
  CandidateInput,
  CandidateJobState,
  CandidateJobStateInput,
  Company,
  CompanyIntelligence,
  CatalogSyncStatus,
  Job,
  JobDetail,
  PageResult,
  Recommendation,
  RecommendationExplanation,
  Stats,
  Coverage,
  SourceHealth,
} from "@/lib/types";
import { getCandidateId, getCandidateToken } from "@/lib/utils/candidate";

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

function candidateInit(candidateId: number, init: RequestInit = {}): RequestInit {
  if (getCandidateId() !== candidateId) return init;
  const token = getCandidateToken();
  if (!token) return init;
  const headers = new Headers(init.headers);
  headers.set("X-Candidate-Token", token);
  return { ...init, headers };
}

async function candidateRequest<T>(candidateId: number, path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, candidateInit(candidateId, init));
}

async function candidateRequestPage<T>(candidateId: number, path: string): Promise<PageResult<T>> {
  const response = await fetchResponse(path, candidateInit(candidateId));
  const items = (await response.json()) as T[];
  const total = Number(response.headers.get("X-Total-Count") ?? items.length);
  return { items, total: Number.isFinite(total) ? total : items.length };
}

export const api = {
  listJobs: async (params: URLSearchParams = new URLSearchParams()) =>
    (await requestPage<Job>(`/api/v1/jobs?${params.toString()}`)).items,
  listJobsPage: (params: URLSearchParams = new URLSearchParams()) =>
    requestPage<Job>(`/api/v1/jobs?${params.toString()}`),
  getJob: (id: number) => request<JobDetail>(`/api/v1/jobs/${id}`),
  listCompanies: (query = "", offset = 0, limit = 50) =>
    requestPage<Company>(`/api/v1/companies?query=${encodeURIComponent(query)}&offset=${offset}&limit=${limit}`),
  getCompany: (id: number, offset = 0, limit = 50) => request<CompanyIntelligence>(`/api/v1/companies/${id}?offset=${offset}&limit=${limit}`),
  getStats: () => request<Stats>("/api/v1/stats"),
  getCatalogStatus: () => request<CatalogSyncStatus>("/api/v1/catalog/status"),
  getCoverage: () => request<Coverage>("/api/v1/coverage"),
  getSourceHealth: () => request<SourceHealth[]>("/api/v1/sources/health?limit=5000"),
  getCountries: () => request<{ countries: string[] }>("/api/v1/countries"),
  createCandidate: (input: CandidateInput) =>
    request<CandidateCreated>("/api/v1/candidates", { method: "POST", body: JSON.stringify(input) }),
  updateCandidate: (id: number, input: CandidateInput) =>
    candidateRequest<Candidate>(id, `/api/v1/candidates/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  getCandidate: (id: number) => candidateRequest<Candidate>(id, `/api/v1/candidates/${id}`),
  exportCandidate: (id: number) => candidateRequest<CandidateExport>(id, `/api/v1/candidates/${id}/export`),
  deleteCandidate: async (id: number) => { await fetchResponse(`/api/v1/candidates/${id}`, candidateInit(id, { method: "DELETE" })); },
  listJobStates: (candidateId: number) => candidateRequest<CandidateJobState[]>(candidateId, `/api/v1/candidates/${candidateId}/job-states`),
  getJobState: (candidateId: number, jobId: number) =>
    candidateRequest<CandidateJobState | null>(candidateId, `/api/v1/candidates/${candidateId}/jobs/${jobId}/state`),
  updateJobState: (candidateId: number, jobId: number, input: CandidateJobStateInput) =>
    candidateRequest<CandidateJobState>(candidateId, `/api/v1/candidates/${candidateId}/jobs/${jobId}/state`, { method: "PUT", body: JSON.stringify(input) }),
  deleteJobState: async (candidateId: number, jobId: number) => {
    await fetchResponse(`/api/v1/candidates/${candidateId}/jobs/${jobId}/state`, candidateInit(candidateId, { method: "DELETE" }));
  },
  getRecommendations: async (id: number, params: URLSearchParams = new URLSearchParams()) =>
    (await candidateRequestPage<Recommendation>(id, `/api/v1/recommendations/${id}?${params.toString()}`)).items,
  getRecommendationsPage: (id: number, params: URLSearchParams = new URLSearchParams()) =>
    candidateRequestPage<Recommendation>(id, `/api/v1/recommendations/${id}?${params.toString()}`),
  getJobRecommendation: (candidateId: number, jobId: number) =>
    candidateRequest<Recommendation>(candidateId, `/api/v1/recommendations/${candidateId}/jobs/${jobId}`),
  explainRecommendations: (id: number, params: URLSearchParams = new URLSearchParams()) =>
    candidateRequest<RecommendationExplanation>(id, `/api/v1/recommendations/${id}/explain?${params.toString()}`),
};
