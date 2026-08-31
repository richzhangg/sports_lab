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

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${r.status})`);
  }
  return r.json();
}

export const getMetadata = () => fetch("/api/metadata").then((r) => j<Metadata>(r));
export const getPreview = () =>
  fetch("/api/preview?limit=30").then((r) =>
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
export const getRosters = () => fetch("/api/rosters?sample=40").then((r) => j<RostersInfo>(r));
export const runModel = (req: RunRequest) =>
  fetch("/api/run", {
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

export const listExperiments = () =>
  fetch("/api/experiments").then((r) => j<SavedExperiment[]>(r));
export const saveExperiment = (label: string, result: RunResult) =>
  fetch("/api/experiments", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ label, result }),
  }).then((r) => j<SavedExperiment>(r));
export const getExperiment = (id: string) =>
  fetch(`/api/experiments/${id}`).then((r) => j<SavedExperimentFull>(r));
export const deleteExperiment = (id: string) =>
  fetch(`/api/experiments/${id}`, { method: "DELETE" }).then((r) => j<{ deleted: string }>(r));
export const clearExperiments = () =>
  fetch("/api/experiments", { method: "DELETE" }).then((r) => j<{ deleted: number }>(r));
