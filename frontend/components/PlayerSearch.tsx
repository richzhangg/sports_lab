"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { searchPlayers, type PlayerHit } from "@/lib/api";

export default function PlayerSearch() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<PlayerHit[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);
  const seq = useRef(0);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) {
      setHits([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    setTouched(true);
    const mine = ++seq.current;
    const t = setTimeout(() => {
      searchPlayers(term, 80)
        .then((r) => {
          if (mine !== seq.current) return;
          setHits(r.results);
          setTotal(r.total);
        })
        .catch(() => {})
        .finally(() => mine === seq.current && setLoading(false));
    }, 220);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="card">
      <div className="card-h justify-between">
        <span className="flex items-center gap-2.5">
          <span className="step-no">?</span> Search players
        </span>
        {total > 0 && (
          <span className="font-mono text-[11px] text-muted">
            {hits.length < total ? `${hits.length} of ${total}` : total} match{total === 1 ? "" : "es"}
          </span>
        )}
      </div>
      <div className="card-b space-y-3">
        <div className="relative">
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Name, school, or hometown — e.g. “Bradenton”, “Ohio State”, “Garcia”"
            className="field-input !py-2.5 pr-9"
          />
          {loading && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[10px] text-muted">
              …
            </span>
          )}
          {q && !loading && (
            <button
              onClick={() => setQ("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[13px] text-muted hover:text-ink"
              aria-label="clear"
            >
              ✕
            </button>
          )}
        </div>

        {touched && q.trim().length >= 2 && !loading && hits.length === 0 && (
          <p className="text-[13px] text-muted">No players match “{q.trim()}”.</p>
        )}

        {hits.length > 0 && (
          <div className="max-h-[520px] overflow-auto">
            <table>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>School</th>
                  <th>Conference</th>
                  <th>Hometown</th>
                  <th>County</th>
                  <th>Seasons</th>
                </tr>
              </thead>
              <tbody>
                {hits.map((p, i) => (
                  <tr key={`${p.player_name}-${p.school}-${i}`}>
                    <td className="whitespace-nowrap font-medium">{p.player_name}</td>
                    <td className="whitespace-nowrap text-ink-2">
                      {p.school}
                      <span className="ml-1 text-muted">{p.gender === "M" ? "M" : "W"}</span>
                    </td>
                    <td className="whitespace-nowrap text-muted">{p.conference}</td>
                    <td className="whitespace-nowrap text-muted">{p.hometown_raw}</td>
                    <td className="whitespace-nowrap">
                      {p.county_fips ? (
                        <Link
                          href={`/map?county=${p.county_fips}`}
                          className="text-accent-ink hover:underline"
                        >
                          {p.county_name}
                        </Link>
                      ) : (
                        <span className="text-muted">— intl.</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap font-mono text-[11px] text-muted">
                      {p.seasons.join(" ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="text-[11.5px] leading-relaxed text-muted">
          {total > hits.length
            ? `Showing the first ${hits.length}. Narrow the search to see the rest. `
            : ""}
          A player who transferred appears once per school. County links open that community on the
          map.
        </p>
      </div>
    </div>
  );
}
