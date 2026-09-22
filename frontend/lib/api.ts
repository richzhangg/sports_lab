export interface VariableSpec {
  key: string;
  label: string;
  description: string;
  unit: string;
}
export type FamilyKey = "linear" | "poisson" | "negbin" | "zip" | "zinb" | "custom";
export interface FamilySpec {
  key: FamilyKey;
  label: string;
  note: string;
}
export interface SourceInfo {
  key?: string;
  name: string;
  is_real: boolean;
  citation: string;
  notes?: string;
  geography?: string;
  n_rows: number;
  n_communities: number;
  years: number[];
  provenance?: Record<string, unknown>;
}
export interface Metadata {
  source: SourceInfo;
  predictors: VariableSpec[];
  outcomes: VariableSpec[];
  families: FamilySpec[];
  years: number[];
  count_outcome: string;
  equation_functions: string[];
}

export interface Coefficient {
  term: string;
  estimate: number;
  std_error: number | null;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  rate_ratio?: number;
  rate_ratio_ci_low?: number;
  rate_ratio_ci_high?: number;
}
export interface Metrics {
  n: number;
  rmse: number;
  mae: number;
  mean_error_bias: number;
  r2_response: number | null;
  pearson_corr: number | null;
  mean_poisson_deviance?: number;
  deviance_r2?: number | null;
}
export interface RunSpec {
  outcome: string;
  predictors: string[];
  family: string;
  train_years: number[];
  test_year: number;
  standardize: boolean;
  n_train: number;
  n_test: number;
  equation?: string;
  variables?: Record<string, string>;
}

export interface EquationInfo {
  text: string;
  bindings: { symbol: string; column: string }[];
  note: string;
  negative_prediction_share: number;
}
export interface CVAgg {
  [metric: string]: { mean: number; sd: number; n: number };
}
export interface CrossValidation {
  primary_metric: string;
  kfold?: {
    scheme: string;
    k: number;
    held_out: CVAgg;
    in_fold: CVAgg;
    per_fold: Record<string, number | null>[];
  };
  leave_one_year_out?: {
    scheme: string;
    held_out: CVAgg;
    per_year: Record<string, number | null>[];
  };
}

export interface RunResult {
  spec: RunSpec;
  coefficients: Coefficient[];
  diagnostics: Record<string, number | string | boolean | null>;
  train_metrics: Metrics;
  test_metrics: Metrics;
  cross_validation?: CrossValidation;
  equation?: EquationInfo;
  predicted_vs_observed: { observed: number; predicted: number; community_name: string; state: string }[];
  residuals: {
    community_id: string;
    community_name: string;
    state: string;
    observed: number;
    predicted: number;
    raw_residual: number;
    pearson_residual: number;
    deviance_residual: number;
  }[];
  geo_distribution: { state: string; observed: number; predicted: number; n: number; residual: number }[];
  baseline?: { description: string; train_metrics: Metrics; test_metrics: Metrics };
  vs_baseline?: Record<string, number | null>;
  overfitting: {
    primary_metric: string;
    train_value: number | null;
    test_value: number | null;
    test_minus_train_pct: number | null;
    flag: boolean;
    note: string;
  };
}

export interface RunRequest {
  outcome: string;
  predictors: string[];
  family: string;
  train_years: number[];
  test_year: number;
  standardize: boolean;
  include_baseline: boolean;
  cv_folds: number;
  equation?: string;
  variables?: Record<string, string>;
}

