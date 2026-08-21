"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { subjectsApi, examsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { Subject } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Search, FileText, Users } from "lucide-react";
import { toast } from "sonner";

export default function TeacherSubjectsPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [examCounts, setExamCounts] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const user = useAuthStore((s) => s.user);

  const fetchData = async () => {
    try {
      const [subRes, examRes] = await Promise.all([
        subjectsApi.getAll({ limit: 500 }),
        examsApi.getAll({ limit: 500 }),
      ]);
      const allSubjects = subRes.data.items || [];
      const allExams = examRes.data.items || [];

      // Filter subjects to only those belonging to this teacher
      const mySubjects = allSubjects.filter((s) => s.teacher_id === user?.id);
      const displaySubjects = mySubjects.length > 0 ? mySubjects : allSubjects;

      // Count exams per subject
      const counts: Record<number, number> = {};
      for (const exam of allExams) {
        counts[exam.subject_id] = (counts[exam.subject_id] || 0) + 1;
      }

      setSubjects(displaySubjects);
      setExamCounts(counts);
    } catch (err) {
      console.error(err);
      toast.error("Failed to load subjects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const filtered = subjects.filter((s) =>
    !search || s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BookOpen className="h-6 w-6" /> My Subjects
          </h1>
          <p className="text-muted-foreground">View your assigned subjects</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search subjects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{subjects.length}</p>
            <p className="text-sm text-muted-foreground">Total Subjects</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{Object.values(examCounts).reduce((a, b) => a + b, 0)}</p>
            <p className="text-sm text-muted-foreground">Total Exams</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{subjects.length > 0 ? Math.round(Object.values(examCounts).reduce((a, b) => a + b, 0) / subjects.length) : 0}</p>
            <p className="text-sm text-muted-foreground">Avg Exams / Subject</p>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <p className="text-center py-12 text-muted-foreground">Loading...</p>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <BookOpen className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">{search ? "No subjects match your search" : "No subjects assigned yet."}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((subject) => (
            <Card key={subject.id} className="hover:shadow-md transition-shadow flex flex-col">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg leading-tight break-words flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary shrink-0" />
                  {subject.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 flex-1 flex flex-col">
                {subject.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2 break-words">{subject.description}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="flex items-center gap-1">
                    <FileText className="h-3 w-3" /> {examCounts[subject.id] || 0} exams
                  </Badge>
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Users className="h-3 w-3" /> Subject
                  </Badge>
                </div>
                <div className="flex gap-2 pt-2 mt-auto">
                  <Link href={`/teacher/exams?subject_id=${subject.id}`} className="flex-1">
                    <Button variant="outline" className="w-full" size="sm">
                      <FileText className="h-4 w-4 mr-1" /> View Exams
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
