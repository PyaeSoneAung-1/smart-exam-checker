"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { dashboardApi } from "@/lib/api";
import type { TeacherDashboard } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, FileText, Users, BarChart3, ClipboardList, ArrowRight, PenLine } from "lucide-react";
import Link from "next/link";
import { RadialGauge } from "@/components/charts/ModernCharts";
import { MotionCard, staggerContainer, fadeUp } from "@/components/shared/motion";

const stats = [
  { key: "total_subjects", label: "Subjects", icon: BookOpen, color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-600/10 dark:bg-emerald-500/15" },
  { key: "total_exams_created", label: "Exams", icon: FileText, color: "text-emerald-500 dark:text-emerald-300", bg: "bg-emerald-500/10 dark:bg-emerald-500/15" },
  { key: "total_students", label: "Students", icon: Users, color: "text-teal-500 dark:text-teal-300", bg: "bg-teal-500/10 dark:bg-teal-500/15" },
  { key: "total_submissions", label: "Submissions", icon: ClipboardList, color: "text-green-500 dark:text-green-300", bg: "bg-green-500/10 dark:bg-green-500/15" },
] as const;

function scoreTone(score: number) {
  if (score >= 8) return { cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400", label: "Excellent" };
  if (score >= 6) return { cls: "bg-teal-500/15 text-teal-600 dark:text-teal-400", label: "Good" };
  if (score >= 4) return { cls: "bg-amber-500/15 text-amber-600 dark:text-amber-400", label: "Fair" };
  return { cls: "bg-red-500/15 text-red-600 dark:text-red-400", label: "Weak" };
}

export default function TeacherDashboardPage() {
  const [data, setData] = useState<TeacherDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await dashboardApi.getTeacher();
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex items-center gap-4"
      >
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 ring-2 ring-emerald-500/30">
          <PenLine className="h-7 w-7" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Teacher Dashboard</h1>
          <p className="text-sm text-muted-foreground">Your subjects, students &amp; recent activity</p>
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
              <Card className="overflow-hidden border transition-all hover:shadow-lg hover:-translate-y-1 hover:border-emerald-500/40 duration-300">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{s.label}</p>
                      <p className="mt-1 text-3xl font-bold tracking-tight">{d[s.key as keyof TeacherDashboard] as number}</p>
                    </div>
                    <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${s.bg}`}>
                      <Icon className={`h-5 w-5 ${s.color}`} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Charts + recent submissions */}
      <div className="grid gap-4 lg:grid-cols-3">
        <MotionCard delay={0.1}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" /> Average Score</CardTitle>
            <CardDescription>Class mean across your subjects</CardDescription>
          </CardHeader>
          <CardContent>
            <RadialGauge value={d.average_class_score} label="class avg" height={220} delay={0.12} />
          </CardContent>
        </MotionCard>

        <MotionCard delay={0.16} className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Submissions</CardTitle>
            <CardDescription>Latest answers from your students</CardDescription>
          </CardHeader>
          <CardContent>
            {d.recent_submissions && d.recent_submissions.length > 0 ? (
              <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate="show"
                className="space-y-2"
              >
                {d.recent_submissions.slice(0, 6).map((s, idx) => {
                  const tone = scoreTone(s.total_score);
                  return (
                    <motion.div
                      key={idx}
                      variants={fadeUp}
                      className="flex items-center justify-between gap-3 rounded-xl border bg-card p-3 transition-colors hover:bg-muted/40"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-600/10 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                          {s.student_name?.charAt(0) ?? "S"}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{s.student_name || `Student #${s.student_id}`}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className={tone.cls}>{tone.label}</Badge>
                        <span className="text-sm font-bold tabular-nums">{s.total_score.toFixed(1)}</span>
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            ) : (
              <p className="py-12 text-center text-sm text-muted-foreground">No submissions yet</p>
            )}
          </CardContent>
        </MotionCard>
      </div>

      {/* Quick actions */}
      <MotionCard delay={0.22}>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Manage your work</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2 sm:grid-cols-2">
          {[
            { href: "/teacher/exams", icon: FileText, label: "Manage Exams" },
            { href: "/teacher/marks", icon: BarChart3, label: "Student Marks" },
            { href: "/teacher/students", icon: Users, label: "My Students" },
            { href: "/teacher/plagiarism", icon: ClipboardList, label: "Plagiarism Check" },
          ].map((a) => {
            const Icon = a.icon;
            return (
              <Link
                key={a.href}
                href={a.href}
                className="group flex items-center justify-between rounded-xl border bg-card p-3 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-emerald-500/40 duration-300"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600/10 text-emerald-600 dark:text-emerald-400">
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className="text-sm font-medium">{a.label}</span>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </Link>
            );
          })}
        </CardContent>
      </MotionCard>
    </div>
  );
}