// In production the API lives on its own host (see DEPLOY.md); locally it's the
// dev proxy. Requests go straight to the backend so the browser — not a Vercel
// edge proxy with a 30 s cap — waits out a free-tier cold start.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const u = (path: string) => `${API_BASE}${path}`;

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${r.status})`);
  }
  return r.json();
}

export const getMetadata = () => fetch(u("/api/metadata")).then((r) => j<Metadata>(r));
export const getPreview = () =>
  fetch(u("/api/preview?limit=30")).then((r) =>
    j<{ columns: string[]; rows: Record<string, unknown>[]; source: SourceInfo }>(r),
  );

export interface RostersInfo {
  available: boolean;
  description?: string;
  player_seasons?: number;
  schools?: number;
  conferences?: string[];
  seasons?: Record<string, number>;
  by_gender?: Record<string, number>;
  placed_in_a_us_county?: number;
  columns?: string[];
  sample?: Record<string, unknown>[];
}
export const getRosters = () => fetch(u("/api/rosters?sample=40")).then((r) => j<RostersInfo>(r));

export interface PlayerHit {
  player_name: string;
  school: string;
  gender: string;
  conference: string;
  hometown_raw: string;
  county_fips: string | null;
  county_name: string | null;
  seasons: number[];
}
export interface PlayerSearchResult {
  available: boolean;
  query?: string;
  total: number;
  results: PlayerHit[];
}
export const searchPlayers = (q: string, limit = 60) =>
  fetch(u(`/api/players?q=${encodeURIComponent(q)}&limit=${limit}`)).then((r) => j<PlayerSearchResult>(r));

export interface CountyYearRow {
  year: number;
  population: number | null;
  youth_population: number | null;
  median_income: number | null;
  poverty_rate: number | null;
  pct_bachelors: number | null;
  tennis_courts_per_100k: number | null;
  pop_density: number | null;
  d1_players: number | null;
  d1_rate_per_100k: number | null;
}
export interface CountyPlayer {
  player_name: string;
  school: string;
  gender: string;
  conference: string;
  hometown_raw: string;
  seasons: number[];
}
export interface CountyDetail {
  found: boolean;
  fips?: string;
  name?: string;
  state?: string;
  by_year?: CountyYearRow[];
  players?: CountyPlayer[];
  player_count?: number;
}
export const getCounty = (fips: string) =>
  fetch(u(`/api/county/${fips}`)).then((r) => j<CountyDetail>(r));

export interface GeoCounty {
  fips: string;
  name: string;
  lat: number;
  lon: number;
  players: number;
}
export interface GeoPayload {
  year: number | null;
  years: number[];
  max_players: number;
  total_players: number;
  counties: GeoCounty[];
}
export const getGeo = (year?: number) =>
  fetch(u(`/api/geo${year ? `?year=${year}` : ""}`)).then((r) => j<GeoPayload>(r));
export const runModel = (req: RunRequest) =>
  fetch(u("/api/run"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  }).then((r) => j<RunResult>(r));

/** Lightweight summary returned by GET /api/experiments (no big arrays). */
export interface SavedExperiment {
  id: string;
  created_at: number;
  label: string;
  source_key: string | null;
  spec: RunSpec;
  train_metrics: Metrics;
  test_metrics: Metrics;
  diagnostics: Record<string, number | string | boolean | null>;
  vs_baseline?: Record<string, number | null>;
  overfitting: RunResult["overfitting"];
  cross_validation?: CrossValidation;
}
/** Full record from GET /api/experiments/{id}. */
export interface SavedExperimentFull extends SavedExperiment {
  result: RunResult;
}

/**
 * Saved models live in the visitor's own browser (localStorage) — no database
 * to run or pay for. Per-browser; survive reloads; not shared across devices.
 * Functions keep a Promise API so callers don't change.
 */
const XKEY = "sol.experiments.v1";

interface StoredExperiment {
  id: string;
  created_at: number;
  label: string;
  result: RunResult;
}

const readStore = (): StoredExperiment[] => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(XKEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
};
const writeStore = (arr: StoredExperiment[]) => {
  try {
    window.localStorage.setItem(XKEY, JSON.stringify(arr));
  } catch {
    /* quota / private mode — silently no-op */
  }
};
const summarize = (x: StoredExperiment): SavedExperiment => ({
  id: x.id,
  created_at: x.created_at,
  label: x.label,
  source_key: (x.result.spec as { source_key?: string }).source_key ?? null,
  spec: x.result.spec,
  train_metrics: x.result.train_metrics,
  test_metrics: x.result.test_metrics,
  diagnostics: x.result.diagnostics,
  vs_baseline: x.result.vs_baseline,
  overfitting: x.result.overfitting,
  cross_validation: x.result.cross_validation,
});

export const listExperiments = async (): Promise<SavedExperiment[]> =>
  readStore()
    .sort((a, b) => a.created_at - b.created_at)
    .map(summarize);

export const saveExperiment = async (label: string, result: RunResult): Promise<SavedExperiment> => {
  const rec: StoredExperiment = {
    id: (globalThis.crypto?.randomUUID?.() ?? String(Date.now() + Math.random())).slice(0, 12),
    created_at: Date.now() / 1000,
    label,
    result,
  };
  writeStore([...readStore(), rec]);
  return summarize(rec);
};

export const getExperiment = async (id: string): Promise<SavedExperimentFull> => {
  const x = readStore().find((e) => e.id === id);
  if (!x) throw new Error("experiment not found");
  return { ...summarize(x), result: x.result };
};

export const deleteExperiment = async (id: string): Promise<{ deleted: string }> => {
  writeStore(readStore().filter((e) => e.id !== id));
  return { deleted: id };
};

export const clearExperiments = async (): Promise<{ deleted: number }> => {
  const n = readStore().length;
  writeStore([]);
  return { deleted: n };
};
