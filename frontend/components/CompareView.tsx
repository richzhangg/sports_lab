"use client";
import { memo } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { SavedExperiment } from "@/lib/api";
import { fmt, fmtPct, specSummary } from "@/lib/format";

const AXIS = { fontSize: 11, fill: "#8b867a" };

function CompareViewImpl({
  runs,
  onRemove,
  onClear,
  onOpen,
}: {
  runs: SavedExperiment[];
  onRemove: (id: string) => void;
  onClear: () => void;
  onOpen: (id: string) => void;
}) {
  if (runs.length === 0)
    return (
      <div className="card">
        <div className="card-h text-[12px]">4 · Compare Models</div>
        <div className="card-b text-sm text-muted">
          Run a model, then “Save to comparison”. Saved runs persist on the server (they survive
          page reloads and restarts) and are listed here side-by-side so you can see which family /
          predictor set generalizes best to the held-out year.
        </div>
      </div>
    );

  const isCount = runs.every((r) => r.test_metrics.mean_poisson_deviance != null);
  const pk = isCount ? "mean_poisson_deviance" : "rmse";
  const chartData = runs.map((r, i) => ({
    name: `M${i + 1}`,
    train: r.train_metrics[pk as "rmse"] ?? r.train_metrics.rmse,
    validation: r.test_metrics[pk as "rmse"] ?? r.test_metrics.rmse,
    cv: r.cross_validation?.kfold?.held_out?.[pk]?.mean ?? null,
  }));

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="card-h justify-between">
          <span className="flex items-center gap-2.5"><span className="step-no">04</span> Compare models <span className="text-muted">· {runs.length} saved</span></span>
          <button className="btn btn-ghost !py-1 !px-2.5 text-[12px]" onClick={onClear}>Clear all</button>
        </div>
        <div className="card-b overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>#</th><th>Configuration</th>
                <th>Train {isCount ? "dev." : "RMSE"}</th>
                <th>Validation {isCount ? "dev." : "RMSE"}</th>
                <th>k-fold CV (mean±sd)</th>
                <th>LOYO CV</th>
                <th>vs. baseline</th>
                <th>Overfit gap</th>
                <th>AIC</th><th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r, i) => {
                const kf = r.cross_validation?.kfold?.held_out?.[pk];
                const loyo = r.cross_validation?.leave_one_year_out?.held_out?.[pk];
                return (
                  <tr key={r.id}>
                    <td>
                      <button className="font-semibold text-accent hover:underline" onClick={() => onOpen(r.id)}>
                        M{i + 1}
                      </button>
                    </td>
                    <td>
                      {specSummary(r.spec)}
                      <div className="text-xs text-muted">{r.spec.predictors.join(", ")}</div>
                    </td>
                    <td>{fmt(r.train_metrics[pk as "rmse"] ?? r.train_metrics.rmse)}</td>
                    <td className="font-semibold">{fmt(r.test_metrics[pk as "rmse"] ?? r.test_metrics.rmse)}</td>
                    <td>{kf ? `${fmt(kf.mean)} ± ${fmt(kf.sd, 2)}` : "—"}</td>
                    <td>{loyo ? fmt(loyo.mean) : "—"}</td>
                    <td className={(r.vs_baseline?.rmse_improvement_pct ?? 0) > 0 ? "text-positive" : "text-court"}>
                      {fmtPct(r.vs_baseline?.rmse_improvement_pct)}
                    </td>
                    <td className={r.overfitting.flag ? "font-semibold text-amber-700" : ""}>
                      {fmtPct(r.overfitting.test_minus_train_pct)}
                    </td>
                    <td>{fmt(r.diagnostics.aic as number, 1)}</td>
                    <td>
                      <button className="text-xs text-court hover:underline" onClick={() => onRemove(r.id)}>
                        remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-muted">
            Click a model number to reopen its full results. Best out-of-sample model = lowest{" "}
            <b>validation {isCount ? "deviance" : "RMSE"}</b> and lowest CV mean. A model with a low
            training error but high validation / CV error (large positive overfit gap) is memorizing
            the training years.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-h text-[12px]">Training vs. validation vs. cross-validated {isCount ? "deviance" : "RMSE"}</div>
        <div className="card-b">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
              <CartesianGrid stroke="#eef2f7" />
              <XAxis dataKey="name" tick={AXIS} />
              <YAxis tick={AXIS} />
              <Tooltip formatter={(v: number) => fmt(v)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="train" name="Training" fill="#cbd5e1" />
              <Bar dataKey="validation" name="Validation year" fill="#1d4ed8" />
              <Bar dataKey="cv" name="k-fold CV" fill="#0f766e" />
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-1 text-xs text-muted">
            Bars where validation / CV ≫ training indicate overfitting.
          </p>
        </div>
      </div>
    </div>
  );
}

const CompareView = memo(CompareViewImpl);
export default CompareView;
