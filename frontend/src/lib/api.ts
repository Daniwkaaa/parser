export type Status = "yes" | "no" | "social_only" | "unreachable" | "unknown" | "na";

export interface BusinessBrief {
  id: number; name: string; category: string; category_label: string;
  address: string | null; city: string | null; phone: string | null; email: string | null;
  website: string | null; instagram: string | null; facebook: string | null;
  lat: number | null; lon: number | null;
  website_status: Status; menu_status: Status; booking_status: Status; outdated_status: Status;
  problems: string[]; lead_score: number; lead_tier: "high" | "medium" | "low"; status: string;
  contact_verified: boolean; rating: number | null; reviews_count: number | null; sources: string[];
  created_at: string | null; last_checked_at: string | null;
}

export interface WebsiteAnalysis {
  url?: string; checked?: boolean; status?: string; final_url?: string | null; http_status?: number | null;
  https?: boolean | null; response_time?: number | null; title?: string | null; has_viewport?: boolean | null;
  copyright_year?: number | null; generator?: string | null; has_menu?: boolean | null; menu_evidence?: string | null;
  has_catalog?: boolean | null; catalog_evidence?: string | null; has_services?: boolean | null; services_evidence?: string | null;
  has_booking?: boolean | null; booking_evidence?: string | null; socials?: Record<string, string>; emails?: string[]; phones?: string[];
  outdated_signals?: { code: string; text: string; strong: boolean }[]; improvement_signals?: string[]; error?: string | null; checked_at?: string;
}

export interface BusinessFull extends BusinessBrief {
  region: string | null; country: string | null; postcode: string | null; raw_type: string | null;
  socials: Record<string, string>; map_url: string | null; opening_hours: string | null; brand: string | null;
  sources_full: { source: string; source_id: string; url: string | null }[];
  website_analysis: WebsiteAnalysis; problem_details: { code: string; label: string; text: string }[];
  summary: string | null; recommendation: string | null; recommended_services: string[];
  score_breakdown: { key: string; label: string; points: number }[]; updated_at: string | null;
  notes: { id: number; text: string; created_at: string }[]; osm_tags: Record<string, string>;
}

export interface Job {
  id: number; status: string; stage: string; params: Record<string, any>; location_label: string | null;
  progress_total: number; progress_done: number; found_count: number; saved_count: number; new_count: number;
  duplicate_count: number; skipped_count: number; error: string | null; area: any;
  created_at: string | null; started_at: string | null; finished_at: string | null;
}

export interface JobLog { id: number; ts: string; level: string; message: string }

export interface Meta {
  categories: { key: string; label: string; group: string; offer_kind: string; booking_kind: string }[];
  groups: Record<string, string>; problems: Record<string, string>; status_labels: Record<string, string>;
  client_statuses: Record<string, string>;
  sources: { key: string; label: string; requires_key: boolean; description: string; key_help: string }[];
}

export interface Stats {
  totals: { businesses: number; no_website: number; social_only: number; no_menu: number; high_potential: number; medium_potential: number; verified_contacts: number; avg_score: number };
  by_category: { key: string; label: string; count: number; avg_score: number }[];
  by_status: { key: string; label: string; count: number }[];
  by_tier: { key: string; label: string; count: number }[];
  by_problem: { key: string; label: string; count: number }[];
  score_histogram: { range: string; count: number }[];
  by_website_status: Record<string, number>;
  recent_jobs: Job[];
}

export interface SettingsData {
  scoring: { weights: Record<string, number>; thresholds: { high: number; medium: number } };
  sources: Record<string, boolean>;
  api_keys: Record<string, { configured: boolean; from_env: boolean; masked: string }>;
  search: { country: string; limit: number; radius_km: number; exclude_chains: boolean; check_websites: boolean; language: string };
  scoring_labels: Record<string, string>;
  source_list: Meta["sources"];
}

