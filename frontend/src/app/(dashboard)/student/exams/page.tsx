"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { examsApi, answersApi, questionsApi } from "@/lib/api";
import type { Exam, Answer } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Clock, FileText, Play, CheckCircle } from "lucide-react";
import { toast } from "sonner";

export default function StudentExamsPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [completedExamIds, setCompletedExamIds] = useState<Set<number>>(new Set());
  const [myTotalScore, setMyTotalScore] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchExams = async () => {
      try {
        const examRes = await examsApi.getAll({ limit: 500 });
        const examList: Exam[] = examRes.data.items || [];
        setExams(examList);

        try {
          const answerRes = await answersApi.getMyAnswers({ limit: 10000 });
          const myAnswers: Answer[] = answerRes.data.items || [];

          const qRes = await questionsApi.getAll({ limit: 500 });
          const questions = qRes.data.items || [];
          const questionToExam: Record<number, number> = {};
          questions.forEach((q) => { questionToExam[q.id] = q.exam_id; });

          const completedIds = new Set<number>();
          let totalScore = 0;

          for (const answer of myAnswers) {
            const examId = questionToExam[answer.question_id];
            if (examId) completedIds.add(examId);
            if (answer.score) totalScore += answer.score.total_score;
          }

          setCompletedExamIds(completedIds);
          setMyTotalScore(Math.round(totalScore * 100) / 100);
        } catch {
          // New student - no answers yet
        }
      } catch (err) {
        console.error(err);
        toast.error("Failed to load exams");
      } finally {
        setLoading(false);
      }
    };
    fetchExams();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <BookOpen className="h-8 w-8" /> Available Exams
        </h1>
        <p className="text-muted-foreground mt-1">Take exams and view your results</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold">{exams.length}</p>
            <p className="text-sm text-muted-foreground">Total Exams</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold text-green-600">{completedExamIds.size}</p>
            <p className="text-sm text-muted-foreground">Completed</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-2xl font-bold text-blue-600">{myTotalScore}</p>
            <p className="text-sm text-muted-foreground">My Total Score</p>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <p className="text-center py-12 text-muted-foreground">Loading exams...</p>
      ) : exams.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg text-muted-foreground">No exams available yet</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {exams.map((exam) => {
            const isCompleted = completedExamIds.has(exam.id);
            return (
              <Card key={exam.id} className="hover:shadow-lg transition-shadow flex flex-col">
                <CardHeader>
                  <CardTitle className="text-lg break-words">{exam.title}</CardTitle>
                  {exam.subject?.name && (
                    <p className="text-sm text-muted-foreground break-words flex items-center gap-1">
                      <BookOpen className="h-3.5 w-3.5" /> {exam.subject.name}
                    </p>
                  )}
                </CardHeader>
                <CardContent className="space-y-3 flex-1 flex flex-col">
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                      <FileText className="h-4 w-4" /> {exam.total_marks} marks
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" /> {exam.time_limit_minutes} min
                    </span>
                  </div>
                  {isCompleted ? (
                    <Badge className="bg-green-100 text-green-700 w-fit">
                      <CheckCircle className="h-3 w-3 mr-1" /> Completed
                    </Badge>
                  ) : (
                    <Badge variant={exam.is_active ? "default" : "secondary"}>
                      {exam.is_active ? "Available" : "Inactive"}
                    </Badge>
                  )}
                  <div className="pt-2 mt-auto">
                    {isCompleted ? (
                      <Link href={`/student/results`}>
                        <Button className="w-full" variant="outline">
                          <CheckCircle className="h-4 w-4 mr-2" /> View Results
                        </Button>
                      </Link>
                    ) : (
                      <Link href={`/student/exams/${exam.id}`}>
                        <Button className="w-full" disabled={!exam.is_active}>
                          <Play className="h-4 w-4 mr-2" /> Take Exam
                        </Button>
                      </Link>
                    )}
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
