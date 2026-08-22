"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { examsApi, questionsApi } from "@/lib/api";
import type { Exam, Question } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { ArrowLeft, Plus, Trash2, FileText, ChevronDown, ChevronUp, Pencil, CalendarDays } from "lucide-react";
import { toast } from "sonner";
import { formatUtcDateTime, toLocalInputValue } from "@/lib/utils";

export default function TeacherExamDetailPage() {
  const { id } = useParams();
  const [exam, setExam] = useState<Exam | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [editOpen, setEditOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editForm, setEditForm] = useState({
    title: "",
    description: "",
    total_marks: "",
    time_limit_minutes: "",
    is_active: true,
    available_from: "",
    available_until: "",
  });

  const fetchData = useCallback(async () => {
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
  }, [id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDeleteQuestion = async (q: Question) => {
    if (!confirm("Delete this question?")) return;
    try {
      await questionsApi.delete(q.id);
      toast.success("Question deleted");
      fetchData();
    } catch {
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

  const handleOpenEdit = () => {
    if (!exam) return;
    setEditForm({
      title: exam.title,
      description: exam.description || "",
      total_marks: String(exam.total_marks),
      time_limit_minutes: String(exam.time_limit_minutes ?? ""),
      is_active: exam.is_active,
      available_from: toLocalInputValue(exam.available_from),
      available_until: toLocalInputValue(exam.available_until),
    });
    setEditOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!exam) return;
    if (!editForm.title.trim()) {
      toast.error("Title is required");
      return;
    }
    const availableFrom = editForm.available_from ? new Date(editForm.available_from).toISOString() : null;
    const availableUntil = editForm.available_until ? new Date(editForm.available_until).toISOString() : null;
    if (availableFrom && availableUntil && availableUntil <= availableFrom) {
      toast.error("End date must be after start date");
      return;
    }
    setSaving(true);
    try {
      await examsApi.update(exam.id, {
        title: editForm.title.trim(),
        description: editForm.description || undefined,
        total_marks: Number(editForm.total_marks),
        time_limit_minutes: editForm.time_limit_minutes ? Number(editForm.time_limit_minutes) : undefined,
        is_active: editForm.is_active,
        available_from: availableFrom,
        available_until: availableUntil,
      });
      toast.success("Exam updated");
      setEditOpen(false);
      fetchData();
    } catch (err) {
      console.error(err);
      toast.error("Failed to update exam");
    } finally {
      setSaving(false);
    }
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
            {(exam.available_from || exam.available_until) && (
              <Badge variant="outline" className="flex items-center gap-1">
                <CalendarDays className="h-3 w-3" />
                {exam.available_from ? formatUtcDateTime(exam.available_from) : "—"} → {exam.available_until ? formatUtcDateTime(exam.available_until) : "—"}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleOpenEdit}>
            <Pencil className="h-4 w-4 mr-2" /> Edit Exam
          </Button>
          <Link href={`/teacher/exams/${id}/questions/new`}>
            <Button><Plus className="h-4 w-4 mr-2" /> Add Question</Button>
          </Link>
        </div>
      </div>

      {/* Edit exam dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Edit Exam</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Title</Label>
              <Input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} placeholder="Optional" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Total Marks</Label>
                <Input type="number" value={editForm.total_marks} onChange={(e) => setEditForm({ ...editForm, total_marks: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Time (minutes)</Label>
                <Input type="number" value={editForm.time_limit_minutes} onChange={(e) => setEditForm({ ...editForm, time_limit_minutes: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Available From (optional)</Label>
                <Input type="datetime-local" value={editForm.available_from} onChange={(e) => setEditForm({ ...editForm, available_from: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Available Until (optional)</Label>
                <Input type="datetime-local" value={editForm.available_until} onChange={(e) => setEditForm({ ...editForm, available_until: e.target.value })} />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Students can only take the exam inside this window. Leave empty for no date restriction.
            </p>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                className="h-4 w-4"
              />
              Exam is active (visible to students)
            </label>
            <Button onClick={handleSaveEdit} disabled={saving} className="w-full">
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

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
