"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { dashboardApi } from "@/lib/api";
import type { AdminDashboard } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Users, BookOpen, FileText, Shield, GraduationCap,
  TrendingUp, CheckCircle, UserCog, ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { AnimatedDonut, RadialGauge } from "@/components/charts/ModernCharts";
import { MotionCard, staggerContainer, fadeUp } from "@/components/shared/motion";

/* Role-coordinated violet palette (solid, no gradients) */
const CHART_PALETTE = ["#7c3aed", "#a78bfa", "#c4b5fd"];

const stats = [
  { key: "total_users", label: "Total Users", icon: Users, href: "/admin/users", color: "text-violet-600 dark:text-violet-400", bg: "bg-violet-600/10 dark:bg-violet-500/15" },
  { key: "total_students", label: "Students", icon: GraduationCap, href: "/admin/users", color: "text-violet-500 dark:text-violet-300", bg: "bg-violet-500/10 dark:bg-violet-500/15" },
  { key: "total_teachers", label: "Teachers", icon: UserCog, href: "/admin/users", color: "text-purple-500 dark:text-purple-300", bg: "bg-purple-500/10 dark:bg-purple-500/15" },
  { key: "total_subjects", label: "Subjects", icon: BookOpen, href: "/admin/subjects", color: "text-purple-400 dark:text-purple-300", bg: "bg-purple-400/10 dark:bg-purple-500/15" },
] as const;

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await dashboardApi.getAdmin();
        setData(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-foreground" />
      </div>
    );
  }

  const d = data!;
  const adminCount = Math.max(0, d.total_users - d.total_students - d.total_teachers);
  const breakdown = [
    { name: "Students", value: d.total_students },
    { name: "Teachers", value: d.total_teachers },
    { name: "Admins", value: adminCount },
  ].filter((x) => x.value > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center gap-4"
      >
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-violet-600 text-white shadow-lg shadow-violet-600/30 ring-2 ring-violet-500/30">
          <Shield className="h-7 w-7" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
          <p className="text-sm text-muted-foreground">System-wide overview &amp; controls</p>
        </div>
      </motion.div>

      {/* Stat cards */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <motion.div key={s.key} variants={fadeUp}>
              <Link href={s.href}>
                <Card className="group cursor-pointer overflow-hidden border transition-all hover:shadow-lg hover:-translate-y-1 hover:border-violet-500/40 duration-300">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm text-muted-foreground">{s.label}</p>
                        <p className="mt-1 text-3xl font-bold tracking-tight">{d[s.key as keyof AdminDashboard] as number}</p>
                      </div>
                      <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${s.bg}`}>
                        <Icon className={`h-5 w-5 ${s.color}`} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Charts row */}
      <div className="grid gap-4 lg:grid-cols-2">
        <MotionCard delay={0.05}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Users className="h-5 w-5 text-violet-600 dark:text-violet-400" /> User Breakdown</CardTitle>
            <CardDescription>Role distribution across the platform</CardDescription>
          </CardHeader>
          <CardContent>
            {breakdown.length > 0 ? (
              <>
                <AnimatedDonut data={breakdown} height={240} delay={0.1} palette={CHART_PALETTE} />
                <div className="mt-3 flex flex-wrap justify-center gap-4">
                  {breakdown.map((b, i) => (
                    <div key={b.name} className="flex items-center gap-2 text-sm">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: CHART_PALETTE[i % CHART_PALETTE.length] }} />
                      <span className="text-muted-foreground">{b.name}</span>
                      <span className="font-semibold">{b.value}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="py-12 text-center text-sm text-muted-foreground">No users yet</p>
            )}
          </CardContent>
        </MotionCard>

        <MotionCard delay={0.12}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5 text-violet-600 dark:text-violet-400" /> Average Score</CardTitle>
            <CardDescription>System-wide mean performance</CardDescription>
          </CardHeader>
          <CardContent>
            <RadialGauge value={d.average_system_score} label="avg score" height={220} delay={0.2} />
          </CardContent>
        </MotionCard>
      </div>

      {/* Quick actions */}
      <MotionCard delay={0.18}>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Jump straight to management</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {[
            { href: "/admin/users", icon: Users, label: "Manage Users", desc: `${d.total_users} accounts` },
            { href: "/admin/subjects", icon: BookOpen, label: "Manage Subjects", desc: `${d.total_subjects} subjects` },
            { href: "/admin/exams", icon: FileText, label: "Manage Exams", desc: `${d.total_exams} exams` },
            { href: "/admin/settings", icon: Shield, label: "System Settings", desc: "Weights &amp; thresholds" },
          ].map((a) => {
            const Icon = a.icon;
            return (
              <Link
                key={a.href}
                href={a.href}
                className="group flex items-center justify-between rounded-xl border bg-card p-4 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-violet-500/40 duration-300"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-600/10 text-violet-600 dark:text-violet-400">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-medium">{a.label}</p>
                    <p className="text-xs text-muted-foreground">{a.desc}</p>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </Link>
            );
          })}
        </CardContent>
      </MotionCard>

      {/* Footer note */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="flex items-center gap-2 rounded-xl border bg-muted/30 p-4 text-sm text-muted-foreground"
      >
        <CheckCircle className="h-4 w-4 text-emerald-500" />
        {d.recent_registrations} new registration{d.recent_registrations === 1 ? "" : "s"} in the last 7 days.
      </motion.div>
    </div>
  );
}
