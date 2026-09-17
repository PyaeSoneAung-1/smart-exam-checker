"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { examsApi, questionsApi, answersApi, asApiError } from "@/lib/api";
import type { Exam, Question, Answer } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import CountdownTimer from "@/components/shared/CountdownTimer";
import ErrorBoundary from "@/components/shared/ErrorBoundary";
import {
  Send, ArrowLeft, CheckCircle, Lock,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import { cn, formatUtcDateTime } from "@/lib/utils";

interface QuestionResult {
  question: Question;
  answer: Answer;
}

export default function TakeExamPage() {
  return (
    <ErrorBoundary>
      <ExamContent />
    </ErrorBoundary>
  );
}

function ExamContent() {
  const { id } = useParams();
  const router = useRouter();
  const [exam, setExam] = useState<Exam | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [results, setResults] = useState<QuestionResult[]>([]);
  // Answers already stored for this exam (a student may be part-way through,
  // or may have finished it in an earlier session).
  const [existing, setExisting] = useState<Record<number, Answer>>({});
  const [currentIdx, setCurrentIdx] = useState(0);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(null);
  const [notAvailable, setNotAvailable] = useState<string | null>(null);
  const submittedRef = useRef(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const examRes = await examsApi.getById(Number(id));
        setExam(examRes.data);
        const qRes = await questionsApi.getAll({ exam_id: Number(id), size: 100 });
        const qs = qRes.data.items || [];
        setQuestions(qs);

        // Restore what this student already submitted for this exam.
        let mine: Answer[] = [];
        try {
          const mineRes = await answersApi.getMyAnswers({ exam_id: Number(id), size: 100 });
          mine = mineRes.data.items || [];
        } catch {
          // Not fatal: start from a blank paper.
        }

        const init: Record<number, string> = {};
        const already: Record<number, Answer> = {};
        qs.forEach((q: Question) => { init[q.id] = ""; });
        for (const a of mine) {
          already[a.question_id] = a;
          init[a.question_id] = a.answer_text || "";
        }
        setAnswers(init);
        setExisting(already);

        // The exam is fully answered → show the graded result instead of an
        // empty paper (the API rejects duplicate submissions anyway).
        if (qs.length > 0 && Object.keys(already).length >= qs.length) {
          submittedRef.current = true;
          setResults(
            qs
              .map((q: Question) => ({ question: q, answer: already[q.id] }))
              .filter((r): r is QuestionResult => Boolean(r.answer))
          );
          setSubmitted(true);
        }
      } catch (err) {
        const apiErr = asApiError(err);
        const status = apiErr?.response?.status;
        const detail = apiErr?.response?.data?.detail;
        if (status === 403 && typeof detail === "string") {
          // Exam exists but is outside its availability window.
          setNotAvailable(detail);
        } else {
          toast.error("Failed to load exam");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  // Confirm before leaving
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!submittedRef.current && Object.values(answers).some((a) => a.trim())) {
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [answers]);

  // Warn before leaving with unsaved answers. Instead of mutating router.push,
  // intercept link clicks in the capture phase so every in-app navigation
  // (including <Link>) is covered.
  const dirtyRef = useRef(false);

  useEffect(() => {
    dirtyRef.current = Object.values(answers).some((a) => a.trim()) && !submitted;
  }, [answers, submitted]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (!dirtyRef.current || event.defaultPrevented) return;
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest?.("a[href]");
      const href = anchor?.getAttribute("href");
      if (!href) return;
      if (/^(https?:)?\/\//.test(href) || anchor?.getAttribute("target") === "_blank") return;
      event.preventDefault();
      setPendingNavigation(href);
      setShowLeaveConfirm(true);
    };
    document.addEventListener("click", handleClick, true);
    return () => document.removeEventListener("click", handleClick, true);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (submitting || submittedRef.current) return;

    // Skip questions this student already answered and any left blank — the API
    // rejects empty answers and duplicates, which used to abort the whole exam
    // submission half-way through.
    const targets = questions.filter(
      (q) => !existing[q.id] && (answers[q.id] || "").trim()
    );

    if (targets.length === 0) {
      if (questions.length > 0 && Object.keys(existing).length >= questions.length) {
        // Everything was already submitted earlier — just show the results.
        submittedRef.current = true;
        setResults(
          questions
            .map((q) => ({ question: q, answer: existing[q.id] }))
            .filter((r): r is QuestionResult => Boolean(r.answer))
        );
        setSubmitted(true);
      } else {
        toast.error("Please answer at least one question before submitting.");
      }
      return;
    }

    submittedRef.current = true;
    setSubmitting(true);
    try {
      const saved: Record<number, Answer> = { ...existing };
      for (const q of targets) {
        const res = await answersApi.submit({
          question_id: q.id,
          answer_text: answers[q.id],
        });
        saved[q.id] = res.data;
      }
      setExisting(saved);
      setResults(
        questions
          .map((q) => ({ question: q, answer: saved[q.id] }))
          .filter((r): r is QuestionResult => Boolean(r.answer))
      );
      setSubmitted(true);
      const skipped = questions.length - Object.keys(saved).length;
      if (skipped > 0) {
        toast.success(`Submitted! ${skipped} unanswered question${skipped === 1 ? "" : "s"} scored 0.`);
      } else {
        toast.success("Exam submitted successfully!");
      }
    } catch (err) {
      const msg = asApiError(err)?.response?.data?.detail || "Failed to submit exam";
      toast.error(typeof msg === "string" ? msg : "Already submitted or error occurred");
      submittedRef.current = false;
    } finally {
      setSubmitting(false);
    }
  }, [submitting, questions, answers, existing]);

  const answeredCount = Object.values(answers).filter((a) => a.trim()).length;
  const remainingUnanswered = questions.filter(
    (q) => !existing[q.id] && !(answers[q.id] || "").trim()
  ).length;

  // Ask for confirmation when questions are left unanswered, so a partial
  // submission is never a surprise.
  const requestSubmit = useCallback(() => {
    if (submitting || submittedRef.current) return;
    if (remainingUnanswered > 0) {
      setShowSubmitConfirm(true);
      return;
    }
    handleSubmit();
  }, [handleSubmit, remainingUnanswered, submitting]);

  const handleTimeEnd = useCallback(() => {
    toast.warning("Time is up! Auto-submitting your exam...");
    handleSubmit();
  }, [handleSubmit]);

  const progress = questions.length > 0 ? (answeredCount / questions.length) * 100 : 0;
  const currentQuestion = questions[currentIdx];

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="h-8 w-64 bg-muted animate-pulse rounded" />
        <div className="h-40 bg-muted animate-pulse rounded-xl" />
        <div className="h-64 bg-muted animate-pulse rounded-xl" />
      </div>
    );
  }

  if (!exam) {
    return (
      <div className="text-center py-12">
        <p className="text-lg text-muted-foreground">Exam not found</p>
        <Link href="/student/exams"><Button className="mt-4">Back to Exams</Button></Link>
      </div>
    );
  }

  // Outside the availability window — show a clear message instead of the paper.
  if (notAvailable) {
    return (
      <div className="max-w-3xl mx-auto text-center py-12">
        <Lock className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h1 className="text-2xl font-bold mb-2">Exam not available</h1>
        <p className="text-muted-foreground mb-6">{notAvailable}</p>
        <Link href="/student/exams">
          <Button><ArrowLeft className="h-4 w-4 mr-2" /> Back to Exams</Button>
        </Link>
      </div>
    );
  }

  // Results view
  if (submitted && results.length > 0) {
    const totalScore = results.reduce((sum, r) => sum + (r.answer.score?.total_score || 0), 0);
    const examTotalMarks = questions.reduce((sum, q) => sum + q.marks, 0);
    const answeredMarks = results.reduce((sum, r) => sum + r.question.marks, 0);
    const missing = questions.length - results.length;

    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <Card className="border-green-200 bg-green-50 dark:bg-green-950">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-700 dark:text-green-300">
              <CheckCircle className="h-6 w-6" /> Exam Submitted!
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <p className="text-2xl font-bold">{totalScore.toFixed(1)} / {examTotalMarks}</p>
            <p className="text-muted-foreground">
              {missing > 0
                ? `Answered ${results.length} of ${questions.length} questions (${answeredMarks} marks attempted).`
                : totalScore >= examTotalMarks * 0.5
                  ? "🎉 Great job!"
                  : "📚 Keep studying!"}
            </p>
            {missing > 0 && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                {missing} question{missing === 1 ? "" : "s"} left unanswered and scored 0.
              </p>
            )}
          </CardContent>
        </Card>

        {results.map((r, idx) => (
          <Card key={r.answer.id}>
            <CardHeader>
              <CardTitle className="text-base">Q{idx + 1}: {r.question.question_text}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm"><strong>Your Answer:</strong> {r.answer.answer_text}</p>
              {r.answer.score && (
                <div className="space-y-1">
                  <div className="flex gap-4 text-sm">
                    <span>Keywords: {((r.answer.score.keyword_score || 0) * 100).toFixed(0)}%</span>
                    <span>Similarity: {((r.answer.score.similarity_score || 0) * 100).toFixed(0)}%</span>
                    <span>Grammar: {((r.answer.score.grammar_score || 0) * 100).toFixed(0)}%</span>
                    <span>Completeness: {((r.answer.score.completeness_score || 0) * 100).toFixed(0)}%</span>
                  </div>
                  <Badge className="text-lg">{r.answer.score.total_score?.toFixed(1)} / {r.question.marks}</Badge>
                  {r.answer.score.feedback && (
                    <p className="text-sm text-muted-foreground mt-2">{r.answer.score.feedback}</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        <div className="flex flex-wrap gap-4">
          <Link href="/student/exams"><Button variant="outline">Back to Exams</Button></Link>
          <Link href={`/student/results/${exam.id}`}><Button variant="outline">Open in My Results</Button></Link>
          <Link href="/student/results"><Button>View All Results</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Partial-submission confirmation */}
      <AlertDialog open={showSubmitConfirm} onOpenChange={setShowSubmitConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Submit with unanswered questions?</AlertDialogTitle>
            <AlertDialogDescription>
              You have {remainingUnanswered} unanswered question
              {remainingUnanswered === 1 ? "" : "s"}. They will be submitted with 0 marks.
              You cannot change your answers after submitting.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep answering</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setShowSubmitConfirm(false);
                handleSubmit();
              }}
            >
              Submit anyway
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Leave confirmation dialog */}
      <AlertDialog open={showLeaveConfirm} onOpenChange={setShowLeaveConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Leave Exam?</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved answers. If you leave now, your progress will be lost. Are you sure you want to leave?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setPendingNavigation(null); }}>Stay</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                submittedRef.current = true;
                if (pendingNavigation) router.push(pendingNavigation);
              }}
              className="bg-red-600 hover:bg-red-700"
            >
              Leave Exam
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <Link href="/student/exams" className="text-sm text-muted-foreground hover:underline flex items-center gap-1 mb-2">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
          <h1 className="text-2xl font-bold">{exam.title}</h1>
          <p className="text-muted-foreground">{exam.total_marks} marks • {exam.time_limit_minutes} minutes</p>
          {(exam.available_from || exam.available_until) && (
            <p className="text-xs text-muted-foreground">
              Window: {exam.available_from ? formatUtcDateTime(exam.available_from) : "—"} → {exam.available_until ? formatUtcDateTime(exam.available_until) : "—"}
            </p>
          )}
        </div>
        <div className="min-w-[200px]">
          <CountdownTimer
            initialSeconds={exam.time_limit_minutes * 60}
            onTimeEnd={handleTimeEnd}
          />
        </div>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">
            {answeredCount} of {questions.length} answered
          </span>
          <span className="font-medium">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Question navigation pills */}
      <div className="flex flex-wrap gap-2">
        {questions.map((q, idx) => (
          <Button
            key={q.id}
            variant={currentIdx === idx ? "default" : "outline"}
            size="sm"
            className={cn(
              "h-9 w-9 p-0",
              answers[q.id]?.trim() && currentIdx !== idx && "border-green-500 text-green-600 bg-green-50 dark:bg-green-950 dark:text-green-400"
            )}
            onClick={() => setCurrentIdx(idx)}
          >
            {idx + 1}
          </Button>
        ))}
      </div>

      {/* Current question card */}
      {currentQuestion && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Question {currentIdx + 1} of {questions.length}</span>
              <Badge variant="outline">{currentQuestion.marks} marks</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-base leading-relaxed">{currentQuestion.question_text}</p>
            <div>
              <Label className="mb-2 block">Your Answer</Label>
              <Textarea
                value={answers[currentQuestion.id] || ""}
                onChange={(e) => setAnswers({ ...answers, [currentQuestion.id]: e.target.value })}
                placeholder="Type your answer here..."
                rows={6}
                className="resize-y"
              />
              <p className="text-xs text-muted-foreground mt-1">
                {(answers[currentQuestion.id] || "").length} characters
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation buttons — "Submit Exam" is always visible so a student can
          finish early without paging through every question first. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          variant="outline"
          disabled={currentIdx === 0}
          onClick={() => setCurrentIdx((i) => i - 1)}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Previous
        </Button>

        <div className="flex items-center gap-3">
          {remainingUnanswered > 0 && (
            <span className="text-xs text-muted-foreground">
              {remainingUnanswered} unanswered
            </span>
          )}
          {currentIdx < questions.length - 1 && (
            <Button variant="outline" onClick={() => setCurrentIdx((i) => i + 1)}>
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
          <Button
            onClick={requestSubmit}
            disabled={submitting}
            className="bg-green-600 hover:bg-green-700"
          >
            <Send className="h-4 w-4 mr-2" />
            {submitting ? "Submitting..." : "Submit Exam"}
          </Button>
        </div>
      </div>
    </div>
  );
}
