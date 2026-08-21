"use client";

import { useEffect, useState } from "react";
import { answersApi, questionsApi, usersApi, examsApi, settingsApi } from "@/lib/api";
import type { Answer, Question, User, Exam } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ClipboardCheck, Search, Copy, Check } from "lucide-react";
import { toast } from "sonner";

interface AnswerDetail {
  answerId: number;
  questionText: string;
  answerText: string;
  score: number | null;
  feedback: string;
  marks: number;
}

interface StudentGroup {
  id: number;
  name: string;
  email: string;
  totalScore: number;
  maxScore: number;
  percentage: number;
  passed: boolean;
  answers: AnswerDetail[];
  examIds: Set<number>;
}

export default function TeacherMarksPage() {
  const [students, setStudents] = useState<StudentGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedExam, setSelectedExam] = useState<string>("all");
  const [exams, setExams] = useState<Exam[]>([]);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [passThreshold, setPassThreshold] = useState(40);

  useEffect(() => {
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch pass threshold FIRST
        let thresholdValue = 40;
        try {
          const settingsRes = await settingsApi.getAll();
          const pp = parseInt(settingsRes.data.pass_percentage);
          if (pp) { thresholdValue = pp; setPassThreshold(pp); }
        } catch {}

        const [examRes, userRes, questionRes, answerRes] = await Promise.all([
          examsApi.getAll({ limit: 500 }),
          usersApi.getAll({ role: "student", limit: 500 }),
          questionsApi.getAll({ limit: 500 }),
          answersApi.getAllAnswers({ limit: 10000 }),
        ]);

        const examList: Exam[] = examRes.data.items || [];
        const studentList: User[] = userRes.data.items || [];
        const questions: Question[] = questionRes.data.items || [];
        const answersData: Answer[] = answerRes.data.items || [];

        setExams(examList);

        const questionMap: Record<number, { marks: number; exam_id: number; text: string }> = {};
        for (const q of questions) {
          questionMap[q.id] = { marks: q.marks, exam_id: q.exam_id, text: q.question_text || "N/A" };
        }

        // Group answers by student
        const studentGroups: Record<number, StudentGroup> = {};
        for (const s of studentList) {
          studentGroups[s.id] = {
            id: s.id,
            name: s.name,
            email: s.email,
            totalScore: 0,
            maxScore: 0,
            percentage: 0,
            passed: false,
            answers: [],
            examIds: new Set(),
          };
        }

        for (const a of answersData) {
          const qInfo = questionMap[a.question_id];
          if (!qInfo) continue;
          if (!studentGroups[a.student_id]) continue;

          studentGroups[a.student_id].examIds.add(qInfo.exam_id);
          studentGroups[a.student_id].answers.push({
            answerId: a.id,
            questionText: qInfo.text,
            answerText: a.answer_text || "No answer provided",
            score: a.score ? a.score.total_score : null,
            feedback: a.score?.feedback || "",
            marks: qInfo.marks,
          });

          studentGroups[a.student_id].maxScore += qInfo.marks;
          if (a.score) {
            studentGroups[a.student_id].totalScore += a.score.total_score;
          }
        }

        // Calculate percentages and sort
        const results = Object.values(studentGroups)
          .filter(s => s.answers.length > 0)
          .map(s => {
            s.totalScore = Math.round(s.totalScore * 100) / 100;
            s.percentage = s.maxScore > 0 ? Math.round((s.totalScore / s.maxScore) * 10000) / 100 : 0;
            s.passed = s.percentage >= thresholdValue;
            return s;
          })
          .sort((a, b) => b.totalScore - a.totalScore);

        setStudents(results);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load student marks");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const filtered = students.filter(s => {
    // Filter by search text
    if (search) {
      const q = search.toLowerCase();
      if (!s.name.toLowerCase().includes(q) && !s.email.toLowerCase().includes(q)) return false;
    }
    // Filter by selected exam
    if (selectedExam !== "all") {
      const examId = parseInt(selectedExam);
      if (!s.examIds.has(examId)) return false;
    }
    return true;
  });

  const handleCopy = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast.success("Copied! Paste in AI Detection.");
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ClipboardCheck className="h-6 w-6" /> Student Marks
        </h1>
        <p className="text-muted-foreground">View student answers grouped by student</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search by name or email..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" />
        </div>
        <div className="w-64">
          <Select value={selectedExam} onValueChange={(v) => setSelectedExam(v ?? "all")}>
            <SelectTrigger>
              <SelectValue placeholder="Filter by exam..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Exams</SelectItem>
              {exams.map((exam) => (
                <SelectItem key={exam.id} value={String(exam.id)}>
                  {exam.title} {exam.subject?.name ? `(${exam.subject.name})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Current threshold indicator */}
      <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-800">
        <CardContent className="py-3 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Pass Threshold (from Settings)</span>
          <span className="text-lg font-bold text-blue-600">≥ {passThreshold}%</span>
        </CardContent>
      </Card>

      {/* Student Groups */}
      {loading ? (
        <p className="text-center py-12 text-muted-foreground">Loading...</p>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <ClipboardCheck className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No students found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {filtered.map((s) => (
            <Card key={s.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">{s.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">{s.email}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-lg">{s.totalScore} / {s.maxScore}</p>
                    <Badge className={s.passed ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}>
                      {s.percentage}%
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {s.answers.map((a, idx) => (
                    <div key={a.answerId} className="p-4 rounded-lg border bg-muted/30">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <p className="text-sm font-medium text-muted-foreground">Q{idx + 1}: {a.questionText}</p>
                        <Badge className="bg-blue-100 text-blue-700 shrink-0">
                          {a.score !== null ? `${a.score}/${a.marks}` : "Not graded"}
                        </Badge>
                      </div>
                      <div className="relative">
                        <p className="text-sm break-words whitespace-pre-wrap bg-background p-3 rounded-md border">
                          {a.answerText}
                        </p>
                        <button
                          onClick={() => handleCopy(a.answerText, a.answerId)}
                          className="absolute top-2 right-2 p-1.5 rounded-md bg-muted hover:bg-muted/80 transition-colors"
                          title="Copy answer for AI Detection"
                        >
                          {copiedId === a.answerId ? (
                            <Check className="h-3.5 w-3.5 text-green-600" />
                          ) : (
                            <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                          )}
                        </button>
                      </div>
                      {a.feedback && (
                        <p className="text-xs text-muted-foreground mt-2 break-words">Feedback: {a.feedback}</p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
