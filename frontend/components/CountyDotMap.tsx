"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { geoAlbersUsa } from "d3-geo";

type County = { fips: string; name: string; lat: number; lon: number; players: number };
type Geo = { counties: County[]; max_players: number; year: number };

// d3.geoAlbersUsa()'s default scale/translate is tuned for exactly 960×600.
const W = 960;
const H = 600;

export default function CountyDotMap({
  interactive = true,
  className = "",
}: {
  interactive?: boolean;
  className?: string;
}) {
  const [geo, setGeo] = useState<Geo | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; c: County } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    fetch("/api/geo")
      .then((r) => r.json())
      .then(setGeo)
      .catch(() => {});
  }, []);

  const model = useMemo(() => {
    if (!geo) return null;
    const projection = geoAlbersUsa();
    const pts = geo.counties
      .map((c) => {
        const p = projection([c.lon, c.lat]);
        return p ? { c, x: p[0], y: p[1] } : null;
      })
      .filter((d): d is { c: County; x: number; y: number } => !!d);

    const withPlayers = pts.filter((d) => d.c.players > 0).sort((a, b) => a.c.players - b.c.players);
    const zeros = pts.filter((d) => d.c.players === 0);
    const rmax = geo.max_players || 1;
    const radius = (n: number) => 1.8 + Math.sqrt(n / rmax) * 13;
    return { withPlayers, zeros, radius };
  }, [geo]);

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
            return (
              <g key={d.c.fips}>
                <circle cx={d.x} cy={d.y} r={model.radius(d.c.players) + 5} fill="url(#dotGlow)" opacity={0.55} />
                <circle
                  cx={d.x}
                  cy={d.y}
                  r={model.radius(d.c.players)}
                  fill="#2a6df4"
                  fillOpacity={0.92}
                  stroke="#fffdf8"
                  strokeWidth={0.6}
                  className={`dot-pop ${big ? "dot-pulse" : ""}`}
                  style={{ animationDelay: `${350 + i * 3}ms` }}
                  onMouseEnter={
                    interactive
                      ? (e) => {
                          const r = svgRef.current!.getBoundingClientRect();
                          setHover({
                            x: ((e.clientX - r.left) / r.width) * W,
                            y: ((e.clientY - r.top) / r.height) * H,
                            c: d.c,
                          });
                        }
                      : undefined
                  }
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
