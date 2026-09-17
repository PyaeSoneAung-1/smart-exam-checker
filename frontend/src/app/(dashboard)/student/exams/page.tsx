"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { examsApi } from "@/lib/api";
import { fetchMyResultsByExam, type MyExamResult } from "@/lib/exam-results";
import type { Exam } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Clock, FileText, Play, CheckCircle, CalendarDays, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { getExamWindowStatus, formatUtcDateTime } from "@/lib/utils";

export default function StudentExamsPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [myResults, setMyResults] = useState<Map<number, MyExamResult>>(new Map());
  const [myTotalScore, setMyTotalScore] = useState(0);
  const [loading, setLoading] = useState(true);

  // An exam counts as completed only when every question has an answer.
  const isComplete = (id: number) => myResults.get(id)?.complete === true;
  const completedCount = exams.filter((e) => isComplete(e.id)).length;

  useEffect(() => {
    let cancelled = false;

    const fetchExams = async () => {
      try {
        const examRes = await examsApi.getAll({ size: 100 });
        const examList: Exam[] = examRes.data.items || [];
        if (cancelled) return;
        setExams(examList);

        // Targeted per-exam query instead of pulling every answer the student
        // ever submitted plus every question in the system.
        const byExam = await fetchMyResultsByExam(examList);
        if (cancelled) return;

        setMyResults(byExam);
        const totalScore = [...byExam.values()].reduce((sum, r) => sum + r.totalScore, 0);
        setMyTotalScore(Math.round(totalScore * 100) / 100);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          toast.error("Failed to load exams");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchExams();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <BookOpen className="h-8 w-8" /> Available Exams
        </h1>
        <p className="text-muted-foreground mt-1">Take exams and view your results</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{exams.length}</p>
            <p className="text-sm text-muted-foreground">Total Exams</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold text-green-600">{completedCount}</p>
            <p className="text-sm text-muted-foreground">Completed</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold text-blue-600">{myTotalScore}</p>
            <p className="text-sm text-muted-foreground">My Total Score</p>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <p className="text-center py-12 text-muted-foreground">Loading exams...</p>
      ) : exams.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg text-muted-foreground">No exams available yet</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {exams.map((exam) => {
            const result = myResults.get(exam.id);
            const isCompleted = result?.complete === true;
            const inProgress = !isCompleted && (result?.answeredCount ?? 0) > 0;
            const status = getExamWindowStatus(exam);
            const canTake = status === "open";
            const windowText =
              exam.available_from || exam.available_until
                ? `${exam.available_from ? formatUtcDateTime(exam.available_from) : "—"} → ${exam.available_until ? formatUtcDateTime(exam.available_until) : "—"}`
                : null;
            return (
              <Card key={exam.id} className="hover:shadow-lg transition-shadow flex flex-col">
                <CardHeader>
                  <CardTitle className="text-lg break-words">{exam.title}</CardTitle>
                  {exam.subject?.name && (
                    <p className="text-sm text-muted-foreground break-words flex items-center gap-1">
                      <BookOpen className="h-3.5 w-3.5" /> {exam.subject.name}
                    </p>
                  )}
                </CardHeader>
                <CardContent className="space-y-3 flex-1 flex flex-col">
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                      <FileText className="h-4 w-4" /> {exam.total_marks} marks
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" /> {exam.time_limit_minutes} min
                    </span>
                  </div>
                  {windowText && (
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <CalendarDays className="h-3.5 w-3.5 shrink-0" /> {windowText}
                    </p>
                  )}
                  {isCompleted ? (
                    <Badge className="bg-green-100 text-green-700 w-fit">
                      <CheckCircle className="h-3 w-3 mr-1" /> Completed
                      {result && exam.total_marks > 0 &&
                        ` · ${((result.totalScore / exam.total_marks) * 100).toFixed(1)}%`}
                    </Badge>
                  ) : inProgress ? (
                    <Badge className="bg-amber-100 text-amber-700 w-fit">
                      In progress · {result?.answeredCount}/{result?.questionCount} answered
                    </Badge>
                  ) : status === "upcoming" ? (
                    <Badge className="bg-blue-100 text-blue-700 w-fit">
                      Opens {exam.available_from ? formatUtcDateTime(exam.available_from) : "soon"}
                    </Badge>
                  ) : status === "closed" ? (
                    <Badge variant="secondary" className="w-fit">Closed</Badge>
                  ) : (
                    <Badge variant={exam.is_active ? "default" : "secondary"} className="w-fit">
                      {exam.is_active ? "Available" : "Inactive"}
                    </Badge>
                  )}
                  <div className="pt-2 mt-auto">
                    {isCompleted ? (
                      <Link href={`/student/results/${exam.id}`}>
                        <Button className="w-full" variant="outline">
                          <CheckCircle className="h-4 w-4 mr-2" /> View Results
                          <ArrowRight className="h-4 w-4 ml-1" />
                        </Button>
                      </Link>
                    ) : inProgress ? (
                      <Link href={`/student/exams/${exam.id}`}>
                        <Button className="w-full" variant="outline">
                          <Play className="h-4 w-4 mr-2" /> Continue Exam
                        </Button>
                      </Link>
                    ) : (
                      <Link href={`/student/exams/${exam.id}`}>
                        <Button className="w-full" disabled={!canTake}>
                          <Play className="h-4 w-4 mr-2" /> {status === "upcoming" ? "Not open yet" : status === "closed" ? "Closed" : "Take Exam"}
                        </Button>
                      </Link>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
