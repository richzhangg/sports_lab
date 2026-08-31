"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import ConfigPanel, { type Config, toRequest } from "@/components/ConfigPanel";
import ResultsView from "@/components/ResultsView";
import { getMetadata, runModel, saveExperiment, type Metadata, type RunResult } from "@/lib/api";
import { specSummary } from "@/lib/format";

const KEY = "sol.lab.v1";

export default function LabPage() {
  const router = useRouter();
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [metaErr, setMetaErr] = useState<string | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [runErr, setRunErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedCount, setSavedCount] = useState(0);
  const restored = useRef(false);

  useEffect(() => {
    getMetadata()
      .then((m) => {
        setMeta(m);
        let stored: { config?: Config; result?: RunResult } = {};
        try {
          stored = JSON.parse(sessionStorage.getItem(KEY) || "{}");
        } catch {}
        setConfig(
          stored.config ?? {
            outcome: m.count_outcome,
            predictors: ["median_income", "tennis_courts_per_100k"],
            family: "custom",
            trainYears: m.years.slice(0, -1),
            testYear: m.years[m.years.length - 1],
            standardize: true,
            cvFolds: 0,
            equation: "(p / 1000000) * (0.4 + 0.02 * b + 0.15 * t)",
            variables: [
              { symbol: "p", column: "population" },
              { symbol: "b", column: "pct_bachelors" },
              { symbol: "t", column: "tennis_courts_per_100k" },
            ],
          },
        );
        if (stored.result) setResult(stored.result);
        restored.current = true;
      })
      .catch((e) => setMetaErr(String(e)));
    fetch("/api/experiments")
      .then((r) => r.json())
      .then((d) => setSavedCount(Array.isArray(d) ? d.length : 0))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!restored.current || !config) return;
    try {
      sessionStorage.setItem(KEY, JSON.stringify({ config, result }));
    } catch {}
  }, [config, result]);

  const run = async () => {
    if (!config) return;
    setRunning(true);
    setRunErr(null);
    try {
      setResult(await runModel(toRequest(config)));
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const saveCurrent = async () => {
    if (!result) return;
    setSaving(true);
    try {
      await saveExperiment(`M${savedCount + 1}`, result);
      router.push("/compare");
    } finally {
      setSaving(false);
    }
  };

  const setConfigCb = useCallback((c: Config) => setConfig(c), []);

  if (metaErr)
    return (
      <Wrap>
        <div className="card">
          <div className="card-b text-sm text-court">
            Could not reach the modeling API ({metaErr}). Start the backend:{" "}
            <code>cd backend &amp;&amp; ./venv/bin/uvicorn main:app --port 8000</code>
          </div>
        </div>
      </Wrap>
    );
  if (!meta || !config)
    return (
      <Wrap>
        <div className="card">
          <div className="card-b text-sm text-muted">Loading the lab…</div>
        </div>
      </Wrap>
    );

  return (
    <Wrap>
      <div className="mb-6">
        <p className="eyebrow mb-1.5">The Lab</p>
        <h1 className="text-[26px] leading-tight text-ink sm:text-[30px]">
          Build a model, run it against the held-out year.
        </h1>
      </div>
      <div className="grid gap-5 lg:grid-cols-[minmax(370px,430px)_1fr]">
        <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <ConfigPanel
            meta={meta}
            config={config}
            setConfig={setConfigCb}
            onRun={run}
            running={running}
            error={runErr}
          />
          {result && (
            <div className="card">
              <div className="card-b space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="eyebrow">current model</span>
                  <button
                    className="btn btn-ghost shrink-0 !py-1.5 text-[12px]"
                    disabled={saving}
                    onClick={saveCurrent}
                  >
                    {saving ? "Saving…" : "Save to comparison →"}
                  </button>
                </div>
                <p className="truncate font-mono text-[12px] text-ink-2">
                  {specSummary(result.spec)}
                </p>
              </div>
            </div>
          )}
        </div>

        <motion.div
          key={result ? "res" : "empty"}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 0.61, 0.24, 1] }}
        >
          <ResultsView run={result} />
        </motion.div>
      </div>
    </Wrap>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8">{children}</main>;
}
