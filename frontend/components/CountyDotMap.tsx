"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { geoAlbersUsa } from "d3-geo";
import { getGeo, type GeoCounty, type GeoPayload } from "@/lib/api";

// d3.geoAlbersUsa()'s default scale/translate is tuned for exactly 960×600.
const W = 960;
const H = 600;

export default function CountyDotMap({
  year,
  interactive = true,
  onSelect,
  selectedFips,
  onData,
  className = "",
}: {
  year?: number;
  interactive?: boolean;
  onSelect?: (fips: string) => void;
  selectedFips?: string | null;
  onData?: (p: GeoPayload) => void;
  className?: string;
}) {
  const [geo, setGeo] = useState<GeoPayload | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; c: GeoCounty } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    let live = true;
    getGeo(year)
      .then((p) => {
        if (!live) return;
        setGeo(p);
        onData?.(p);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year]);

  const model = useMemo(() => {
    if (!geo) return null;
    const projection = geoAlbersUsa();
    const pts = geo.counties
      .map((c) => {
        const p = projection([c.lon, c.lat]);
        return p ? { c, x: p[0], y: p[1] } : null;
      })
      .filter((d): d is { c: GeoCounty; x: number; y: number } => !!d);
    const withPlayers = pts.filter((d) => d.c.players > 0).sort((a, b) => a.c.players - b.c.players);
    const zeros = pts.filter((d) => d.c.players === 0);
    const rmax = geo.max_players || 1;
    const radius = (n: number) => 1.8 + Math.sqrt(n / rmax) * 13;
    return { withPlayers, zeros, radius };
  }, [geo]);

  const toLocal = (e: React.MouseEvent) => {
    const r = svgRef.current!.getBoundingClientRect();
    return { x: ((e.clientX - r.left) / r.width) * W, y: ((e.clientY - r.top) / r.height) * H };
  };

  return (
    <div className={`relative ${className}`}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full overflow-visible"
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <radialGradient id="dotGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#3f83f8" stopOpacity="0.85" />
            <stop offset="65%" stopColor="#2a6df4" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#2a6df4" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* every county — a faint constellation that reads as the map */}
        <g fill="#c3bcac">
          {model?.zeros.map((d, i) => (
            <circle
              key={d.c.fips}
              cx={d.x}
              cy={d.y}
              r={0.9}
              className="dot-in"
              style={{ animationDelay: `${(i % 70) * 7}ms` }}
            />
          ))}
        </g>

        {/* counties that produce D1 players */}
        <g>
          {model?.withPlayers.map((d, i) => {
            const big = d.c.players >= (geo!.max_players || 1) * 0.4;
            const isSel = selectedFips === d.c.fips;
            return (
              <g key={d.c.fips}>
                <circle
                  cx={d.x}
                  cy={d.y}
                  r={model.radius(d.c.players) + (isSel ? 9 : 5)}
                  fill="url(#dotGlow)"
                  opacity={isSel ? 0.9 : 0.55}
                />
                <circle
                  cx={d.x}
                  cy={d.y}
                  r={model.radius(d.c.players)}
                  fill={isSel ? "#c05327" : "#2a6df4"}
                  fillOpacity={0.92}
                  stroke="#fffdf8"
                  strokeWidth={isSel ? 1.4 : 0.6}
                  className={`dot-pop ${big && !isSel ? "dot-pulse" : ""}`}
                  style={{
                    animationDelay: `${350 + i * 3}ms`,
                    cursor: onSelect ? "pointer" : "default",
                  }}
                  onMouseEnter={interactive ? (e) => setHover({ ...toLocal(e), c: d.c }) : undefined}
                  onMouseMove={interactive ? (e) => setHover({ ...toLocal(e), c: d.c }) : undefined}
                  onClick={onSelect ? () => onSelect(d.c.fips) : undefined}
                />
              </g>
            );
          })}
        </g>

        {hover && (
          <g transform={`translate(${hover.x}, ${hover.y})`} pointerEvents="none">
            <g transform="translate(10, -30)">
              <rect x={0} y={0} width={Math.max(96, hover.c.name.length * 6.6)} height={30} rx={5} fill="#1b1a15" />
              <text x={8} y={12} fill="#fffdf8" fontSize={9} fontFamily="var(--font-mono)">
                {hover.c.name}
              </text>
              <text x={8} y={24} fill="#a9c4f7" fontSize={9} fontFamily="var(--font-mono)">
                {hover.c.players} D1 player{hover.c.players === 1 ? "" : "s"}
                {onSelect ? " · click to open" : ""}
              </text>
            </g>
          </g>
        )}
      </svg>

      <style jsx>{`
        .dot-in {
          opacity: 0;
          animation: dotIn 0.8s ease forwards;
        }
        .dot-pop {
          opacity: 0;
          transform-box: fill-box;
          transform-origin: center;
          animation: dotPop 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }
        .dot-pulse {
          animation:
            dotPop 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards,
            dotPulse 3.6s ease-in-out 1.2s infinite;
        }
        @keyframes dotIn {
          to {
            opacity: 0.6;
          }
        }
        @keyframes dotPop {
          0% {
            opacity: 0;
            transform: scale(0);
          }
          100% {
            opacity: 1;
            transform: scale(1);
          }
        }
        @keyframes dotPulse {
          0%,
          100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.13);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .dot-in,
          .dot-pop,
          .dot-pulse {
            animation: none;
            opacity: 1;
          }
          .dot-in {
            opacity: 0.6;
          }
        }
      `}</style>
    </div>
  );
}
