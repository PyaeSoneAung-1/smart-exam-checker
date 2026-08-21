"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { answersApi } from "@/lib/api";
import type { Answer } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";

export default function StudentResultDetailPage() {
  const { id } = useParams();
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await answersApi.getMyAnswers({ limit: 500 });
        const all = res.data.items || [];
        // Filter by question_id if id is a question id, or show all for an exam
        setAnswers(all);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  if (loading) return <div className="text-center py-12 text-muted-foreground">Loading...</div>;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link href="/student/results" className="flex items-center gap-1 text-sm text-muted-foreground hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to Results
      </Link>
      <h1 className="text-2xl font-bold">Result Detail</h1>

      {answers.length === 0 ? (
        <p className="text-muted-foreground">No results found</p>
      ) : (
        answers.map((a) => (
          <Card key={a.id}>
            <CardHeader>
              <CardTitle className="text-base">{a.question?.question_text || `Question #${a.question_id}`}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Your Answer:</p>
                <p className="mt-1">{a.answer_text}</p>
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
        ))
      )}
    </div>
  );
}
