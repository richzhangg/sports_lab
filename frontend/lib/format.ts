export const fmt = (v: number | null | undefined, d = 3): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (!Number.isFinite(v)) return v > 0 ? "∞" : "-∞";
  const abs = Math.abs(v);
  if (abs !== 0 && (abs >= 1e6 || abs < 1e-4)) return v.toExponential(2);
  return v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
};

export const fmtInt = (v: number | null | undefined): string =>
  v === null || v === undefined ? "—" : Math.round(v).toLocaleString();

export const fmtPct = (v: number | null | undefined, d = 1): string =>
  v === null || v === undefined || !Number.isFinite(v) ? "—" : `${v.toFixed(d)}%`;

export const fmtP = (v: number | null | undefined): string => {
  if (v === null || v === undefined) return "—";
  if (v < 0.001) return "<0.001";
  return v.toFixed(3);
};

export const FAMILY_LABEL: Record<string, string> = {
  linear: "Linear (OLS)",
  poisson: "Poisson",
  negbin: "Negative Binomial",
  zip: "Zero-Inflated Poisson",
  zinb: "Zero-Inflated NB",
  custom: "Custom equation",
};

export const specSummary = (s: {
  family: string;
  outcome: string;
  predictors: string[];
  train_years: number[];
  test_year: number;
  equation?: string;
}): string => {
  const yrs =
    s.train_years.length > 1
      ? `${s.train_years[0]}–${s.train_years[s.train_years.length - 1]}`
      : `${s.train_years[0]}`;
  const tail = `${yrs} → ${s.test_year}`;
  if (s.family === "custom") return `${s.equation ?? "equation"}  ·  ${tail}`;
  return `${FAMILY_LABEL[s.family] ?? s.family} · ${s.predictors.length} predictor${
    s.predictors.length === 1 ? "" : "s"
  } · ${tail}`;
};
