"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface StatsCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  trend?: { value: number; label: string };
  className?: string;
  gradient?: string;
}

export default function StatsCard({ icon: Icon, label, value, trend, className, gradient }: StatsCardProps) {
  return (
    <Card className={cn("overflow-hidden transition-all hover:shadow-md", className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight">{value}</p>
            {trend && (
              <div className="mt-2 flex items-center gap-1 text-xs">
                {trend.value > 0 ? (
                  <TrendingUp className="h-3 w-3 text-emerald-500" />
                ) : trend.value < 0 ? (
                  <TrendingDown className="h-3 w-3 text-red-500" />
                ) : (
                  <Minus className="h-3 w-3 text-muted-foreground" />
                )}
                <span className={trend.value > 0 ? "text-emerald-600" : trend.value < 0 ? "text-red-600" : "text-muted-foreground"}>
                  {trend.value > 0 ? "+" : ""}{trend.value}%
                </span>
                <span className="text-muted-foreground">{trend.label}</span>
              </div>
            )}
          </div>
          <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10", gradient)}>
            <Icon className="h-6 w-6 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
