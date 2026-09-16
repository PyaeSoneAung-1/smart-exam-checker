"use client";

import { useCallback, useEffect, useState } from "react";
import {
  examsApi, questionsApi, answersApi, usersApi, settingsApi, asApiError, fetchAllPages,
} from "@/lib/api";
import type { Exam, Answer } from "@/types";
import { DEFAULT_THRESHOLDS, parseNumberOr } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { FileText, Clock, Hash, Search, BookOpen, Users, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface ExamSummary {
  totalStudents: number;
  passCount: number;
  failCount: number;
  questionCount: number;
}

interface ExamComputation {
  summary: ExamSummary;
  /** Total score per student for this exam. */
  studentScores: Record<number, number>;
}

interface OverallStats {
  totalStudents: number;
  overallPass: number;
  overallFail: number;
  /** False until the user asks for the (capped) sweep. */
  computed: boolean;
}

/**
 * How many exams the "calculate overall" sweep is allowed to walk. Each exam
 * costs a handful of targeted requests; without a cap an installation with
 * hundreds of exams would fire hundreds of requests from one click.
 */
const OVERALL_EXAM_CAP = 10;

export default function AdminExamsPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [examSummaries, setExamSummaries] = useState<Record<number, ExamSummary>>({});
  const [loadingSummaries, setLoadingSummaries] = useState<Set<number>>(new Set());
  const [overallStats, setOverallStats] = useState<OverallStats>({
    totalStudents: 0, overallPass: 0, overallFail: 0, computed: false,
  });
  const [overallLoading, setOverallLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [passPct, setPassPct] = useState(DEFAULT_THRESHOLDS.pass_percentage);

  // One load, one settings request: exams + the student head-count only.
  // Per-exam result summaries are fetched on demand below.
  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [settingsRes, examRes, studentsRes] = await Promise.all([
          settingsApi.getAll().catch(() => null),
          examsApi.getAll({ size: 100 }),
          usersApi.getAll({ role: "student", size: 1 }),
        ]);
        if (cancelled) return;

        setPassPct(parseNumberOr(settingsRes?.data?.pass_percentage, DEFAULT_THRESHOLDS.pass_percentage));
        setExams(examRes.data.items || []);
        setOverallStats((prev) => ({
          ...prev,
          totalStudents: studentsRes.data.total ?? 0,
        }));
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          const message = asApiError(err)?.message;
          toast.error(typeof message === "string" ? message : "Failed to load exams");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  /** Targeted summary for a single exam: its question count + its answers. */
  const computeExam = useCallback(async (exam: Exam, thresholdPct: number): Promise<ExamComputation> => {
    const [questionsRes, answers] = await Promise.all([
      questionsApi.getAll({ exam_id: exam.id, size: 1 }),
      fetchAllPages<Answer>((page, size) => answersApi.getAllAnswers({ exam_id: exam.id, page, size })),
    ]);

    const studentScores: Record<number, number> = {};
    for (const answer of answers.items) {
      if (studentScores[answer.student_id] === undefined) studentScores[answer.student_id] = 0;
      if (answer.score) studentScores[answer.student_id] += answer.score.total_score;
    }

    const passThreshold = exam.total_marks * (thresholdPct / 100);
    let passCount = 0;
    let failCount = 0;
    for (const score of Object.values(studentScores)) {
      if (score >= passThreshold) passCount += 1;
      else failCount += 1;
    }

    return {
      summary: {
        totalStudents: Object.keys(studentScores).length,
        passCount,
        failCount,
        questionCount: questionsRes.data.total ?? 0,
      },
      studentScores,
    };
  }, []);

  const handleLoadSummary = async (exam: Exam) => {
    setLoadingSummaries((prev) => new Set(prev).add(exam.id));
    try {
      const { summary } = await computeExam(exam, passPct);
      setExamSummaries((prev) => ({ ...prev, [exam.id]: summary }));
    } catch (err) {
      console.error(err);
      toast.error(`Failed to load summary for "${exam.title}"`);
    } finally {
      setLoadingSummaries((prev) => {
        const next = new Set(prev);
        next.delete(exam.id);
        return next;
      });
    }
  };

  const handleLoadOverall = async () => {
    setOverallLoading(true);
    try {
      const capped = exams.slice(0, OVERALL_EXAM_CAP);
      const computations = await Promise.all(capped.map((exam) => computeExam(exam, passPct)));

      // A student fails overall if they scored below the pass mark in any exam.
      let overallPass = 0;
      let overallFail = 0;
      const studentExamScores: Record<number, Record<number, number>> = {};
      computations.forEach((computation, idx) => {
        const exam = capped[idx];
        for (const [studentId, score] of Object.entries(computation.studentScores)) {
          const id = Number(studentId);
          if (!studentExamScores[id]) studentExamScores[id] = {};
          studentExamScores[id][exam.id] = score;
        }
      });

      for (const examScores of Object.values(studentExamScores)) {
        let studentFailed = false;
        for (const [examId, score] of Object.entries(examScores)) {
          const exam = capped.find((e) => e.id === Number(examId));
          if (exam && exam.total_marks > 0 && score / exam.total_marks < passPct / 100) {
            studentFailed = true;
            break; // One fail = overall fail
          }
        }
        if (studentFailed) overallFail += 1;
        else overallPass += 1;
      }

      // Fold the freshly computed summaries into the cards for free.
      const fresh: Record<number, ExamSummary> = {};
      computations.forEach((computation, idx) => {
        fresh[capped[idx].id] = computation.summary;
      });
      setExamSummaries((prev) => ({ ...prev, ...fresh }));

      setOverallStats((prev) => ({ ...prev, overallPass, overallFail, computed: true }));
      if (exams.length > OVERALL_EXAM_CAP) {
        toast.info(`Calculated over the first ${OVERALL_EXAM_CAP} of ${exams.length} exams.`);
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to calculate overall statistics");
    } finally {
      setOverallLoading(false);
    }
  };

  const filtered = exams.filter((e) =>
    !search ||
    e.title.toLowerCase().includes(search.toLowerCase()) ||
    e.description?.toLowerCase().includes(search.toLowerCase()) ||
    e.subject?.name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="h-6 w-6" /> All Exams
        </h1>
        <p className="text-muted-foreground">View all exams with results summary</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search exams..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Current threshold indicator */}
      <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800">
        <CardContent className="py-3 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Pass Threshold (from Settings)</span>
          <span className="text-lg font-bold text-blue-600">≥ {passPct}%</span>
        </CardContent>
      </Card>

      {/* Overall stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{exams.length}</p>
            <p className="text-sm text-muted-foreground">Total Exams</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{overallStats.totalStudents}</p>
            <p className="text-sm text-muted-foreground">Total Students</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold text-green-600">
              {overallStats.computed ? overallStats.overallPass : "—"}
            </p>
            <p className="text-sm text-muted-foreground">Overall Pass</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold text-red-600">
              {overallStats.computed ? overallStats.overallFail : "—"}
            </p>
            <p className="text-sm text-muted-foreground">Overall Fail</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={handleLoadOverall} disabled={overallLoading || exams.length === 0}>
          {overallLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          Calculate overall pass / fail
        </Button>
        <span className="text-xs text-muted-foreground">
          Uses up to {OVERALL_EXAM_CAP} exams; per-exam summaries load on demand.
        </span>
      </div>

      {loading ? (
        <p className="text-center py-12 text-muted-foreground">Loading...</p>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No exams found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((exam) => {
            const summary = examSummaries[exam.id];
            const summaryLoading = loadingSummaries.has(exam.id);
            return (
              <Card key={exam.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg leading-tight break-words">{exam.title}</CardTitle>
                  {exam.subject?.name && (
                    <p className="text-sm text-muted-foreground break-words flex items-center gap-1">
                      <BookOpen className="h-3.5 w-3.5" /> {exam.subject.name}
                    </p>
                  )}
                </CardHeader>
                <CardContent className="space-y-3">
                  {exam.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2 break-words">{exam.description}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline" className="flex items-center gap-1">
                      <FileText className="h-3 w-3" /> {exam.total_marks} marks
                    </Badge>
                    <Badge variant="outline" className="flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {exam.time_limit_minutes} min
                    </Badge>
                    {summary && (
                      <Badge variant="outline" className="flex items-center gap-1">
                        <Hash className="h-3 w-3" /> {summary.questionCount} Qs
                      </Badge>
                    )}
                  </div>
                  <div>
                    {exam.is_active ? (
                      <Badge className="bg-green-100 text-green-700">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </div>

                  {/* Results Summary — loaded on demand (no N+1 on page load) */}
                  {summary ? (
                    <div className="border-t pt-3 space-y-2">
                      <p className="text-sm font-medium flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" /> Results Summary
                      </p>
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="bg-muted rounded-md p-2">
                          <p className="text-lg font-bold">{summary.totalStudents}</p>
                          <p className="text-xs text-muted-foreground">Students</p>
                        </div>
                        <div className="bg-green-50 rounded-md p-2">
                          <p className="text-lg font-bold text-green-600">{summary.passCount}</p>
                          <p className="text-xs text-muted-foreground flex items-center justify-center gap-0.5">
                            <CheckCircle className="h-3 w-3" /> Pass
                          </p>
                        </div>
                        <div className="bg-red-50 rounded-md p-2">
                          <p className="text-lg font-bold text-red-600">{summary.failCount}</p>
                          <p className="text-xs text-muted-foreground flex items-center justify-center gap-0.5">
                            <XCircle className="h-3 w-3" /> Fail
                          </p>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground text-center">
                        Pass threshold: {(exam.total_marks * passPct / 100).toFixed(0)} / {exam.total_marks} marks ({passPct}%)
                      </p>
                    </div>
                  ) : (
                    <div className="border-t pt-3">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => handleLoadSummary(exam)}
                        disabled={summaryLoading}
                      >
                        {summaryLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        {summaryLoading ? "Loading..." : "Load results summary"}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
