"use client";

import { useEffect, useState } from "react";
import { usersApi, answersApi, examsApi, subjectsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { User, Answer } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Users, Search, Mail, Trophy, Award } from "lucide-react";
import { toast } from "sonner";

interface StudentWithScore {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  total_score: number;
  exams_taken: number;
}

export default function TeacherStudentsPage() {
  const [students, setStudents] = useState<StudentWithScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    const fetchStudents = async () => {
      try {
        // Fetch students and answers in parallel
        const [studentsRes, answersRes] = await Promise.all([
          usersApi.getAll({ role: "student", limit: 500 }),
          answersApi.getAllAnswers({ limit: 10000 }),
        ]);

        const studentList: User[] = studentsRes.data.items || [];
        const answers: Answer[] = answersRes.data.items || [];

        // Aggregate scores by student
        const scoreMap: Record<number, { total_score: number; examIds: Set<number> }> = {};

        for (const answer of answers) {
          if (!scoreMap[answer.student_id]) {
            scoreMap[answer.student_id] = { total_score: 0, examIds: new Set() };
          }
          if (answer.score) {
            scoreMap[answer.student_id].total_score += answer.score.total_score;
          }
          // Track unique exams (we don't have exam_id directly, but we can count unique questions)
          scoreMap[answer.student_id].examIds.add(answer.question_id);
        }

        // Build student list with scores
        const studentsWithScores: StudentWithScore[] = studentList.map((s) => ({
          id: s.id,
          name: s.name,
          email: s.email,
          is_active: s.is_active,
          total_score: Math.round((scoreMap[s.id]?.total_score || 0) * 100) / 100,
          exams_taken: scoreMap[s.id]?.examIds.size || 0,
        }));

        // Sort by total score descending
        studentsWithScores.sort((a, b) => b.total_score - a.total_score);

        setStudents(studentsWithScores);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load students");
      } finally {
        setLoading(false);
      }
    };
    fetchStudents();
  }, []);

  const filtered = students.filter((s) =>
    !search ||
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.email.toLowerCase().includes(search.toLowerCase())
  );

  const getRankBadge = (index: number) => {
    if (index === 0) return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300">🥇 1st</Badge>;
    if (index === 1) return <Badge className="bg-gray-100 text-gray-800 border-gray-300">🥈 2nd</Badge>;
    if (index === 2) return <Badge className="bg-orange-100 text-orange-800 border-orange-300">🥉 3rd</Badge>;
    return <Badge variant="outline">{index + 1}th</Badge>;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Users className="h-6 w-6" /> Students
        </h1>
        <p className="text-muted-foreground">View students ranked by performance</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search students..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{students.length}</p>
            <p className="text-sm text-muted-foreground">Total Students</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{students.filter(s => s.total_score > 0).length}</p>
            <p className="text-sm text-muted-foreground">Active Test Takers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">
              {students.length > 0 ? Math.round(students.reduce((sum, s) => sum + s.total_score, 0) / students.length) : 0}
            </p>
            <p className="text-sm text-muted-foreground">Avg Score</p>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <p className="text-center py-12 text-muted-foreground">Loading...</p>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No students found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {/* Header row */}
          <div className="grid grid-cols-12 gap-4 px-4 py-2 text-sm font-medium text-muted-foreground">
            <div className="col-span-1">Rank</div>
            <div className="col-span-4">Student</div>
            <div className="col-span-3">Email</div>
            <div className="col-span-2 text-center">Total Score</div>
            <div className="col-span-2 text-center">Questions Answered</div>
          </div>
          {filtered.map((student, index) => (
            <Card key={student.id} className="hover:shadow-md transition-shadow">
              <CardContent className="py-4">
                <div className="grid grid-cols-12 gap-4 items-center">
                  <div className="col-span-1">
                    {getRankBadge(index)}
                  </div>
                  <div className="col-span-4 flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold text-sm">
                      {student.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium truncate">{student.name}</p>
                      <Badge variant={student.is_active ? "default" : "secondary"} className="text-xs">
                        {student.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                  </div>
                  <div className="col-span-3">
                    <p className="text-sm text-muted-foreground flex items-center gap-1 truncate">
                      <Mail className="h-3 w-3 flex-shrink-0" /> {student.email}
                    </p>
                  </div>
                  <div className="col-span-2 text-center">
                    <span className="text-lg font-bold text-primary">{student.total_score.toFixed(1)}</span>
                  </div>
                  <div className="col-span-2 text-center">
                    <Badge variant="outline">{student.exams_taken}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
