"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { answersApi, examsApi, questionsApi, asApiError } from "@/lib/api";
import type { Answer, Exam, Question } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, FileQuestion } from "lucide-react";

/**
 * Detail view for a single exam result: `/student/results/<examId>`.
 *
 * Only this student's answers for the requested exam are fetched
 * (`/answers/my-answers?exam_id=<id>`), plus the exam and its questions so the
 * question text and marks can be shown.
 */
interface LoadedResult {
  exam: Exam | null;
  answers: Answer[];
  questions: Question[];
  error: string | null;
}

export default function StudentResultDetailPage() {
  const params = useParams();
  const id = Number(params?.id);
  const examId = Number.isFinite(id) ? id : NaN;

  const invalidId = !Number.isFinite(examId);

  const [data, setData] = useState<LoadedResult | null>(null);

  useEffect(() => {
    if (invalidId) return;

    let cancelled = false;
    Promise.all([
      answersApi.getMyAnswers({ exam_id: examId, size: 100 }),
      questionsApi.getAll({ exam_id: examId, size: 100 }),
      // Exam metadata is a nice-to-have; answers already carry the scores.
      examsApi.getById(examId).catch(() => null),
    ])
      .then(([answersRes, questionsRes, examRes]) => {
        if (cancelled) return;
        setData({
          exam: examRes?.data ?? null,
          answers: answersRes.data.items || [],
          questions: questionsRes.data.items || [],
          error: null,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setData({
          exam: null,
          answers: [],
          questions: [],
          error: asApiError(err)?.response?.data?.detail || "Failed to load this result.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [examId, invalidId]);

  if (invalidId) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <Link href="/student/results" className="flex items-center gap-1 text-sm text-muted-foreground hover:underline">
          <ArrowLeft className="h-4 w-4" /> Back to Results
        </Link>
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">Invalid exam id.</CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return <div className="text-center py-12 text-muted-foreground">Loading...</div>;

  const { exam, answers, questions, error } = data;
  const totalScore = answers.reduce((sum, a) => sum + (a.score?.total_score || 0), 0);
  const maxMarks = exam?.total_marks ?? questions.reduce((sum, q) => sum + (q.marks || 0), 0);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link href="/student/results" className="flex items-center gap-1 text-sm text-muted-foreground hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to Results
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold break-words">{exam?.title || `Exam #${examId}`}</h1>
          {exam?.subject?.name && (
            <p className="text-sm text-muted-foreground">{exam.subject.name}</p>
          )}
        </div>
        {answers.length > 0 && (
          <Badge className="text-base px-3 py-1">
            {totalScore.toFixed(1)} / {maxMarks}
          </Badge>
        )}
      </div>

      {error ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">{error}</CardContent>
        </Card>
      ) : answers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileQuestion className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No answers found for this exam.</p>
            <Link href="/student/exams">
              <Button className="mt-4" variant="outline">Back to Exams</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        answers.map((a, idx) => {
          const question = questions.find((q) => q.id === a.question_id);
          return (
            <Card key={a.id}>
              <CardHeader>
                <CardTitle className="text-base flex items-start justify-between gap-3">
                  <span className="break-words">
                    Q{idx + 1}: {question?.question_text || `Question #${a.question_id}`}
                  </span>
                  {question && <Badge variant="outline" className="shrink-0">{question.marks} marks</Badge>}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Your Answer:</p>
                  <p className="mt-1 whitespace-pre-wrap break-words">{a.answer_text}</p>
                </div>
                {a.score && (
                  <div className="space-y-2 border-t pt-3">
                    <div className="grid grid-cols-4 gap-2 text-center">
                      <div><p className="text-xs text-muted-foreground">Keywords</p><p className="font-bold">{((a.score.keyword_score || 0) * 100).toFixed(0)}%</p></div>
                      <div><p className="text-xs text-muted-foreground">Similarity</p><p className="font-bold">{((a.score.similarity_score || 0) * 100).toFixed(0)}%</p></div>
                      <div><p className="text-xs text-muted-foreground">Grammar</p><p className="font-bold">{((a.score.grammar_score || 0) * 100).toFixed(0)}%</p></div>
                      <div><p className="text-xs text-muted-foreground">Total</p><p className="font-bold text-lg">{a.score.total_score?.toFixed(1)}</p></div>
                    </div>
                    {a.score.feedback && (
                      <div className="bg-muted p-3 rounded-lg text-sm">
                        <strong>Feedback:</strong> {a.score.feedback}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })
      )}
    </div>
  );
}
