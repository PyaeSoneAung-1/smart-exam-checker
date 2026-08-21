"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { questionsApi, asApiError } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

export default function CreateQuestionPage() {
  const { id } = useParams();
  const router = useRouter();
  const [form, setForm] = useState({
    question_text: "",
    model_answer: "",
    marks: "10",
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!form.question_text || !form.model_answer) {
      toast.error("Question and model answer required");
      return;
    }
    setSaving(true);
    try {
      await questionsApi.create({
        exam_id: Number(id),
        question_text: form.question_text,
        model_answer: form.model_answer,
        marks: Number(form.marks),
      });
      toast.success("Question created!");
      router.push(`/teacher/exams/${id}`);
    } catch (err) {
      const msg = asApiError(err)?.response?.data?.detail; toast.error(typeof msg === "string" ? msg : "Failed to create question");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link href={`/teacher/exams/${id}`} className="flex items-center gap-1 text-sm text-muted-foreground hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to Exam
      </Link>

      <h1 className="text-2xl font-bold">Add New Question</h1>

      <Card>
        <CardHeader><CardTitle>Question Details</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Question Text *</Label>
            <Textarea
              value={form.question_text}
              onChange={(e) => setForm({ ...form, question_text: e.target.value })}
              placeholder="e.g. What is Natural Language Processing?"
              rows={3}
            />
          </div>
          <div>
            <Label>Model Answer * (NLP will use this to grade)</Label>
            <Textarea
              value={form.model_answer}
              onChange={(e) => setForm({ ...form, model_answer: e.target.value })}
              placeholder="The expected/correct answer that students should write..."
              rows={5}
            />
            <p className="text-xs text-muted-foreground mt-1">
              This is the ideal answer. Student answers will be compared against this using NLP.
            </p>
          </div>
          <div>
            <Label>Marks</Label>
            <Input
              type="number"
              value={form.marks}
              onChange={(e) => setForm({ ...form, marks: e.target.value })}
              min="1"
            />
          </div>
          <Button onClick={handleSave} disabled={saving} className="w-full" size="lg">
            <Save className="h-4 w-4 mr-2" />
            {saving ? "Saving..." : "Save Question"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
