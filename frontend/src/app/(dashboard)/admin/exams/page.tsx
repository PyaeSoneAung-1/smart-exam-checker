"use client";

import { useEffect, useState } from "react";
import { examsApi, questionsApi, answersApi, usersApi, settingsApi, asApiError } from "@/lib/api";
import type { Exam, Answer } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { FileText, Clock, Hash, Search, BookOpen, Users, CheckCircle, XCircle } from "lucide-react";
import { toast } from "sonner";

interface ExamSummary {
  totalStudents: number;
  passCount: number;
  failCount: number;
  questionCount: number;
}

interface OverallStats {
  totalStudents: number;
  overallPass: number;
  overallFail: number;
}

export default function AdminExamsPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [examSummaries, setExamSummaries] = useState<Record<number, ExamSummary>>({});
  const [overallStats, setOverallStats] = useState<OverallStats>({ totalStudents: 0, overallPass: 0, overallFail: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [passPct, setPassPct] = useState(40);

  useEffect(() => {
    // Load pass threshold from backend API
    settingsApi.getAll().then((res) => {
      const pp = parseInt(res.data.pass_percentage);
      if (pp) setPassPct(pp);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch pass threshold FIRST before using it
        let passPctValue = 40;
        try {
          const settingsRes = await settingsApi.getAll();
          const pp = parseInt(settingsRes.data.pass_percentage);
          if (pp) { passPctValue = pp; setPassPct(pp); }
        } catch {}

        const examRes = await examsApi.getAll({ limit: 500 });
        const examList = examRes.data.items || [];
        setExams(examList);

        // Fetch summaries for each exam
        const summaries: Record<number, ExamSummary> = {};

        for (const exam of examList) {
          try {
            // Get question count
            const qRes = await questionsApi.getAll({ exam_id: exam.id, limit: 500 });
            const questionCount = qRes.data.items?.length ?? 0;

            // Get all answers for this exam
            const aRes = await answersApi.getAllAnswers({ exam_id: exam.id, limit: 10000 });
            const answers: Answer[] = aRes.data.items || [];

            // Aggregate: per student, compute total score across all questions
            const studentScores: Record<number, number> = {};
            for (const answer of answers) {
              if (!studentScores[answer.student_id]) {
                studentScores[answer.student_id] = 0;
              }
              if (answer.score) {
                studentScores[answer.student_id] += answer.score.total_score;
              }
            }

            const totalStudents = Object.keys(studentScores).length;
            const passThreshold = exam.total_marks * (passPctValue / 100);
            let passCount = 0;
            let failCount = 0;

            for (const score of Object.values(studentScores)) {
              if (score >= passThreshold) {
                passCount++;
              } else {
                failCount++;
              }
            }

            summaries[exam.id] = { totalStudents, passCount, failCount, questionCount };
          } catch {
            summaries[exam.id] = { totalStudents: 0, passCount: 0, failCount: 0, questionCount: 0 };
          }
        }

        setExamSummaries(summaries);

        // Calculate overall stats: unique student pass/fail across ALL exams
        try {
          const [usersRes, allQuestionsRes, allAnswersRes] = await Promise.all([
            usersApi.getAll({ role: 'student', limit: 1000 }),
            questionsApi.getAll({ limit: 10000 }),
            answersApi.getAllAnswers({ limit: 10000 }),
          ]);
          const students = usersRes.data.items || [];
          const allQuestions = allQuestionsRes.data.items || [];
          const allAnswers: Answer[] = allAnswersRes.data.items || [];

          // Build question_id -> exam_id map
          const questionToExam: Record<number, number> = {};
          for (const q of allQuestions) {
            questionToExam[q.id] = q.exam_id;
          }

          // Build exam_id -> total_marks map
          const examMarks: Record<number, number> = {};
          for (const exam of examList) {
            examMarks[exam.id] = exam.total_marks;
          }

          // Build per-student per-exam scores
          // Key logic: if a student fails ANY single exam → overall fail
          const studentExamScores: Record<number, Record<number, number>> = {};
          for (const answer of allAnswers) {
            const examId = questionToExam[answer.question_id];
            if (!examId) continue;
            if (!studentExamScores[answer.student_id]) studentExamScores[answer.student_id] = {};
            if (!studentExamScores[answer.student_id][examId]) studentExamScores[answer.student_id][examId] = 0;
            if (answer.score) {
              studentExamScores[answer.student_id][examId] += answer.score.total_score;
            }
          }

          let overallPass = 0;
          let overallFail = 0;
          for (const examScores of Object.values(studentExamScores)) {
            let studentFailed = false;
            for (const [examIdStr, score] of Object.entries(examScores)) {
              const examId = Number(examIdStr);
              const totalMarks = examMarks[examId] || 0;
              if (totalMarks > 0) {
                const pct = score / totalMarks;
                if (pct < passPctValue / 100) {
                  studentFailed = true;
                  break; // One fail = overall fail
                }
              }
            }
            if (studentFailed) overallFail++;
            else overallPass++;
          }

          setOverallStats({ totalStudents: students.length, overallPass, overallFail });
        } catch (e) {
          console.error('Failed to calculate overall stats', e);
        }
      } catch (err) {
        console.error(err);
        const message = asApiError(err)?.message;
        toast.error(typeof message === "string" ? message : "Failed to load exams");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

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
            <p className="text-2xl font-bold text-green-600">{overallStats.overallPass}</p>
            <p className="text-sm text-muted-foreground">Overall Pass</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold text-red-600">{overallStats.overallFail}</p>
            <p className="text-sm text-muted-foreground">Overall Fail</p>
          </CardContent>
        </Card>
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
                    <Badge variant="outline" className="flex items-center gap-1">
                      <Hash className="h-3 w-3" /> {summary?.questionCount ?? 0} Qs
                    </Badge>
                  </div>
                  <div>
                    {exam.is_active ? (
                      <Badge className="bg-green-100 text-green-700">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </div>

                  {/* Results Summary */}
                  {summary && (
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
