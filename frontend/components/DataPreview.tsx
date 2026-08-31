"use client";
import { useEffect, useState } from "react";
import { getPreview, getRosters, type SourceInfo, type RostersInfo } from "@/lib/api";

const cell = (v: unknown): string => {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString();
    return Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(3);
  }
  return String(v);
};

export default function DataPreview() {
  const [data, setData] = useState<{ columns: string[]; rows: Record<string, unknown>[]; source: SourceInfo } | null>(
    null,
  );
  const [rosters, setRosters] = useState<RostersInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getPreview().then(setData).catch((e) => setErr(String(e)));
    getRosters().then(setRosters).catch(() => {});
  }, []);

  if (err) return <div className="card"><div className="card-b text-sm text-court">{err}</div></div>;
  if (!data) return <div className="card"><div className="card-b text-sm text-muted">Loading…</div></div>;

  return (
    <div className="space-y-4">
      {/* ---- the NCAA side of the data ---- */}
      {rosters?.available && (
        <div className="card">
          <div className="card-h justify-between">
            <span className="flex items-center gap-2.5"><span className="step-no">Y</span> NCAA D1 tennis rosters — the outcome data</span>
            <span className="font-mono text-[11px] text-muted">
              {rosters.player_seasons?.toLocaleString()} player-seasons · {rosters.schools} programs
            </span>
          </div>
          <div className="card-b space-y-3">
            <p className="text-[13px] leading-relaxed text-ink-2">{rosters.description}</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Player-seasons scraped" value={rosters.player_seasons?.toLocaleString()} />
              <Stat label="D1 programs" value={String(rosters.schools)} />
              <Stat label="Conferences" value={String(rosters.conferences?.length)} />
              <Stat
                label="Placed in a U.S. county"
                value={rosters.placed_in_a_us_county?.toLocaleString()}
              />
            </div>
            <p className="text-xs text-muted">
              Seasons:{" "}
              {rosters.seasons &&
                Object.entries(rosters.seasons)
                  .map(([y, n]) => `${y} (${n})`)
                  .join(" · ")}
              {rosters.by_gender && (
                <>
                  {"  ·  "}
                  {Object.entries(rosters.by_gender)
                    .map(([g, n]) => `${g === "M" ? "men" : g === "W" ? "women" : g}: ${n}`)
                    .join(", ")}
                </>
              )}
            </p>
            <div className="max-h-[360px] overflow-auto">
              <table>
                <thead>
                  <tr>{rosters.columns?.map((c) => <th key={c}>{c}</th>)}</tr>
                </thead>
                <tbody>
                  {rosters.sample?.map((row, i) => (
                    <tr key={i}>
                      {rosters.columns?.map((c) => (
                        <td key={c} className={`whitespace-nowrap ${c === "source_url" ? "max-w-[220px] truncate text-muted" : c === "hometown_raw" || c === "player_name" || c === "school" ? "" : "font-mono text-[12px]"}`}>
                          {cell(row[c])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted">
              Random sample of {rosters.sample?.length} rows. Every row records the exact team page it
              was read from.
            </p>
          </div>
        </div>
      )}

      {/* ---- the modelling panel (NCAA joined to Census + OSM) ---- */}
      <div className="card">
        <div className="card-h justify-between">
          <span className="flex items-center gap-2.5">
            <span className="step-no">X·Y</span> Modelling panel — one row per county-year
          </span>
          <span className="font-mono text-[11px] text-muted">
            {data.source.n_communities.toLocaleString()} {data.source.is_real ? "counties" : "communities"} ×{" "}
            {data.source.years.length} years = {data.source.n_rows.toLocaleString()} rows
          </span>
        </div>
        <div className="card-b space-y-3">
          <div
            className={`rounded-md border px-3 py-2 text-xs ${
              data.source.is_real
                ? "border-positive/30 bg-positive/10 text-positive"
                : "border-amber-400/40 bg-amber-50 text-amber-900"
            }`}
          >
            <b>{data.source.is_real ? "RESEARCH DATA" : "DEMO DATASET — SYNTHETIC"}:</b>{" "}
            {data.source.citation}
            {data.source.notes ? (
              <div className="mt-1.5 border-t border-current/20 pt-1.5">
                <b>Limitations:</b> {data.source.notes}
              </div>
            ) : null}
          </div>
          <p className="text-xs text-muted">
            The <span className="font-mono tabular-nums">d1_players</span> column is the NCAA roster count above,
            geocoded to each county; the other columns are the Census / OpenStreetMap predictors for
            that county and year.
          </p>
          <div className="max-h-[420px] overflow-auto">
            <table>
              <thead>
                <tr>{data.columns.map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {data.rows.map((row, i) => (
                  <tr key={i}>
                    {data.columns.map((c) => (
                      <td key={c} className="whitespace-nowrap font-mono text-[12px]">{cell(row[c])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value?: string }) {
  return (
    <div className="rounded-md border border-line bg-raised p-2.5">
      <div className="text-[10.5px] leading-tight text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-[17px] font-medium tabular-nums text-ink">{value ?? "—"}</div>
    </div>
  );
}
