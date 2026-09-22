"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import CountyDotMap from "@/components/CountyDotMap";
import { getCounty, type CountyDetail, type GeoPayload } from "@/lib/api";
import { fmt, fmtInt } from "@/lib/format";

export default function MapPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [geo, setGeo] = useState<GeoPayload | null>(null);
  const [year, setYear] = useState<number | undefined>(undefined);
  const [detail, setDetail] = useState<CountyDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // open a county from a ?county= deep link (search results, shared URLs)
  useEffect(() => {
    const c = new URLSearchParams(window.location.search).get("county");
    if (c) setSelected(c);
  }, []);

  const select = useCallback((fips: string | null) => {
    setSelected(fips);
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", fips ? `/map?county=${fips}` : "/map");
    }
  }, []);

  useEffect(() => {
    if (!selected) {
      setDetail(null);
      return;
    }
    setLoadingDetail(true);
    let live = true;
    getCounty(selected)
      .then((d) => live && setDetail(d))
      .finally(() => {
        if (live) setLoadingDetail(false);
      });
    return () => {
      live = false;
    };
  }, [selected]);

  const topCounties = useMemo(
    () =>
      geo
        ? [...geo.counties]
            .filter((c) => c.players > 0)
            .sort((a, b) => b.players - a.players)
            .slice(0, 12)
        : [],
    [geo],
  );

  return (
    <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow mb-1.5">The Map</p>
          <h1 className="text-[26px] leading-tight text-ink sm:text-[30px]">
            Every county that sends a player to Division&nbsp;I tennis.
          </h1>
          <p className="mt-2 max-w-xl text-[13px] leading-relaxed text-ink-2">
            Point size is the number of NCAA D1 tennis players from that community. Click a point to
            see who they are and the county&apos;s socioeconomic profile.
          </p>
        </div>
        {geo && geo.years.length > 1 && (
          <div className="flex items-center gap-1.5">
            <span className="eyebrow mr-1">roster year</span>
            {geo.years.map((y) => {
              const active = year === y || (year === undefined && geo.year === y);
              return (
                <button
                  key={y}
                  onClick={() => setYear(y)}
                  className={`rounded-md px-2.5 py-1 font-mono text-[12px] font-medium transition-colors ${
                    active ? "bg-ink text-paper" : "border border-line-strong text-muted hover:text-ink"
                  }`}
                >
                  {y}
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_minmax(340px,400px)]">
        <div className="card">
          <div className="card-b">
            <CountyDotMap
              year={year}
              onSelect={(f) => select(f)}
              selectedFips={selected}
              onData={setGeo}
              className="mx-auto max-w-[880px]"
            />
            <p className="mt-1 text-center font-mono text-[10.5px] text-muted">
              {geo ? `${fmtInt(geo.total_players)} players · ${geo.counties.filter((c) => c.players > 0).length} counties` : "loading…"}
              {year ? ` · ${year} rosters` : ""}
            </p>
          </div>
        </div>

        <div className="lg:sticky lg:top-20 lg:self-start">
          <AnimatePresence mode="wait">
            {selected ? (
              <motion.div
                key={selected}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
              >
                <CountyPanel
                  detail={detail}
                  year={year ?? geo?.year ?? undefined}
                  loading={loadingDetail}
                  onClose={() => select(null)}
                />
              </motion.div>
            ) : (
              <motion.div
                key="prompt"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="card"
              >
                <div className="card-h">Top communities</div>
                <div className="card-b">
                  <p className="mb-3 text-[12.5px] leading-relaxed text-muted">
                    Click any glowing point on the map, or pick one below.
                  </p>
                  <ol className="space-y-0.5">
                    {topCounties.map((c, i) => (
                      <li key={c.fips}>
                        <button
                          onClick={() => select(c.fips)}
                          className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-[13px] hover:bg-raised"
                        >
                          <span className="flex items-center gap-2.5">
                            <span className="w-4 font-mono text-[11px] text-muted">{i + 1}</span>
                            {c.name}
                          </span>
                          <span className="font-mono text-[12px] text-accent-ink">{c.players}</span>
                        </button>
                      </li>
                    ))}
                  </ol>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}

function CountyPanel({
  detail,
  year,
  loading,
  onClose,
}: {
  detail: CountyDetail | null;
  year?: number;
  loading: boolean;
  onClose: () => void;
}) {
  if (loading && !detail)
    return (
      <div className="card">
        <div className="card-b text-sm text-muted">Loading…</div>
      </div>
    );
  if (!detail || !detail.found)
    return (
      <div className="card">
        <div className="card-b flex items-center justify-between text-sm text-muted">
          <span>County not found.</span>
          <button className="text-[12px] text-accent-ink hover:underline" onClick={onClose}>
            back
          </button>
        </div>
      </div>
    );

  const latest =
    (year != null ? detail.by_year?.find((r) => r.year === year) : undefined) ??
    detail.by_year?.[detail.by_year.length - 1];
  const allPlayers = detail.players ?? [];
  const players =
    year != null ? allPlayers.filter((p) => p.seasons.includes(year)) : allPlayers;
  const rows: [string, string][] = latest
    ? [
        ["Population", fmtInt(latest.population)],
        ["Youth population (0-17)", fmtInt(latest.youth_population)],
        ["Median household income", latest.median_income == null ? "—" : `$${fmtInt(latest.median_income)}`],
        ["Poverty rate", latest.poverty_rate == null ? "—" : `${fmt(latest.poverty_rate, 1)}%`],
        ["Bachelor's degree or higher", latest.pct_bachelors == null ? "—" : `${fmt(latest.pct_bachelors, 1)}%`],
        ["Tennis courts / 100k", fmt(latest.tennis_courts_per_100k, 1)],
        ["Population density (/sq mi)", fmt(latest.pop_density, 1)],
      ]
    : [];

  return (
    <div className="card">
      <div className="card-h justify-between">
        <span className="font-display text-[16px]">{detail.name}</span>
        <button className="text-[12px] text-muted hover:text-ink" onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="card-b space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="font-display text-[34px] leading-none text-ink">
            {year != null ? players.length : detail.player_count}
          </span>
          <span className="text-[12px] text-muted">
            NCAA D1 tennis player{(year != null ? players.length : detail.player_count) === 1 ? "" : "s"} from this
            county{year != null ? ` · ${year} rosters` : " · all seasons"}
          </span>
        </div>

        <div>
          <p className="eyebrow mb-1.5">Community profile{latest ? ` · ${latest.year}` : ""}</p>
          <dl className="divide-y divide-line text-[12.5px]">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 py-1.5">
                <dt className="text-muted">{k}</dt>
                <dd className="font-mono tabular-nums text-ink">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="max-h-[42vh] overflow-auto">
          <p className="eyebrow mb-1.5">The players ({players.length})</p>
          <ul className="space-y-1.5">
            {players.map((p, i) => (
              <li key={`${p.player_name}-${p.school}-${i}`} className="rounded-md bg-raised px-2.5 py-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[13px] font-medium text-ink">{p.player_name}</span>
                  <span className="font-mono text-[10.5px] text-muted">{p.seasons.join(" · ")}</span>
                </div>
                <div className="mt-0.5 text-[11.5px] text-muted">
                  {p.school} · {p.gender === "M" ? "Men's" : "Women's"} · {p.conference}
                </div>
                <div className="text-[11px] text-muted">from {p.hometown_raw}</div>
              </li>
            ))}
            {!players.length && (
              <li className="text-[12px] text-muted">
                {year != null
                  ? `No players on ${year} rosters resolved to this county.`
                  : "No players resolved to this county."}
              </li>
            )}
          </ul>
        </div>

        <Link href="/data" className="btn btn-ghost w-full !py-1.5 text-[12px]">
          Search all players →
        </Link>
      </div>
    </div>
  );
}
