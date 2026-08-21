"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { dashboardApi, examsApi, answersApi, questionsApi } from "@/lib/api";
import type { StudentDashboard, Exam, Answer } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  GraduationCap, ClipboardCheck, TrendingUp, ArrowUpRight, ArrowDownRight,
  Trophy, FileText, ArrowRight, Award, CheckCircle,
} from "lucide-react";
import Link from "next/link";
import { MotionCard, staggerContainer, fadeUp } from "@/components/shared/motion";

export default function StudentDashboardPage() {
  const [data, setData] = useState<StudentDashboard | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [completedExamIds, setCompletedExamIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [dash, examRes] = await Promise.all([
          dashboardApi.getStudent(),
          examsApi.getAll({ limit: 100 }),
        ]);
        setData(dash.data);
        setExams(examRes.data.items ?? []);

        try {
          const [answerRes, qRes] = await Promise.all([
            answersApi.getMyAnswers({ limit: 10000 }),
            questionsApi.getAll({ limit: 500 }),
          ]);
          const answers: Answer[] = answerRes.data.items || [];
          const questions = qRes.data.items || [];
          const questionToExam: Record<number, number> = {};
          questions.forEach((q) => { questionToExam[q.id] = q.exam_id; });
          const completed = new Set<number>();
          for (const answer of answers) {
            const examId = questionToExam[answer.question_id];
            if (examId) completed.add(examId);
          }
          setCompletedExamIds(completed);
        } catch {
          // New student — no answers yet
        }
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
  const availableExams = exams.filter((e) => e.is_active && !completedExamIds.has(e.id));
  const completedExams = exams.filter((e) => completedExamIds.has(e.id));

  const statCards = [
    { label: "Exams Taken", value: d.total_exams_taken, icon: ClipboardCheck, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-600/10 dark:bg-blue-500/15" },
    { label: "Average Score", value: d.average_score.toFixed(1), icon: TrendingUp, color: "text-blue-500 dark:text-blue-300", bg: "bg-blue-500/10 dark:bg-blue-500/15" },
    { label: "Highest", value: d.highest_score.toFixed(1), icon: ArrowUpRight, color: "text-sky-500 dark:text-sky-300", bg: "bg-sky-500/10 dark:bg-sky-500/15" },
    { label: "Lowest", value: d.lowest_score.toFixed(1), icon: ArrowDownRight, color: "text-indigo-500 dark:text-indigo-300", bg: "bg-indigo-500/10 dark:bg-indigo-500/15" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-wrap items-center justify-between gap-3"
      >
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-600/30 ring-2 ring-blue-500/30">
            <GraduationCap className="h-7 w-7" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Student Dashboard</h1>
            <p className="text-sm text-muted-foreground">Your performance at a glance</p>
          </div>
        </div>
        {availableExams.length > 0 && (
          <Link
            href="/student/exams"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-blue-600/30 transition-transform hover:-translate-y-0.5"
          >
            <FileText className="h-4 w-4" /> {availableExams.length} exam{availableExams.length === 1 ? "" : "s"} available
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </motion.div>

      {/* Stat cards */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        {statCards.map((s) => {
          const Icon = s.icon;
          return (
            <motion.div key={s.label} variants={fadeUp}>
              <Card className="overflow-hidden border transition-all hover:shadow-lg hover:-translate-y-1 hover:border-blue-500/40 duration-300">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{s.label}</p>
                      <p className="mt-1 text-3xl font-bold tracking-tight tabular-nums">{s.value}</p>
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

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2">
        <MotionCard delay={0.1}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" /> Available Exams</CardTitle>
            <CardDescription>Exams you haven&apos;t taken yet</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {availableExams.length > 0 ? (
              availableExams.slice(0, 4).map((e) => (
                <Link
                  key={e.id}
                  href={`/student/exams/${e.id}`}
                  className="group flex items-center justify-between rounded-xl border bg-card p-3 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-blue-500/40 duration-300"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{e.title}</p>
                    <p className="text-xs text-muted-foreground">{e.total_marks} marks · {e.time_limit_minutes} min</p>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1" />
                </Link>
              ))
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">No exams available right now.</p>
            )}
            {completedExams.length > 0 && (
              <div className="pt-2">
                <p className="mb-2 text-xs font-medium text-muted-foreground">Completed</p>
                {completedExams.slice(0, 4).map((e) => (
                  <Link
                    key={e.id}
                    href="/student/results"
                    className="group mb-2 flex items-center justify-between rounded-xl border bg-muted/30 p-3 transition-all hover:shadow-md hover:-translate-y-0.5 duration-300"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <CheckCircle className="h-4 w-4 shrink-0 text-emerald-500" />
                      <p className="truncate text-sm font-medium">{e.title}</p>
                    </div>
                    <Badge variant="secondary" className="shrink-0">Done</Badge>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </MotionCard>

        <MotionCard delay={0.16}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Award className="h-5 w-5 text-blue-600 dark:text-blue-400" /> Your Results</CardTitle>
            <CardDescription>Review detailed feedback</CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/student/results"
              className="group flex h-full min-h-[120px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-blue-500/30 bg-blue-500/[0.03] p-6 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-blue-500/50 duration-300"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600/10 text-blue-600 dark:text-blue-400">
                <Trophy className="h-6 w-6" />
              </div>
              <p className="text-sm font-medium">View all my results</p>
              <p className="text-xs text-muted-foreground">{d.total_exams_taken} exam{d.total_exams_taken === 1 ? "" : "s"} taken</p>
            </Link>
          </CardContent>
        </MotionCard>
      </div>
    </div>
  );
}
