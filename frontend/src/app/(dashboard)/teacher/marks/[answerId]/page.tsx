"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import api, { answersApi, questionsApi } from "@/lib/api";
import type { Answer, Question } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import ScoreBadge from "@/components/shared/ScoreBadge";
import ProgressBar from "@/components/shared/ProgressBar";
import { toast } from "sonner";
import { ArrowLeft, Save, AlertTriangle, Loader2, CheckCircle2, Tag, Sparkles, MessageSquare } from "lucide-react";
import Link from "next/link";

export default function OverrideScorePage() {
  const router = useRouter();
  const params = useParams();
  const answerId = Number(params?.answerId);

  const [answer, setAnswer] = useState<Answer | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [loading, setLoading] = useState(true);
  const [newScore, setNewScore] = useState("");
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  const handleGetFeedback = async () => {
    if (!answer) return;
    setFeedbackLoading(true);
    setFeedback("");
    try {
      const res = await api.get(`/nlp/feedback/${answer.id}`);
      setFeedback(res.data.feedback || "No feedback generated");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || "Failed to generate feedback");
    } finally {
      setFeedbackLoading(false);
    }
  };

  useEffect(() => {
    if (!answerId) return;

    const fetchData = async () => {
      try {
        // Fetch all answers to find this one
        const answersRes = await answersApi.getAllAnswers({ limit: 10000 });
        const allAnswers: Answer[] = answersRes.data.items || [];
        const found = allAnswers.find(a => a.id === answerId);

        if (!found) {
          toast.error("Answer not found");
          router.push("/teacher/marks");
          return;
        }

        setAnswer(found);
        setNewScore(found.score ? String(Math.round(found.score.total_score * 100) / 100) : "0");

        // Fetch question details
        if (found.question_id) {
          try {
            const qRes = await questionsApi.getById(found.question_id);
            setQuestion(qRes.data);
          } catch {
            // Question fetch failed, use what we have
          }
        }
      } catch (err) {
        console.error(err);
        toast.error("Failed to load answer details");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [answerId, router]);

  const handleOverride = async () => {
    const score = Number(newScore);
    const maxMarks = question?.marks ?? 100;
    if (isNaN(score) || score < 0 || score > maxMarks) {
      toast.error(`Score must be between 0 and ${maxMarks}`);
      return;
    }
    if (!reason.trim()) {
      toast.error("Please provide a reason for the override");
      return;
    }
    setIsSubmitting(true);
    try {
      await answersApi.overrideScore(answerId, {
        total_score: score,
        feedback: reason.trim(),
      });
      toast.success(`Score overridden to ${score}/${maxMarks}`);
      router.push("/teacher/marks");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || "Failed to override score");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!answer) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Answer not found</p>
        <Link href="/teacher/marks"><Button className="mt-4">Back to Marks</Button></Link>
      </div>
    );
  }

  const maxMarks = question?.marks ?? 100;
  const currentScore = answer.score?.total_score ?? 0;

  return (
    <div className="space-y-6">
      <Link href="/teacher/marks">
        <Button variant="ghost" size="sm"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Marks</Button>
      </Link>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Answer details */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{question?.question_text || `Question #${answer.question_id}`}</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Student ID: {answer.student_id} • Answer #{answer.id}
                  </p>
                </div>
                <ScoreBadge score={currentScore} max={maxMarks} />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="mb-1 text-sm font-medium text-muted-foreground">Question</p>
                <div className="rounded-lg border p-3 text-sm">{question?.question_text || "Loading..."}</div>
              </div>
              <div>
                <p className="mb-1 text-sm font-medium text-muted-foreground">Student Answer</p>
                <div className="rounded-lg border bg-muted/50 p-3 text-sm break-words whitespace-pre-wrap">
                  {answer.answer_text || "No answer provided"}
                </div>
              </div>
              {question?.model_answer && (
                <div>
                  <p className="mb-1 text-sm font-medium text-muted-foreground">Model Answer</p>
                  <div className="rounded-lg border bg-emerald-50 p-3 text-sm dark:bg-emerald-900/10">
                    {question.model_answer}
                  </div>
                </div>
              )}
              {question?.keywords && question.keywords.length > 0 && (
                <div>
                  <p className="mb-2 flex items-center gap-1 text-sm font-medium text-muted-foreground">
                    <Tag className="h-3.5 w-3.5" /> Expected Keywords
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {question.keywords.map((kw) => (
                      <Badge key={kw} variant="secondary" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                        <CheckCircle2 className="mr-1 h-3 w-3" /> {kw}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <ProgressBar value={currentScore} max={maxMarks} showLabel />
            </CardContent>
          </Card>
        </div>

        {/* Override form */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Override Score</CardTitle>
              <CardDescription>Manually adjust the score for this answer</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                This action will be logged and cannot be undone.
              </div>
              <div className="space-y-2">
                <Label>Current Score</Label>
                <p className="text-2xl font-bold">{currentScore} / {maxMarks}</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-score">New Score (0-{maxMarks})</Label>
                <Input
                  id="new-score"
                  type="number"
                  min={0}
                  max={maxMarks}
                  value={newScore}
                  onChange={(e) => setNewScore(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reason">Reason for Override *</Label>
                <Textarea
                  id="reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain why you're overriding this score..."
                  className="min-h-[100px]"
                />
              </div>
              <Button className="w-full" onClick={handleOverride} disabled={isSubmitting}>
                {isSubmitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : <><Save className="mr-2 h-4 w-4" /> Apply Override</>}
              </Button>
            </CardContent>
          </Card>

          {/* AI Feedback Card */}
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-4 w-4" /> AI Feedback
              </CardTitle>
              <CardDescription>Generate AI-powered feedback for this answer</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="outline"
                className="w-full"
                onClick={handleGetFeedback}
                disabled={feedbackLoading}
              >
                {feedbackLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating...</>
                ) : (
                  <><MessageSquare className="mr-2 h-4 w-4" /> Get AI Feedback</>
                )}
              </Button>
              {feedback && (
                <div className="p-4 rounded-lg bg-muted/50 border text-sm whitespace-pre-wrap break-words">
                  {feedback}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
