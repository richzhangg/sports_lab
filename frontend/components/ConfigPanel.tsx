"use client";
import { useMemo } from "react";
import type { Metadata, RunRequest, FamilyKey } from "@/lib/api";

export interface VarBinding {
  symbol: string;
  column: string;
}

export interface Config {
  outcome: string;
  predictors: string[];
  family: FamilyKey;
  trainYears: number[];
  testYear: number;
  standardize: boolean;
  cvFolds: number;
  equation: string;
  variables: VarBinding[];
}

export const PRESETS: { name: string; predictors: string[] }[] = [
  { name: "Population only", predictors: ["population"] },
  { name: "Population + Income", predictors: ["population", "median_income"] },
  {
    name: "Socioeconomic + Geographic",
    predictors: ["median_income", "poverty_rate", "pct_bachelors", "tennis_courts_per_100k", "pop_density"],
  },
  {
    name: "Everything (incl. nuisance)",
    predictors: [
      "median_income", "poverty_rate", "pct_bachelors", "tennis_courts_per_100k", "pop_density",
      "noise_1", "noise_2", "noise_3", "noise_4", "noise_5", "noise_6",
    ],
  },
];

export const EXAMPLE_EQUATIONS: { label: string; equation: string; vars: VarBinding[] }[] = [
  {
    label: "rate × population",
    equation: "(p / 1000000) * (0.4 + 0.02 * b + 0.15 * t)",
    vars: [
      { symbol: "p", column: "population" },
      { symbol: "b", column: "pct_bachelors" },
      { symbol: "t", column: "tennis_courts_per_100k" },
    ],
  },
  {
    label: "income-driven",
    equation: "0.00003 * i - 0.15 * v",
    vars: [
      { symbol: "i", column: "median_income" },
      { symbol: "v", column: "poverty_rate" },
    ],
  },
  {
    label: "threshold on access",
    equation: "where(t > 3, (p / 100000) * t * 0.6, 0)",
    vars: [
      { symbol: "p", column: "population" },
      { symbol: "t", column: "tennis_courts_per_100k" },
    ],
  },
];

export function toRequest(c: Config): RunRequest {
  const base = {
    outcome: c.outcome,
    family: c.family,
    train_years: c.trainYears,
    test_year: c.testYear,
    include_baseline: true,
    cv_folds: c.family === "custom" ? 0 : c.cvFolds,
  };
  if (c.family === "custom") {
    const variables: Record<string, string> = {};
    for (const v of c.variables) if (v.symbol.trim() && v.column) variables[v.symbol.trim()] = v.column;
    return { ...base, predictors: [], standardize: false, equation: c.equation, variables };
  }
  return { ...base, predictors: c.predictors, standardize: c.standardize };
}