export class ApiError extends Error {}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") msg = j.detail;
      else if (Array.isArray(j.detail)) msg = j.detail.map((d: any) => d.msg).join("; ");
    } catch { /* ignore */ }
    throw new ApiError(msg);
  }
  return res.json();
}

export type Filters = Partial<{
  q: string; categories: string[]; problems: string[]; tiers: string[]; statuses: string[]; website_status: string[];
  city: string; min_score: number; has_contact: boolean; job_id: number; sort: string; order: string;
}>;

export function filtersToQuery(f: Filters, extra: Record<string, string | number> = {}): string {
  const p = new URLSearchParams();
  Object.entries(f).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    if (Array.isArray(v)) { if (v.length) p.set(k, v.join(",")); }
    else p.set(k, String(v));
  });
  Object.entries(extra).forEach(([k, v]) => p.set(k, String(v)));
  return p.toString();
}

export const api = {
  meta: () => req<Meta>("/api/meta"),
  stats: () => req<Stats>("/api/stats"),
  businesses: (f: Filters, page: number, pageSize: number) =>
    req<{ total: number; items: BusinessBrief[] }>(`/api/businesses?${filtersToQuery(f, { page, page_size: pageSize })}`),
  mapPoints: (f: Filters) => req<{ id: number; name: string; lat: number; lon: number; lead_score: number; lead_tier: string; category: string; website_status: string; address: string | null }[]>(`/api/businesses/map?${filtersToQuery(f)}`),
  business: (id: number) => req<BusinessFull>(`/api/businesses/${id}`),
  updateBusiness: (id: number, body: Record<string, unknown>) => req<BusinessFull>(`/api/businesses/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteBusiness: (id: number) => req(`/api/businesses/${id}`, { method: "DELETE" }),
  recheck: (id: number) => req<BusinessFull>(`/api/businesses/${id}/recheck`, { method: "POST" }),
  addNote: (id: number, text: string) => req<BusinessFull>(`/api/businesses/${id}/notes`, { method: "POST", body: JSON.stringify({ text }) }),
  deleteNote: (id: number, nid: number) => req(`/api/businesses/${id}/notes/${nid}`, { method: "DELETE" }),
  geocode: (body: Record<string, unknown>) => req<any>("/api/geocode", { method: "POST", body: JSON.stringify(body) }),
  search: (body: Record<string, unknown>) => req<Job>("/api/search", { method: "POST", body: JSON.stringify(body) }),
  jobs: () => req<Job[]>("/api/jobs"),
  job: (id: number) => req<Job>(`/api/jobs/${id}`),
  jobLogs: (id: number, after: number) => req<JobLog[]>(`/api/jobs/${id}/logs?after=${after}`),
  cancelJob: (id: number) => req(`/api/jobs/${id}/cancel`, { method: "POST" }),
  resumeJob: (id: number) => req<Job>(`/api/jobs/${id}/resume`, { method: "POST" }),
  deleteJob: (id: number) => req(`/api/jobs/${id}`, { method: "DELETE" }),
  settings: () => req<SettingsData>("/api/settings"),
  saveScoring: (body: SettingsData["scoring"]) => req<{ rescored: number }>("/api/settings/scoring", { method: "PUT", body: JSON.stringify(body) }),
  resetScoring: () => req<{ rescored: number }>("/api/settings/reset-scoring", { method: "POST" }),
  saveSources: (body: Record<string, boolean>) => req("/api/settings/sources", { method: "PUT", body: JSON.stringify(body) }),
  saveSearchDefaults: (body: Record<string, unknown>) => req("/api/settings/search", { method: "PUT", body: JSON.stringify(body) }),
  saveKeys: (body: Record<string, string>) => req("/api/settings/api-keys", { method: "PUT", body: JSON.stringify(body) }),
  exportUrl: (format: "csv" | "xlsx", f: Filters, ids?: number[]) =>
    `/api/export?${filtersToQuery(f, { format, ...(ids && ids.length ? { ids: ids.join(",") } : {}) })}`,
};
