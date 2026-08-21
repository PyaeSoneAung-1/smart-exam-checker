"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

/**
 * Reads the chart CSS variables from :root so recharts SVGs recolor
 * automatically when the dark/light theme changes.
 * Returns ready-to-use color strings.
 */
export function useChartColors() {
  const { resolvedTheme } = useTheme();
  const [colors, setColors] = useState<Record<string, string>>({});

  useEffect(() => {
    const read = () => {
      const root = document.documentElement;
      const get = (name: string) =>
        getComputedStyle(root).getPropertyValue(name).trim();
      setColors({
        chart1: get("--chart-1"),
        chart2: get("--chart-2"),
        chart3: get("--chart-3"),
        chart4: get("--chart-4"),
        chart5: get("--chart-5"),
        card: get("--card"),
        border: get("--border"),
        muted: get("--muted"),
        mutedFg: get("--muted-foreground"),
        foreground: get("--foreground"),
        accent1: get("--accent-1"),
        accent2: get("--accent-2"),
      });
    };
    read();
    // Re-read after the theme class has been applied.
    const t = setTimeout(read, 60);
    return () => clearTimeout(t);
  }, [resolvedTheme]);

  return colors;
}

/** Shared tooltip content style derived from theme tokens. */
export function tooltipStyle(c: Record<string, string>) {
  return {
    backgroundColor: c.card || "#fff",
    border: `1px solid ${c.border || "rgba(0,0,0,0.1)"}`,
    borderRadius: "12px",
    color: c.foreground || "#000",
    fontSize: "12px",
    boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
  };
}

export const axisTickStyle = (c: Record<string, string>) => ({
  fill: c.mutedFg || "#888",
  fontSize: 12,
});
