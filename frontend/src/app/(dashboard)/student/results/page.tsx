"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { answersApi, examsApi, questionsApi, settingsApi } from "@/lib/api";
import type { Answer, Exam, Question } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ClipboardList } from "lucide-react";
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
  const [passThreshold, setPassThreshold] = useState(40);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        // Fetch all answers, exams, and questions in parallel
        const [answersRes, examsRes] = await Promise.all([
          answersApi.getMyAnswers({ limit: 500 }),
          examsApi.getAll({ limit: 100 }),
        ]);

        const answers: Answer[] = answersRes.data.items || [];
        const exams: Exam[] = examsRes.data.items || [];

        // Fetch questions for each exam to build question_id → exam mapping
        const questionToExam: Record<
          number,
          { examId: number; examTitle: string; subjectName: string; examTotalMarks: number }
        > = {};

        await Promise.all(
          exams.map(async (exam) => {
            try {
              const questionsRes = await questionsApi.getAll({ exam_id: exam.id });
              const questions: Question[] = questionsRes.data.items || [];
              questions.forEach((q) => {
                questionToExam[q.id] = {
                  examId: exam.id,
                  examTitle: exam.title,
                  subjectName: exam.subject?.name || `Subject #${exam.subject_id}`,
                  examTotalMarks: exam.total_marks,
                };
              });
            } catch {
              // Skip exams where questions can't be fetched
            }
          })
        );

        // Group answers by exam
        const examMap: Record<number, ExamResult> = {};

        answers.forEach((a) => {
          const examInfo = questionToExam[a.question_id];
          if (!examInfo) return;

          if (!examMap[examInfo.examId]) {
            examMap[examInfo.examId] = {
              examId: examInfo.examId,
              examTitle: examInfo.examTitle,
              subjectName: examInfo.subjectName,
              totalScore: 0,
              maxMarks: examInfo.examTotalMarks,
              percentage: 0,
              passed: false,
              questionCount: 0,
            };
          }

          const result = examMap[examInfo.examId];
          result.questionCount += 1;
          if (a.score) {
            result.totalScore += a.score.total_score;
          }
        });

        // Get pass threshold from backend API
        let threshold = 40;
        try {
          const settingsRes = await settingsApi.getAll();
          const pp = parseInt(settingsRes.data.pass_percentage);
          if (pp) threshold = pp;
        } catch {}

        Object.values(examMap).forEach((r) => {
          r.percentage = r.maxMarks > 0 ? (r.totalScore / r.maxMarks) * 100 : 0;
          r.passed = r.percentage >= threshold;
        });

        setExamResults(Object.values(examMap));
      } catch (err) {
        console.error(err);
        toast.error("Failed to load results");
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
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
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
