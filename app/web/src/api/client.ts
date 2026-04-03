import type {
  AfterActionReviewRecord,
  ComparePlansResponse,
  DashboardSummaryResponse,
  ExperimentRecord,
  HealthResponse,
  JobRecord,
  LibraryTemplateRecord,
  LocationSearchResponse,
  MissionPlanRecord,
  MissionAreaPreviewResponse,
  PlanComparisonRecord,
  RecommendationResponse,
  ResolvedLocation,
  ReportRecord,
  RunRecord,
  ScenarioRecord,
  WeatherSummary,
} from "@/api/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(await response.text(), response.status);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }

  return (await response.text()) as T;
}

export const api = {
  baseUrl: API_BASE_URL,
  health: () => request<HealthResponse>("/health"),
  dashboardSummary: () => request<DashboardSummaryResponse>("/dashboard/summary"),
  searchLocations: (payload: Record<string, unknown>) =>
    request<LocationSearchResponse>("/geo/search-locations", { method: "POST", body: JSON.stringify(payload) }),
  resolveLocation: (payload: Record<string, unknown>) =>
    request<ResolvedLocation>("/geo/resolve-location", { method: "POST", body: JSON.stringify(payload) }),
  previewMissionArea: (payload: Record<string, unknown>) =>
    request<MissionAreaPreviewResponse>("/geo/preview-area", { method: "POST", body: JSON.stringify(payload) }),
  weather: (payload: Record<string, unknown>) =>
    request<WeatherSummary>("/geo/weather", { method: "POST", body: JSON.stringify(payload) }),
  scenarios: () => request<{ items: ScenarioRecord[] }>("/scenarios"),
  scenario: (id: string) => request<ScenarioRecord>(`/scenarios/${id}`),
  createScenario: (payload: Record<string, unknown>) =>
    request<ScenarioRecord>("/scenarios", { method: "POST", body: JSON.stringify(payload) }),
  updateScenario: (id: string, payload: Record<string, unknown>) =>
    request<ScenarioRecord>(`/scenarios/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  templates: () => request<{ items: LibraryTemplateRecord[] }>("/library/templates"),
  template: (id: string) => request<LibraryTemplateRecord>(`/library/templates/${id}`),
  plans: () => request<{ items: MissionPlanRecord[] }>("/plans"),
  plan: (id: string) => request<MissionPlanRecord>(`/plans/${id}`),
  createPlan: (payload: Record<string, unknown>) =>
    request<MissionPlanRecord>("/plans", { method: "POST", body: JSON.stringify(payload) }),
  updatePlan: (id: string, payload: Record<string, unknown>) =>
    request<MissionPlanRecord>(`/plans/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  comparisons: () => request<{ items: PlanComparisonRecord[] }>("/comparisons"),
  comparison: (id: string) => request<PlanComparisonRecord>(`/comparisons/${id}`),
  createComparison: (payload: Record<string, unknown>) =>
    request<PlanComparisonRecord>("/comparisons", { method: "POST", body: JSON.stringify(payload) }),
  comparisonSummary: (id: string) =>
    request<Record<string, unknown>>(`/comparisons/${id}/summary`),
  comparePlans: (payload: Record<string, unknown>) =>
    request<ComparePlansResponse>("/compare-plans", { method: "POST", body: JSON.stringify(payload) }),
  recommend: (payload: Record<string, unknown>) =>
    request<RecommendationResponse>("/recommend", { method: "POST", body: JSON.stringify(payload) }),
  runs: () => request<{ items: RunRecord[] }>("/runs"),
  run: (id: string) => request<RunRecord>(`/runs/${id}`),
  launchRun: (payload: Record<string, unknown>) =>
    request<RunRecord>("/runs", { method: "POST", body: JSON.stringify(payload) }),
  launchComparisonRun: (id: string, payload: Record<string, unknown>) =>
    request<RunRecord>(`/comparisons/${id}/run`, { method: "POST", body: JSON.stringify(payload) }),
  intervene: (id: string, payload: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/runs/${id}/interventions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  replay: (id: string) => request<{ run_id: string; replay: unknown[] }>(`/runs/${id}/replay`),
  events: (id: string) => request<{ run_id: string; events: Record<string, unknown>[] }>(`/runs/${id}/events`),
  experiments: () => request<{ items: ExperimentRecord[] }>("/experiments"),
  experiment: (id: string) => request<ExperimentRecord>(`/experiments/${id}`),
  createExperiment: (payload: Record<string, unknown>) =>
    request<ExperimentRecord>("/experiments", { method: "POST", body: JSON.stringify(payload) }),
  experimentSummary: (id: string) =>
    request<{ experiment_id: string; summary: Record<string, unknown>[] }>(`/experiments/${id}/summary`),
  jobs: () => request<{ items: JobRecord[] }>("/jobs"),
  reports: () => request<{ items: ReportRecord[] }>("/reports"),
  createRunReport: (runId: string) => request<ReportRecord>(`/reports/${runId}`, { method: "POST", body: "{}" }),
  report: (id: string) => request<ReportRecord>(`/reports/${id}`),
  reviews: () => request<{ items: AfterActionReviewRecord[] }>("/reviews"),
  review: (id: string) => request<AfterActionReviewRecord>(`/reviews/${id}`),
  createReviewFromRun: (runId: string) =>
    request<AfterActionReviewRecord>(`/reviews/from-run/${runId}`, { method: "POST", body: "{}" }),
};
