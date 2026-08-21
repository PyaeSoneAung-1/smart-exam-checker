"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { examsApi, questionsApi } from "@/lib/api";
import type { Exam, Question } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Plus, Trash2, FileText, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "sonner";

export default function TeacherExamDetailPage() {
  const { id } = useParams();
  const [exam, setExam] = useState<Exam | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const fetchData = async () => {
    try {
      const [examRes, qRes] = await Promise.all([
        examsApi.getById(Number(id)),
        questionsApi.getAll({ exam_id: Number(id) }),
      ]);
      setExam(examRes.data);
      setQuestions(qRes.data.items || []);
    } catch (err) {
      console.error(err);
      toast.error("Failed to load exam");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [id]);

  const handleDeleteQuestion = async (q: Question) => {
    if (!confirm("Delete this question?")) return;
    try {
      await questionsApi.delete(q.id);
      toast.success("Question deleted");
      fetchData();
    } catch (err) {
      toast.error("Failed to delete question");
    }
  };

  const toggleExpand = (qId: number) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(qId)) next.delete(qId);
      else next.add(qId);
      return next;
    });
  };

  if (loading) return <div className="text-center py-12 text-muted-foreground">Loading...</div>;
  if (!exam) return <div className="text-center py-12">Exam not found</div>;

  return (
    <div className="space-y-6">
      <Link href="/teacher/exams" className="flex items-center gap-1 text-sm text-muted-foreground hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to Exams
      </Link>

      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold break-words">{exam.title}</h1>
          <p className="text-muted-foreground break-words">{exam.description || "No description"}</p>
          <div className="flex gap-2 mt-2 flex-wrap">
            <Badge>{exam.total_marks} marks</Badge>
            <Badge variant="outline">{exam.time_limit_minutes} min</Badge>
            <Badge variant="secondary">{questions.length} questions</Badge>
          </div>
        </div>
        <Link href={`/teacher/exams/${id}/questions/new`}>
          <Button><Plus className="h-4 w-4 mr-2" /> Add Question</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Questions ({questions.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {questions.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No questions yet. Add your first question!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {questions.map((q, idx) => {
                const isExpanded = expandedIds.has(q.id);
                const modelAnswer = q.model_answer || "";
                const isLong = modelAnswer.length > 120;

                return (
                  <div key={q.id} className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0 space-y-2">
                        {/* Question number and text */}
                        <div className="flex items-start gap-3">
                          <Badge variant="outline" className="shrink-0 mt-0.5">Q{idx + 1}</Badge>
                          <p className="text-sm font-medium break-words flex-1">{q.question_text}</p>
                        </div>

                        {/* Model answer */}
                        <div className="ml-12">
                          <p className="text-xs text-muted-foreground mb-1">Model Answer:</p>
                          <p className={`text-sm text-muted-foreground break-words ${!isExpanded && isLong ? "line-clamp-3" : ""}`}>
                            {modelAnswer}
                          </p>
                          {isLong && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs mt-1"
                              onClick={() => toggleExpand(q.id)}
                            >
                              {isExpanded ? (
                                <><ChevronUp className="h-3 w-3 mr-1" /> Show less</>
                              ) : (
                                <><ChevronDown className="h-3 w-3 mr-1" /> Show more</>
                              )}
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Marks + Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="outline">{q.marks} marks</Badge>
                        <Button size="sm" variant="destructive" onClick={() => handleDeleteQuestion(q)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