export default function ConfigPanel({
  meta,
  config,
  setConfig,
  onRun,
  running,
  error,
}: {
  meta: Metadata;
  config: Config;
  setConfig: (c: Config) => void;
  onRun: () => void;
  running: boolean;
  error: string | null;
}) {
  const set = (patch: Partial<Config>) => setConfig({ ...config, ...patch });
  const isCustom = config.family === "custom";
  const isCount = ["poisson", "negbin", "zip", "zinb"].includes(config.family);
  const outcomeValid = !isCount || config.outcome === meta.count_outcome;

  const togglePredictor = (k: string) =>
    set({
      predictors: config.predictors.includes(k)
        ? config.predictors.filter((p) => p !== k)
        : [...config.predictors, k],
    });

  const toggleTrainYear = (y: number) =>
    set({
      trainYears: config.trainYears.includes(y)
        ? config.trainYears.filter((v) => v !== y)
        : [...config.trainYears, y].sort(),
    });

  const setVar = (i: number, patch: Partial<VarBinding>) =>
    set({ variables: config.variables.map((v, j) => (j === i ? { ...v, ...patch } : v)) });
  const addVar = () => {
    const used = new Set(config.variables.map((v) => v.symbol));
    const next = ["x", "y", "z", "w", "u", "v", "a", "b", "c", "d"].find((s) => !used.has(s)) ?? "";
    set({ variables: [...config.variables, { symbol: next, column: "" }] });
  };
  const removeVar = (i: number) => set({ variables: config.variables.filter((_, j) => j !== i) });

  const validVars = config.variables.filter((v) => v.symbol.trim() && v.column);
  const yearsOverlap = config.trainYears.includes(config.testYear);
  const canRun = isCustom
    ? config.equation.trim().length > 0 && validVars.length > 0 && config.trainYears.length > 0 &&
      !yearsOverlap && !running
    : config.predictors.length > 0 && config.trainYears.length > 0 && !yearsOverlap && outcomeValid && !running;

  const familyNote = useMemo(
    () => meta.families.find((f) => f.key === config.family)?.note ?? "",
    [meta.families, config.family],
  );

  return (
    <div className="card">
      <div className="card-h justify-between">
        <span className="flex items-center gap-2.5">
          <span className="step-no">01</span> Configure experiment
        </span>
        <span className="eyebrow">Hypothesis</span>
      </div>
      <div className="card-b space-y-5">
        {/* Outcome */}
        <Field label="Outcome variable (Y)">
          <select
            className="field-input"
            value={config.outcome}
            onChange={(e) => set({ outcome: e.target.value })}
          >
            {meta.outcomes.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label} {o.unit ? `(${o.unit})` : ""}
              </option>
            ))}
          </select>
          {!outcomeValid && (
            <p className="mt-1 text-[12px] text-court">
              Poisson / Negative Binomial require the count outcome “
              {meta.outcomes.find((o) => o.key === meta.count_outcome)?.label}”.
            </p>
          )}
        </Field>

        {/* Model family */}
        <Field label="Model family">
          <div className="grid grid-cols-2 gap-1.5">
            {meta.families.map((f) => (
              <button
                key={f.key}
                onClick={() => set({ family: f.key })}
                className={`rounded-md border px-2 py-1.5 text-[12px] font-medium transition-colors ${
                  config.family === f.key
                    ? "border-accent bg-accent/8 text-accent-ink"
                    : "border-line-strong bg-surface text-ink-2 hover:border-muted"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-muted">{familyNote}</p>
        </Field>

        {/* --- CUSTOM EQUATION mode --- */}
        {isCustom ? (
          <>
            <Field label={`Variables — assign a symbol to a dataset column`}>
              <div className="space-y-1.5">
                {config.variables.map((v, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      className="field-input !w-14 text-center font-mono"
                      value={v.symbol}
                      onChange={(e) => setVar(i, { symbol: e.target.value.replace(/[^A-Za-z_0-9]/g, "") })}
                      aria-label="symbol"
                    />
                    <span className="text-muted">=</span>
                    <select
                      className="field-input flex-1"
                      value={v.column}
                      onChange={(e) => setVar(i, { column: e.target.value })}
                    >
                      <option value="">— choose a variable —</option>
                      {meta.predictors.map((p) => (
                        <option key={p.key} value={p.key}>
                          {p.label} {p.unit ? `(${p.unit})` : ""}
                        </option>
                      ))}
                    </select>
                    <button
                      className="px-1 text-[13px] text-muted hover:text-court"
                      onClick={() => removeVar(i)}
                      aria-label="remove"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <button
                className="mt-2 rounded-md border border-line-strong bg-raised px-2.5 py-1 text-[12px] font-medium text-ink-2 hover:border-muted"
                onClick={addVar}
              >
                + Add variable
              </button>
            </Field>

            <Field label="Your equation — predicts the player count for each community">
              <div className="mb-2 flex flex-wrap gap-1.5">
                {EXAMPLE_EQUATIONS.map((ex) => (
                  <button
                    key={ex.label}
                    onClick={() => set({ equation: ex.equation, variables: ex.vars })}
                    className="rounded-md border border-line-strong bg-raised px-2.5 py-1 text-[11.5px] font-medium text-ink-2 hover:border-muted"
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
              <div className="flex items-start gap-2">
                <span className="mt-2 shrink-0 font-mono text-[13px] text-court">predicted&nbsp;=</span>
                <textarea
                  className="field-input min-h-[76px] resize-y border-accent/30 bg-accent/[0.04] font-mono !text-[13px] leading-relaxed"
                  rows={3}
                  spellCheck={false}
                  placeholder="e.g.  0.00002 * x + 0.5 * z - 0.1 * y"
                  value={config.equation}
                  onChange={(e) => set({ equation: e.target.value })}
                />
              </div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-muted">
                Symbols {validVars.map((v) => v.symbol).join(", ") || "(none yet)"} · numbers ·{" "}
                <span className="font-mono">+ − * / ^ ( )</span>. Raw column units (income in $,
                rates in %). Nothing is fitted — the formula is evaluated exactly as typed.
              </p>
              <details className="mt-1 text-[12px] text-muted">
                <summary className="cursor-pointer select-none hover:text-ink-2">functions</summary>
                <span className="mt-1 block font-mono text-[11px] leading-relaxed">
                  {meta.equation_functions.join("  ·  ")}
                </span>
              </details>
            </Field>
          </>
        ) : (
          <Field label={`Predictors (X) — ${config.predictors.length} selected`}>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {PRESETS.filter((p) => p.predictors.every((k) => meta.predictors.some((m) => m.key === k))).map((p) => (
                <button
                  key={p.name}
                  onClick={() => set({ predictors: p.predictors })}
                  className="rounded-md border border-line-strong bg-raised px-2.5 py-1 text-[12px] font-medium text-ink-2 hover:border-muted"
                >
                  {p.name}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {meta.predictors.map((p) => {
                const on = config.predictors.includes(p.key);
                const noise = p.key.startsWith("noise_");
                return (
                  <span
                    key={p.key}
                    title={p.description}
                    data-on={on}
                    onClick={() => togglePredictor(p.key)}
                    className={`chip ${
                      on && noise ? "!border-court !bg-court/10 !text-court" : ""
                    }`}
                  >
                    {on ? "✓" : "+"} {p.label}
                  </span>
                );
              })}
            </div>
          </Field>
        )}

        {/* Years */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Training years">
            <div className="flex flex-wrap gap-1.5">
              {meta.years.map((y) => (
                <span
                  key={y}
                  data-on={config.trainYears.includes(y)}
                  onClick={() => toggleTrainYear(y)}
                  className={`chip font-mono ${y === config.testYear ? "pointer-events-none opacity-35" : ""}`}
                >
                  {y}
                </span>
              ))}
            </div>
          </Field>
          <Field label="Validation year (held out)">
            <div className="flex flex-wrap gap-1.5">
              {meta.years.map((y) => (
                <span
                  key={y}
                  onClick={() => set({ testYear: y, trainYears: config.trainYears.filter((v) => v !== y) })}
                  className={`chip font-mono ${
                    y === config.testYear ? "!border-positive !bg-positive/10 !text-positive" : ""
                  }`}
                >
                  {y}
                </span>
              ))}
            </div>
          </Field>
        </div>

        {isCustom ? (
          <p className="text-xs text-muted">
            The equation is compared against actual NCAA counts on the validation year, and
            evaluated separately on every year (Analyze → Cross-validation) to check it holds up.
          </p>
        ) : (
          <div className="space-y-2.5">
            <label className="flex items-center gap-2 text-[12px] text-ink-2">
              <input
                type="checkbox"
                className="accent-accent"
                checked={config.standardize}
                onChange={(e) => set({ standardize: e.target.checked })}
              />
              Standardize predictors (z-score, training stats only)
            </label>
            <label className="flex flex-wrap items-center gap-2 text-[12px] text-ink-2">
              <input
                type="checkbox"
                className="accent-accent"
                checked={config.cvFolds > 0}
                onChange={(e) => set({ cvFolds: e.target.checked ? 5 : 0 })}
              />
              Cross-validate
              {config.cvFolds > 0 && (
                <select
                  className="field-input !w-auto !py-1 !text-[12px]"
                  value={config.cvFolds}
                  onChange={(e) => set({ cvFolds: Number(e.target.value) })}
                >
                  {[3, 5, 10].map((k) => (
                    <option key={k} value={k}>{k}-fold</option>
                  ))}
                </select>
              )}
              <span className="text-muted">+ leave-one-year-out</span>
            </label>
          </div>
        )}

        {yearsOverlap && (
          <p className="text-[12px] text-court">Validation year cannot also be a training year.</p>
        )}
        {error && <p className="rounded-md border border-court/30 bg-court/10 px-2.5 py-2 text-[12px] text-court">{error}</p>}

        <button className="btn btn-primary w-full !py-2.5 !text-[13px]" disabled={!canRun} onClick={onRun}>
          {running
            ? isCustom ? "Evaluating…" : "Estimating…"
            : isCustom ? "Evaluate equation  →" : "Run model  →"}
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="eyebrow mb-2">{label}</div>
      {children}
    </div>
  );
}
