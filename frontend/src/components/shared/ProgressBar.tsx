"use client";

import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
}

export default function ProgressBar({ value, max = 100, className, showLabel = false, size = "md" }: ProgressBarProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);
  const heightClass = size === "sm" ? "h-1.5" : size === "lg" ? "h-4" : "h-2.5";
  
  const colorClass = pct >= 80
    ? "bg-emerald-500"
    : pct >= 60
      ? "bg-blue-500"
      : pct >= 40
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className={cn("w-full", className)}>
      {showLabel && (
        <div className="mb-1 flex justify-between text-xs text-muted-foreground">
          <span>{Math.round(pct)}%</span>
        </div>
      )}
      <div className={cn("w-full overflow-hidden rounded-full bg-muted", heightClass)}>
        <div
          className={cn("rounded-full transition-all duration-500", heightClass, colorClass)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
