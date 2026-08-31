// Chart tokens — categorical hues from the validated data-viz palette, in fixed
// slot order (never cycled). Chrome matches the app's warm paper surface.

export const SERIES = {
  s1: "#2a78d6", // blue   — predicted / model
  s2: "#eb6834", // orange — residuals / secondary
  s3: "#1baf7a", // aqua   — cross-validation
} as const;

export const CHART = {
  grid: "#e6e1d4",
  axisLine: "#d6d0be",
  ref: "#b8b2a2",
  tick: { fontSize: 11, fill: "#8b867a", fontFamily: "var(--font-mono)" },
  muteFill: "#d8d2c2", // non-significant bar
  observed: "#8b867a", // actual NCAA counts, recessive
} as const;

export const tooltipStyle = {
  borderRadius: 8,
  border: "1px solid #e6e1d4",
  background: "#fffdf8",
  boxShadow: "0 6px 24px -12px rgba(27,26,21,0.18)",
  fontSize: 12,
  fontFamily: "var(--font-mono)",
} as const;
