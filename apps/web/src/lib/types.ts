export type EligibilityStatus = "eligible" | "rejected" | "unknown";
export type JobFamily =
  | "software_engineering"
  | "backend"
  | "frontend"
  | "fullstack"
  | "mobile"
  | "ai_ml"
  | "data_science"
  | "data_engineering"
  | "mlops"
  | "devops_cloud"
  | "qa_automation"
  | "other";
export type ApplicationStatus = "not_applied" | "applied" | "interview" | "offer" | "rejected" | "withdrawn";

export interface PageResult<T> {
  items: T[];
  total: number;
}

export interface Job {
  id: number;
  company_id: number;
  external_id: string;
  provider: string;
  source_slug: string;
  company_name: string;
  title: string;
  description: string;
  location: string;
  country: string | null;
  department: string | null;
  employment_type: string | null;
  workplace_type: string | null;
  apply_url: string;
  job_url: string | null;
  posted_at: string | null;
  job_family: JobFamily;
  required_skills: string[];
  preferred_skills: string[];
  min_experience_years: number | null;
  seniority: string | null;
  eligibility_status: EligibilityStatus | null;
  eligibility_score: number | null;
}

export interface Evidence {
  kind: string;
  code: string;
  message: string;
  weight: number;
  matched_text: string | null;
  source_url: string | null;
}

export interface JobDetail extends Job {
  evidence: Evidence[];
}

export interface Company {
  id: number;
  name: string;
  normalized_name: string;
  country: string | null;
  career_url: string | null;
  sponsor_verified: boolean;
}

export interface CompanyIntelligence {
  company: Company;
  visa_friendliness_score: number;
  positive_signals: string[];
  negative_signals: string[];
  active_jobs: number;
  eligible_jobs: number;
  jobs: Job[];
}

export interface Stats {
  total_jobs: number;
  eligible_jobs: number;
  rejected_jobs: number;
  unknown_jobs: number;
  companies: number;
}

export interface Coverage {
  configured_sources: number;
  discovered_sources: number;
  verified_sources: number;
  healthy_sources: number;
  degraded_sources: number;
  failing_sources: number;
  blocked_sources: number;
  empty_sources: number;
  sources_scanned_latest_run: number;
  raw_jobs_scanned: number;
  technical_jobs: number;
  european_technical_jobs: number;
  active_jobs: number;
  ai_ml_jobs: number;
  eligible_jobs: number;
  unknown_jobs: number;
  rejected_jobs: number;
  last_refresh_at: string | null;
}

export interface SourceHealth {
  id: number;
  provider: string;
  board_identifier: string;
  company_name: string | null;
  status: "healthy" | "degraded" | "failing" | "blocked" | "empty" | "disabled" | "unverified";
  enabled: boolean;
  manual_override: boolean;
  consecutive_failures: number;
  raw_job_count: number;
  technical_job_count: number;
  active_job_count: number;
  eligible_job_count: number;
  unknown_job_count: number;
  rejected_job_count: number;
  last_http_status: number | null;
  last_error_category: string | null;
  last_error: string | null;
}

export interface Candidate {
  id: number;
  name: string;
  target_roles: string[];
  skills: string[];
  years_of_experience: number;
  seniority: string | null;
  preferred_countries: string[];
  visa_required: boolean;
  relocation_preference: string;
  remote_preference: string;
  excluded_locations: string[];
  created_at: string;
  updated_at: string;
}

export interface CandidateInput {
  name: string;
  target_roles: string[];
  skills: string[];
  years_of_experience: number;
  seniority: string | null;
  preferred_countries: string[];
  visa_required: boolean;
  relocation_preference: string;
  remote_preference: string;
  excluded_locations: string[];
}

export interface CandidateJobStateInput {
  saved: boolean;
  application_status: ApplicationStatus;
  note?: string | null;
}

export interface CandidateJobState extends CandidateJobStateInput {
  id: number;
  candidate_id: number;
  job_id: number;
  created_at: string;
  updated_at: string;
  job: Job;
}

export interface RecommendationScores {
  overall: number;
  visa: number;
  skill: number;
  experience: number;
  country: number;
  company: number;
}

export interface Recommendation {
  job_id: number;
  scores: RecommendationScores;
  total_score: number;
  visa_score: number;
  skill_score: number;
  skill_match: number;
  experience_score: number;
  country_score: number;
  company_score: number;
  required_skill_coverage: number;
  preferred_skill_coverage: number;
  seniority_match: number;
  role_similarity: number;
  matched_skills: string[];
  missing_skills: string[];
  missing_preferred_skills: string[];
  reasons: string[];
  warnings: string[];
  explanation: string[];
  job: Job;
}

export interface RecommendationExplanation {
  candidate: Candidate;
  weights: Record<string, number>;
  recommendations: Recommendation[];
}

export interface ApiError {
  detail?: string;
}
