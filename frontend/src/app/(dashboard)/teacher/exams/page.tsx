"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { examsApi, subjectsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { Exam, Subject } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText, Plus, Eye, Trash2, Search, Clock, Hash } from "lucide-react";
import { toast } from "sonner";

export default function TeacherExamsPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({ title: "", description: "", subject_id: "", total_marks: "20", time_limit_minutes: "30" });

  const user = useAuthStore((s) => s.user);

  const fetchData = async () => {
    try {
      const [examRes, subRes] = await Promise.all([
        examsApi.getAll({ limit: 500 }),
        subjectsApi.getAll({ limit: 500 }),
      ]);
      // Backend already filters teacher exams, but also filter on frontend as backup
      const allExams = examRes.data.items || [];
      const allSubjects = subRes.data.items || [];

      // Filter subjects to only those belonging to this teacher
      const mySubjects = allSubjects.filter((s) => s.teacher_id === user?.id);
      const mySubjectIds = new Set(mySubjects.map((s) => s.id));

      // Filter exams to only those for this teacher's subjects
      const myExams = allExams.filter((e) => mySubjectIds.has(e.subject_id));

      setExams(myExams.length > 0 ? myExams : allExams);
      setSubjects(mySubjects.length > 0 ? mySubjects : allSubjects);
    } catch (err) {
      console.error(err);
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreate = async () => {
    if (!form.title || !form.subject_id) {
      toast.error("Title and subject required");
      return;
    }
    try {
      await examsApi.create({
        title: form.title,
        description: form.description,
        subject_id: Number(form.subject_id),
        total_marks: Number(form.total_marks),
        time_limit_minutes: Number(form.time_limit_minutes),
      });
      toast.success(`Exam "${form.title}" created`);
      setForm({ title: "", description: "", subject_id: "", total_marks: "20", time_limit_minutes: "30" });
      setDialogOpen(false);
      fetchData();
    } catch (err: any) {
      const msg = err?.response?.data?.detail; toast.error(typeof msg === "string" ? msg : "Failed to create exam");
    }
  };

  const handleDelete = async (exam: Exam) => {
    if (!confirm(`Delete "${exam.title}"?`)) return;
    try {
      await examsApi.delete(exam.id);
      toast.success("Exam deleted");
      fetchData();
    } catch (err) {
      toast.error("Failed to delete exam");
    }
  };

  const filtered = exams.filter((e) =>
    !search || e.title.toLowerCase().includes(search.toLowerCase()) ||
    e.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="h-6 w-6" /> My Exams
          </h1>
          <p className="text-muted-foreground">Create and manage your exams</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger>
            <Button><Plus className="h-4 w-4 mr-2" /> Create Exam</Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle>Create New Exam</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Title</Label>
                <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Midterm Exam" />
              </div>
              <div className="space-y-2">
                <Label>Subject</Label>
                <Select value={form.subject_id} onValueChange={(v) => setForm({ ...form, subject_id: v ?? "" })}>
                  <SelectTrigger><SelectValue placeholder="Select subject" /></SelectTrigger>
                  <SelectContent>
                    {subjects.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Total Marks</Label>
                  <Input type="number" value={form.total_marks} onChange={(e) => setForm({ ...form, total_marks: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Time (minutes)</Label>
                  <Input type="number" value={form.time_limit_minutes} onChange={(e) => setForm({ ...form, time_limit_minutes: e.target.value })} />
                </div>
              </div>
              <Button onClick={handleCreate} className="w-full">Create Exam</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search exams..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{exams.length}</p>
            <p className="text-sm text-muted-foreground">Total Exams</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{exams.filter(e => e.is_active).length}</p>
            <p className="text-sm text-muted-foreground">Active</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{subjects.length}</p>
            <p className="text-sm text-muted-foreground">My Subjects</p>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <p className="text-center py-12 text-muted-foreground">Loading...</p>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">{search ? "No exams match your search" : "No exams yet. Create your first exam!"}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((exam) => {
            const subjectName = subjects.find(s => s.id === exam.subject_id)?.name;
            return (
              <Card key={exam.id} className="hover:shadow-md transition-shadow flex flex-col">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg leading-tight break-words">{exam.title}</CardTitle>
                  {subjectName && <p className="text-sm text-muted-foreground break-words">{subjectName}</p>}
                </CardHeader>
                <CardContent className="space-y-3 flex-1 flex flex-col">
                  {exam.description && <p className="text-sm text-muted-foreground line-clamp-2 break-words">{exam.description}</p>}
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline" className="flex items-center gap-1">
                      <FileText className="h-3 w-3" /> {exam.total_marks} marks
                    </Badge>
                    <Badge variant="outline" className="flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {exam.time_limit_minutes} min
                    </Badge>
                    {exam.questions && (
                      <Badge variant="outline" className="flex items-center gap-1">
                        <Hash className="h-3 w-3" /> {exam.questions.length} Qs
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {exam.is_active ? (
                      <Badge className="bg-green-100 text-green-700">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </div>
                  <div className="flex gap-2 pt-2 mt-auto">
                    <Link href={`/teacher/exams/${exam.id}`} className="flex-1">
                      <Button variant="outline" className="w-full" size="sm">
                        <Eye className="h-4 w-4 mr-1" /> View
                      </Button>
                    </Link>
                    <Button variant="destructive" size="icon" className="h-9 w-9" onClick={() => handleDelete(exam)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
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
