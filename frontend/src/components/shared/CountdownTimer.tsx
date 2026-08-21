"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Clock, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface CountdownTimerProps {
  initialSeconds: number;
  onTimeEnd: () => void;
  onTick?: (secondsLeft: number) => void;
  className?: string;
}

export default function CountdownTimer({
  initialSeconds,
  onTimeEnd,
  onTick,
  className,
}: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState(initialSeconds);
  const hasEnded = useRef(false);

  useEffect(() => {
    if (timeLeft <= 0 && !hasEnded.current) {
      hasEnded.current = true;
      onTimeEnd();
    }
  }, [timeLeft, onTimeEnd]);

  useEffect(() => {
    if (timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        const next = prev - 1;
        onTick?.(next);
        return next;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeft, onTick]);

  const progress = initialSeconds > 0 ? (timeLeft / initialSeconds) * 100 : 0;
  const isWarning = timeLeft <= 300 && timeLeft > 60;
  const isCritical = timeLeft <= 60;

  const formatTime = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center gap-2">
        {isCritical ? (
          <AlertTriangle className="h-5 w-5 text-red-500 animate-pulse" />
        ) : (
          <Clock className={cn("h-5 w-5", isWarning ? "text-amber-500" : "text-muted-foreground")} />
        )}
        <span
          className={cn(
            "text-lg font-mono font-semibold tracking-wider",
            isCritical && "text-red-600 dark:text-red-400 animate-pulse",
            isWarning && "text-amber-600 dark:text-amber-400",
            !isWarning && !isCritical && "text-foreground"
          )}
        >
          {formatTime(timeLeft)}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-1000",
            isCritical ? "bg-red-500" : isWarning ? "bg-amber-500" : "bg-primary"
          )}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
