"use client";
import { memo } from "react";
import {
  CartesianGrid, Cell, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis, Bar, BarChart,
} from "recharts";
import type { RunResult, CrossValidation, EquationInfo, RunSpec } from "@/lib/api";
import { fmt, fmtP, fmtPct, FAMILY_LABEL } from "@/lib/format";
import { SERIES, CHART, tooltipStyle } from "@/lib/charts";

const AXIS = CHART.tick;

// Heavy (thousands of scatter points + many charts). Memoized so typing in the
// config panel — which lives in a sibling and re-renders the page — does not
// re-render these charts. Only a new `run` object triggers a redraw.
function ResultsViewImpl({ run }: { run: RunResult | null }) {
  if (!run) return <EmptyState />;

  const { spec, test_metrics: tm, train_metrics: trm, diagnostics: d, overfitting: of } = run;
  const isCount = tm.mean_poisson_deviance !== undefined && tm.mean_poisson_deviance !== null;
  const isCustom = spec.family === "custom";
  const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
  const pctl = (arr: number[], q: number) => {
    const s = arr.filter(finite).sort((a, b) => a - b);
    return s.length ? s[Math.max(0, Math.floor((s.length - 1) * q))] : 0;
  };
  const rnd = (v: number) => {
    const p = Math.pow(10, Math.max(0, Math.floor(Math.log10(Math.max(v, 1)))));
    return Math.ceil(Math.max(v, 1) / p) * p;
  };
  // symmetric, outlier-resistant frame for the scatter plots
  const scaleMax = rnd(
    Math.max(
      pctl(run.predicted_vs_observed.map((p) => p.observed), 1),
      pctl(run.predicted_vs_observed.map((p) => p.predicted), 0.99),
      4,
    ) * 1.05,
  );
  const offChart = run.predicted_vs_observed.filter((p) => p.predicted > scaleMax).length;
  const clamp = (v: number) => Math.min(Math.max(v, 0), scaleMax);
  const pvo = run.predicted_vs_observed.map((p) => ({
    community_name: p.community_name,
    observed: clamp(p.observed),
    predicted: clamp(p.predicted),
    _pred: p.predicted,
  }));

  const resBand = rnd(pctl(run.residuals.map((r) => Math.abs(r.raw_residual)), 0.98) * 1.25 || 4);
  const residualPts = run.residuals.map((r) => ({
    community_name: r.community_name,
    fitted: clamp(r.predicted),
    residual: Math.max(-resBand, Math.min(resBand, r.raw_residual)),
  }));

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="card-h justify-between">
          <span className="flex items-center gap-2.5">
            <span className="step-no">03</span> {FAMILY_LABEL[spec.family]}
          </span>
          <span className="font-mono text-[11px] text-muted">
            train {spec.train_years.join("/")} · n={spec.n_train.toLocaleString()} &nbsp;/&nbsp;
            test {spec.test_year} · n={spec.n_test.toLocaleString()}
          </span>
        </div>
        <div className="card-b space-y-4">
          {of.flag && (
            <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              <b>Possible overfitting.</b> Validation {of.primary_metric.replace(/_/g, " ")} is{" "}
              {fmtPct(of.test_minus_train_pct)} worse than training ({fmt(of.train_value)} →{" "}
              {fmt(of.test_value)}). {of.note}
            </div>
          )}

          {/* Metric cards: out-of-sample first */}
          <div>
            <SectionLabel>Out-of-sample validation ({spec.test_year}) — the model has not seen this year</SectionLabel>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Metric label="RMSE" value={fmt(tm.rmse)} accent />
              <Metric label="MAE" value={fmt(tm.mae)} accent />
              {isCount ? (
                <Metric label="Mean Poisson deviance" value={fmt(tm.mean_poisson_deviance)} accent />
              ) : (
                <Metric label="R² (response)" value={fmt(tm.r2_response)} accent />
              )}
              <Metric label="Pred–obs correlation" value={fmt(tm.pearson_corr)} accent />
            </div>
          </div>
          <div>
            <SectionLabel>Training fit ({spec.train_years.join("/")}) — for comparison only</SectionLabel>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Metric label="RMSE" value={fmt(trm.rmse)} />
              <Metric label="MAE" value={fmt(trm.mae)} />
              {isCount ? (
                <Metric label="Mean Poisson deviance" value={fmt(trm.mean_poisson_deviance)} />
              ) : (
                <Metric label="R²" value={fmt(trm.r2_response)} />
              )}
              <Metric label="Bias (mean resid.)" value={fmt(trm.mean_error_bias)} />
            </div>
          </div>

          {/* vs baseline */}
          {run.vs_baseline && run.baseline && (
            <div className="rounded-md bg-raised px-3 py-2 text-xs">
              <b>vs. baseline</b> ({run.baseline.description}): validation RMSE{" "}
              {fmt(run.baseline.test_metrics.rmse)} → {fmt(tm.rmse)} (
              <span className={(run.vs_baseline.rmse_improvement_pct ?? 0) > 0 ? "text-positive" : "text-court"}>
                {fmtPct(run.vs_baseline.rmse_improvement_pct)} {(run.vs_baseline.rmse_improvement_pct ?? 0) > 0 ? "better" : "worse"}
              </span>
              ). Predictors {(run.vs_baseline.rmse_improvement_pct ?? 0) > 0 ? "add" : "do not add"} out-of-sample signal.
            </div>
          )}
        </div>
      </div>

      {isCustom && run.equation && <EquationCard eq={run.equation} spec={spec} />}

      {run.cross_validation && (
        <CrossValidationCard cv={run.cross_validation} />
      )}

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Predicted vs. observed (validation year)">
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 8, right: 12, bottom: 24, left: 4 }}>
              <CartesianGrid stroke={CHART.grid} />
              <XAxis
                type="number" dataKey="observed" name="Observed" domain={[0, scaleMax]} tick={AXIS}
                label={{ value: "Observed", position: "bottom", fontSize: 11, fill: "#8b867a" }}
              />
              <YAxis
                type="number" dataKey="predicted" name="Predicted" domain={[0, scaleMax]} tick={AXIS}
                label={{ value: "Predicted", angle: -90, position: "insideLeft", fontSize: 11, fill: "#8b867a" }}
              />
              <ZAxis range={[24, 24]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                formatter={(v: number) => fmt(v, 2)}
                labelFormatter={() => ""}
                content={({ payload }) =>
                  payload && payload.length ? (
                    <div className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-[11px] font-mono shadow-lift">
                      <div className="font-medium">{payload[0].payload.community_name}</div>
                      <div>observed {fmt(payload[0].payload.observed, 1)}</div>
                      <div>predicted {fmt(payload[0].payload._pred, 2)}</div>
                    </div>
                  ) : null
                }
              />
              <ReferenceLine
                segment={[{ x: 0, y: 0 }, { x: scaleMax, y: scaleMax }]}
                stroke={CHART.ref} strokeDasharray="4 4"
              />
              <Scatter data={pvo} fill={SERIES.s1} fillOpacity={0.5} />
            </ScatterChart>
          </ResponsiveContainer>
          <p className="mt-1 text-xs text-muted">Dashed line = perfect prediction (y = x).{offChart > 0 ? ` ${offChart} outlier${offChart===1?"":"s"} beyond the axis.` : ""}</p>
        </ChartCard>

        <ChartCard title="Residuals vs. fitted (validation year)">
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 8, right: 12, bottom: 24, left: 4 }}>
              <CartesianGrid stroke={CHART.grid} />
              <XAxis
                type="number" dataKey="fitted" name="Fitted" tick={AXIS}
                label={{ value: "Fitted value", position: "bottom", fontSize: 11, fill: "#8b867a" }}
              />
              <YAxis
                type="number" dataKey="residual" domain={[-resBand, resBand]} tick={AXIS}
                label={{
                  value: "Residual (obs − fit)",
                  angle: -90, position: "insideLeft", fontSize: 11, fill: "#8b867a",
                }}
              />
              <ZAxis range={[24, 24]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={({ payload }) =>
                  payload && payload.length ? (
                    <div className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-[11px] font-mono shadow-lift">
                      <div className="font-medium">{payload[0].payload.community_name}</div>
                      <div>fitted {fmt(payload[0].payload.fitted, 2)}</div>
                      <div>residual {fmt(payload[0].payload.residual, 2)}</div>
                    </div>
                  ) : null
                }
              />
              <ReferenceLine y={0} stroke={CHART.ref} />
              <Scatter data={residualPts} fill={SERIES.s2} fillOpacity={0.5} />
            </ScatterChart>
          </ResponsiveContainer>
          <p className="mt-1 text-xs text-muted">
            Look for structure (funnels, curves) — it signals a mis-specified model.
          </p>
        </ChartCard>

        {!isCustom && (
        <ChartCard title="Coefficients (standardized scale)">
          <ResponsiveContainer width="100%" height={Math.max(150, run.coefficients.filter((c) => c.term !== "const").length * 40)}>
            <BarChart
              layout="vertical"
              data={run.coefficients.filter((c) => c.term !== "const")}
              margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
              barCategoryGap="28%"
            >
              <CartesianGrid stroke={CHART.grid} horizontal={false} />
              <XAxis type="number" tick={AXIS} />
              <YAxis type="category" dataKey="term" width={132} tick={AXIS} />
              <Tooltip formatter={(v: number) => fmt(v)} contentStyle={tooltipStyle} />
              <ReferenceLine x={0} stroke={CHART.ref} />
              <Bar dataKey="estimate" fill={SERIES.s1} isAnimationActive={false} radius={2}>
                {run.coefficients
                  .filter((c) => c.term !== "const")
                  .map((c, i) => (
                    <Cell key={i} fill={(c.p_value ?? 1) < 0.05 ? SERIES.s1 : CHART.muteFill} />
                  ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-1 text-xs text-muted">Solid = p &lt; 0.05. Full table below.</p>
        </ChartCard>
        )}

        <ChartCard title="Geographic distribution (by state, validation year)">
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={run.geo_distribution.slice(0, 14)} margin={{ top: 8, right: 12, bottom: 24, left: 4 }}>
              <CartesianGrid stroke={CHART.grid} />
              <XAxis dataKey="state" tick={AXIS} interval={0} angle={-40} textAnchor="end" height={40} />
              <YAxis tick={AXIS} />
              <Tooltip formatter={(v: number) => fmt(v, 1)} contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="observed" fill={CHART.observed} fillOpacity={0.45} name="Observed" />
              <Line dataKey="predicted" stroke={SERIES.s1} strokeWidth={2} dot={false} name="Predicted" />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Coefficient table */}
      {!isCustom && (
      <div className="card">
        <div className="card-h text-[12px]">Model coefficients &amp; uncertainty</div>
        <div className="card-b overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Term</th>
                <th>Estimate</th>
                <th>Std. error</th>
                <th>95% CI</th>
                <th>p-value</th>
                {isCount && <th>Rate ratio (95% CI)</th>}
              </tr>
            </thead>
            <tbody>
              {run.coefficients.map((c) => (
                <tr key={c.term}>
                  <td className="font-medium">{c.term}</td>
                  <td>{fmt(c.estimate)}</td>
                  <td>{fmt(c.std_error)}</td>
                  <td>
                    {c.ci_low === null ? "—" : `[${fmt(c.ci_low, 2)}, ${fmt(c.ci_high, 2)}]`}
                  </td>
                  <td className={(c.p_value ?? 1) < 0.05 ? "font-semibold text-accent" : ""}>{fmtP(c.p_value)}</td>
                  {isCount && (
                    <td>
                      {c.rate_ratio === undefined
                        ? "—"
                        : `${fmt(c.rate_ratio, 2)} [${fmt(c.rate_ratio_ci_low, 2)}, ${fmt(
                            c.rate_ratio_ci_high, 2,
                          )}]`}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* Fit diagnostics */}
      <div className="card">
        <div className="card-h text-[12px]">{isCustom ? "Evaluation notes" : "Fit diagnostics (training data)"}</div>
        <div className="card-b grid grid-cols-2 gap-x-6 gap-y-2 text-[12.5px] sm:grid-cols-3">
          {Object.entries(d).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-line py-1">
              <span className="text-muted">{k.replace(/_/g, " ")}</span>
              <span className="font-mono tabular-nums text-ink">
                {typeof v === "number" ? fmt(v, 3) : String(v)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Residual table */}
      <div className="card">
        <div className="card-h text-[12px]">Largest residuals (validation year)</div>
        <div className="card-b overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Community</th><th>State</th><th>Observed</th><th>Predicted</th>
                <th>Residual</th><th>{isCount ? "Pearson resid." : "Std. resid."}</th>
              </tr>
            </thead>
            <tbody>
              {[...run.residuals]
                .sort((a, b) => Math.abs(b.raw_residual) - Math.abs(a.raw_residual))
                .slice(0, 12)
                .map((r) => (
                  <tr key={r.community_id}>
                    <td>{r.community_name}</td>
                    <td>{r.state}</td>
                    <td>{fmt(r.observed, 1)}</td>
                    <td>{fmt(r.predicted, 2)}</td>
                    <td className={r.raw_residual > 0 ? "text-positive" : "text-court"}>
                      {fmt(r.raw_residual, 2)}
                    </td>
                    <td>{fmt(r.pearson_residual, 2)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function EquationCard({ eq, spec }: { eq: EquationInfo; spec: RunSpec }) {
  return (
    <div className="card">
      <div className="card-h text-[12px]">Your equation</div>
      <div className="card-b space-y-3">
        <div className="rounded-md bg-slate-900 px-3 py-2 font-mono text-sm text-slate-100 overflow-x-auto">
          predicted&nbsp;=&nbsp;{eq.text}
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr><th>Symbol</th><th>Variable</th></tr>
            </thead>
            <tbody>
              {eq.bindings.map((b) => (
                <tr key={b.symbol}>
                  <td className="font-mono font-semibold">{b.symbol}</td>
                  <td>{b.column}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted">{eq.note}</p>
        {eq.negative_prediction_share > 0 && (
          <p className="rounded bg-amber-50 px-2 py-1.5 text-xs text-amber-900">
            {fmtPct(eq.negative_prediction_share * 100)} of communities got a <b>negative</b>{" "}
            predicted count from this equation (clipped to 0 for the count-scale error metrics).
            A player count can't be negative — consider a form that stays non-negative.
          </p>
        )}
      </div>
    </div>
  );
}

function CrossValidationCard({ cv }: { cv: CrossValidation }) {
  const pk = cv.primary_metric;
  const label = pk.replace(/_/g, " ");
  const kf = cv.kfold;
  const loyo = cv.leave_one_year_out;
  return (
    <div className="card">
      <div className="card-h text-[12px]">Cross-validation — {label}</div>
      <div className="card-b space-y-3 text-sm">
        {kf && (
          <div>
            <SectionLabel>{kf.scheme}</SectionLabel>
            <div className="flex flex-wrap gap-2">
              <Metric
                label={`held-out ${label} (mean ± sd)`}
                value={`${fmt(kf.held_out[pk]?.mean)} ± ${fmt(kf.held_out[pk]?.sd, 2)}`}
                accent
              />
              <Metric label={`in-fold ${label}`} value={fmt(kf.in_fold[pk]?.mean)} />
              <Metric
                label="held-out − in-fold"
                value={fmtPct(
                  kf.in_fold[pk] && kf.held_out[pk]
                    ? ((kf.held_out[pk].mean - kf.in_fold[pk].mean) / Math.abs(kf.in_fold[pk].mean)) * 100
                    : null,
                )}
              />
            </div>
          </div>
        )}
        {loyo && (
          <div>
            <SectionLabel>{loyo.scheme}</SectionLabel>
            <div className="overflow-x-auto">
              <table>
                <thead>
                  <tr>
                    <th>Held-out year</th><th>n</th><th>{label}</th><th>RMSE</th><th>MAE</th>
                  </tr>
                </thead>
                <tbody>
                  {loyo.per_year.map((y) => (
                    <tr key={String(y.year)}>
                      <td className="font-medium">{y.year}</td>
                      <td>{y.n_test}</td>
                      <td>{fmt(y[pk] as number)}</td>
                      <td>{fmt(y.rmse as number)}</td>
                      <td>{fmt(y.mae as number)}</td>
                    </tr>
                  ))}
                  <tr className="border-t-2 border-line font-semibold">
                    <td>mean</td>
                    <td />
                    <td>{fmt(loyo.held_out[pk]?.mean)}</td>
                    <td>{fmt(loyo.held_out.rmse?.mean)}</td>
                    <td>{fmt(loyo.held_out.mae?.mean)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="mt-1 text-xs text-muted">
              Each year is held out once and the model refit on the others — the most honest
              out-of-sample estimate. Big year-to-year swings mean the relationship isn't stable.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="eyebrow mb-2">{children}</div>;
}
function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div
      className={`rounded-md border p-2.5 ${
        accent ? "border-accent/25 bg-accent/[0.05]" : "border-line bg-raised"
      }`}
    >
      <div className="text-[10.5px] leading-tight text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-[17px] font-medium tabular-nums text-ink">{value}</div>
    </div>
  );
}
function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <div className="card-h text-[12px]">{title}</div>
      <div className="card-b">{children}</div>
    </div>
  );
}

function EmptyState() {
  const steps = [
    ["Choose an outcome & predictors", "or type your own equation — the model of representation you want to test."],
    ["Pick training years and one held-out validation year", "the model never sees the validation year while it's being built."],
    ["Run it", "the model predicts the held-out year; you see predicted vs. actual NCAA counts, residuals and error metrics."],
    ["Save and compare", "stack several models side by side and watch for overfitting."],
  ];
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-line bg-raised px-6 py-8">
        <p className="eyebrow mb-2">The research loop</p>
        <h2 className="max-w-md text-[22px] leading-snug text-ink">
          A model is a claim about why some communities produce more D1 players.
        </h2>
        <p className="mt-2 max-w-lg text-[13px] leading-relaxed text-ink-2">
          You build the claim; the app tests it against the real NCAA record and tells you where it
          holds and where it breaks.
        </p>
      </div>
      <ol className="divide-y divide-line">
        {steps.map(([t, d], i) => (
          <li key={i} className="flex gap-4 px-6 py-4">
            <span className="step-no mt-0.5">{String(i + 1).padStart(2, "0")}</span>
            <div>
              <div className="text-[13px] font-medium text-ink">{t}</div>
              <div className="mt-0.5 text-[12.5px] leading-relaxed text-muted">{d}</div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

const ResultsView = memo(ResultsViewImpl);
export default ResultsView;
