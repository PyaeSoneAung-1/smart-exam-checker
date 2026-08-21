"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number;
  max: number;
  className?: string;
}

export default function ScoreBadge({ score, max, className }: ScoreBadgeProps) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  let colorClass = "";

  if (pct >= 80) {
    colorClass = "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 border-emerald-200";
  } else if (pct >= 60) {
    colorClass = "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200";
  } else if (pct >= 40) {
    colorClass = "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 border-amber-200";
  } else {
    colorClass = "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200";
  }

  return (
    <Badge variant="outline" className={cn("font-mono font-semibold", colorClass, className)}>
      {score}/{max} ({Math.round(pct)}%)
    </Badge>
  );
}
