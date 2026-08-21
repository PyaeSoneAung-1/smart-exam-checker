"use client";

import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  AreaChart,
  Area,
  Line,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from "recharts";
import { useChartColors, tooltipStyle, axisTickStyle } from "./useChartColors";

/* ── Shared entrance animation wrapper ─────────────────────────────────── */
export function ChartFrame({
  children,
  delay = 0,
  height = 300,
}: {
  children: React.ReactNode;
  delay?: number;
  height?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      style={{ width: "100%", height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        {children as React.ReactElement}
      </ResponsiveContainer>
    </motion.div>
  );
}

/* ── Animated bar chart (horizontal or vertical) ───────────────────────── */
export function AnimatedBarChart({
  data,
  dataKey = "value",
  xKey = "label",
  horizontal = false,
  unit = "",
  height = 300,
  delay = 0,
}: {
  data: { label: string; value: number }[];
  dataKey?: string;
  xKey?: string;
  horizontal?: boolean;
  unit?: string;
  height?: number;
  delay?: number;
}) {
  const c = useChartColors();
  const palette = [c.chart1, c.chart2, c.chart3, c.chart4, c.chart5];

  return (
    <ChartFrame delay={delay} height={height}>
      <BarChart
        data={data}
        layout={horizontal ? "vertical" : "horizontal"}
        margin={{ top: 8, right: 16, left: horizontal ? 8 : 0, bottom: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={c.border || "#eee"} vertical={horizontal} horizontal={!horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" tick={axisTickStyle(c)} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey={xKey} tick={axisTickStyle(c)} width={120} axisLine={false} tickLine={false} />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} tick={axisTickStyle(c)} axisLine={false} tickLine={false} interval={0} angle={-12} textAnchor="end" height={50} />
            <YAxis tick={axisTickStyle(c)} axisLine={false} tickLine={false} />
          </>
        )}
        <Tooltip
          cursor={{ fill: c.muted || "rgba(0,0,0,0.04)" }}
          contentStyle={tooltipStyle(c)}
          formatter={(v) => [`${Number(v).toFixed(1)}${unit}`, "Value"]}
        />
        <Bar dataKey={dataKey} radius={horizontal ? [0, 8, 8, 0] : [8, 8, 0, 0]} isAnimationActive animationDuration={900}>
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length] || c.chart1} />
          ))}
        </Bar>
      </BarChart>
    </ChartFrame>
  );
}

/* ── Animated donut chart ──────────────────────────────────────────────── */
export function AnimatedDonut({
  data,
  height = 300,
  delay = 0,
  unit = "",
  palette,
}: {
  data: { name: string; value: number }[];
  height?: number;
  delay?: number;
  unit?: string;
  palette?: string[];
}) {
  const c = useChartColors();
  const colors = palette || [c.chart1, c.chart2, c.chart3, c.chart4, c.chart5];

  return (
    <ChartFrame delay={delay} height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius="58%"
          outerRadius="92%"
          paddingAngle={3}
          dataKey="value"
          stroke="none"
          isAnimationActive
          animationDuration={900}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={colors[i % colors.length] || c.chart1} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle(c)} formatter={(v, n) => [`${Number(v).toFixed(1)}${unit}`, n]} />
      </PieChart>
    </ChartFrame>
  );
}

/* ── Animated area chart (trends) ──────────────────────────────────────── */
export function AnimatedAreaChart({
  data,
  dataKey = "value",
  xKey = "label",
  height = 300,
  delay = 0,
  unit = "",
}: {
  data: { label: string; value: number }[];
  dataKey?: string;
  xKey?: string;
  height?: number;
  delay?: number;
  unit?: string;
}) {
  const c = useChartColors();
  const stroke = c.accent1 || "#6366f1";
  const fill = c.accent1 || "#6366f1";

  return (
    <ChartFrame delay={delay} height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={fill} stopOpacity={0.35} />
            <stop offset="100%" stopColor={fill} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={c.border || "#eee"} vertical={false} />
        <XAxis dataKey={xKey} tick={axisTickStyle(c)} axisLine={false} tickLine={false} minTickGap={12} />
        <YAxis tick={axisTickStyle(c)} axisLine={false} tickLine={false} width={36} />
        <Tooltip contentStyle={tooltipStyle(c)} formatter={(v) => [`${Number(v).toFixed(1)}${unit}`, "Score"]} />
        <Area
          type="monotone"
          dataKey={dataKey}
          stroke={stroke}
          strokeWidth={2.5}
          fill="url(#areaFill)"
          isAnimationActive
          animationDuration={1000}
          dot={{ r: 3, fill: stroke, strokeWidth: 0 }}
          activeDot={{ r: 5, strokeWidth: 0 }}
        />
      </AreaChart>
    </ChartFrame>
  );
}

/* ── Radial gauge (single % value) ─────────────────────────────────────── */
export function RadialGauge({
  value,
  label,
  height = 220,
  delay = 0,
}: {
  value: number; // 0..100
  label?: string;
  height?: number;
  delay?: number;
}) {
  const c = useChartColors();
  const data = [{ name: "score", value: Math.max(0, Math.min(100, value)) }];
  const color = value >= 75 ? "#22c55e" : value >= 50 ? c.accent1 || "#6366f1" : value >= 35 ? "#f59e0b" : "#ef4444";

  return (
    <ChartFrame delay={delay} height={height}>
      <RadialBarChart
        innerRadius="72%"
        outerRadius="100%"
        data={data}
        startAngle={90}
        endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
        <RadialBar
          background={{ fill: c.muted || "rgba(0,0,0,0.06)" }}
          dataKey="value"
          cornerRadius={20}
          fill={color}
          isAnimationActive
          animationDuration={1100}
        />
        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" style={{ fill: c.foreground || "#000" }}>
          <tspan fontSize="28" fontWeight="700">{value.toFixed(1)}%</tspan>
          {label ? <tspan x="50%" dy="22" fontSize="11" fill={c.mutedFg || "#888"}>{label}</tspan> : null}
        </text>
      </RadialBarChart>
    </ChartFrame>
  );
}

export { Line };
