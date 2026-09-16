"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { examsApi, settingsApi, asApiError } from "@/lib/api";
import { fetchMyResultsByExam } from "@/lib/exam-results";
import type { Exam } from "@/types";
import { DEFAULT_THRESHOLDS, parseNumberOr } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ClipboardList, ArrowRight } from "lucide-react";
import { toast } from "sonner";

interface ExamResult {
  examId: number;
  examTitle: string;
  subjectName: string;
  totalScore: number;
  maxMarks: number;
  percentage: number;
  passed: boolean;
  questionCount: number;
}

export default function StudentResultsPage() {
  const [examResults, setExamResults] = useState<ExamResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [passThreshold, setPassThreshold] = useState(DEFAULT_THRESHOLDS.pass_percentage);

  useEffect(() => {
    let cancelled = false;

    const fetchResults = async () => {
      try {
        const [examsRes, settingsRes] = await Promise.all([
          examsApi.getAll({ size: 100 }),
          settingsApi.getAll().catch(() => null),
        ]);

        const exams: Exam[] = examsRes.data.items || [];
        const threshold = parseNumberOr(
          settingsRes?.data?.pass_percentage,
          DEFAULT_THRESHOLDS.pass_percentage
        );

        // Only this student's answers, one targeted request per exam.
        const byExam = await fetchMyResultsByExam(exams);
        if (cancelled) return;

        setPassThreshold(threshold);

        const results: ExamResult[] = exams
          .filter((exam) => byExam.has(exam.id))
          .map((exam) => {
            const { totalScore, answeredCount } = byExam.get(exam.id)!;
            const maxMarks = exam.total_marks;
            const percentage = maxMarks > 0 ? (totalScore / maxMarks) * 100 : 0;
            return {
              examId: exam.id,
              examTitle: exam.title,
              subjectName: exam.subject?.name || `Subject #${exam.subject_id}`,
              totalScore,
              maxMarks,
              percentage,
              passed: percentage >= threshold,
              questionCount: answeredCount,
            };
          });

        setExamResults(results);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          toast.error(asApiError(err)?.message || "Failed to load results");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchResults();

    return () => {
      cancelled = true;
    };
  }, []);

  const getPercentageBadge = (pct: number) => {
    if (pct >= 70) return "bg-green-100 text-green-700";
    if (pct >= 50) return "bg-yellow-100 text-yellow-700";
    return "bg-red-100 text-red-700";
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <ClipboardList className="h-8 w-8" /> My Results
      </h1>

      <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800">
        <CardContent className="py-3 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Pass Threshold (from Settings)</span>
          <span className="text-lg font-bold text-blue-600">≥ {passThreshold}%</span>
        </CardContent>
      </Card>

      {loading ? (
        <p className="text-center py-8 text-muted-foreground">Loading...</p>
      ) : examResults.length === 0 ? (
        <div className="text-center py-12">
          <ClipboardList className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No results yet</p>
          <Link href="/student/exams">
            <Button className="mt-4">Take an Exam</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {examResults.map((r) => (
            <Card key={r.examId}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div>
                  <CardTitle className="text-lg">{r.subjectName}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">{r.examTitle}</p>
                </div>
                <Badge
                  className={
                    r.passed
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  }
                >
                  {r.passed ? "Pass" : "Fail"}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Score</p>
                    <p className="text-2xl font-bold">
                      {r.totalScore.toFixed(1)}{" "}
                      <span className="text-base font-normal text-muted-foreground">
                        / {r.maxMarks}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Percentage</p>
                    <Badge className={`text-lg px-3 py-1 ${getPercentageBadge(r.percentage)}`}>
                      {r.percentage.toFixed(1)}%
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Questions Answered</p>
                    <p className="text-2xl font-bold">{r.questionCount}</p>
                  </div>
                </div>
                <div className="mt-4">
                  <Link
                    href={`/student/results/${r.examId}`}
                    className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                  >
                    View detailed answers <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
