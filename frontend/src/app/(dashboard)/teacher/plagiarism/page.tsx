"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";
import { examsApi } from "@/lib/api";
import { usersApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Scale, Loader2, CheckCircle } from "lucide-react";
import { toast } from "sonner";

export default function TeacherPlagiarismPage() {
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExam, setSelectedExam] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [students, setStudents] = useState<any[]>([]);

  useEffect(() => {
    examsApi.getAll({ limit: 100 }).then((res) => {
      setExams(res.data.items || []);
    }).catch(() => {});
    usersApi.getAll({ role: 'student', limit: 100 }).then((res) => {
      setStudents(res.data.items || []);
    }).catch(() => {});
  }, []);

  const handleRun = async () => {
    if (!selectedExam) { toast.error("Select an exam"); return; }
    setLoading(true);
    try {
      const res = await api.post("/nlp/plagiarism-check", { exam_id: parseInt(selectedExam) });
      setResult(res.data);
      toast.success("Plagiarism check complete");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || "Plagiarism check failed");
    } finally {
      setLoading(false);
    }
  };

  const pairs = result?.pairs || [];
  const nameMap: Record<number, string> = {};
  students.forEach((s) => { nameMap[s.id] = s.name; });

  // Use backend summary (respects DB plagiarism threshold)
  const totalPairs = result?.summary?.total_pairs ?? pairs.length;
  const flaggedPairs = result?.summary?.flagged_pairs ?? pairs.filter((p: any) => p.flagged === true).length;
  const maxSimilarity = result?.summary?.max_similarity ?? (totalPairs > 0
    ? Math.max(...pairs.map((p: any) => p.similarity || 0))
    : 0);

  const getSimilarityColor = (sim: number) => {
    if (sim >= 0.80) return "bg-red-100 text-red-700";
    if (sim >= 0.50) return "bg-yellow-100 text-yellow-700";
    return "bg-green-100 text-green-700";
  };

  const getStudentName = (pair: any, key: string) => {
    const id = pair[key] || pair[`${key}_id`] || pair[key.replace('_', '')] || pair[key.replace('_', '1')];
    return nameMap[id] || id || "Student ?";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Scale className="h-6 w-6" /> Plagiarism Check
        </h1>
        <p className="text-muted-foreground">Detect potential plagiarism by comparing student answers for an exam</p>
      </div>

      {/* Exam Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Select Exam</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <Select value={selectedExam} onValueChange={(v) => setSelectedExam(v ?? "")}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an exam..." />
                </SelectTrigger>
                <SelectContent>
                  {exams.map((exam: any) => (
                    <SelectItem key={exam.id} value={String(exam.id)}>
                      {exam.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleRun} disabled={loading || !selectedExam}>
              {loading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Scale className="h-4 w-4 mr-2" />
              )}
              {loading ? "Checking..." : "Run Plagiarism Check"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-100 mx-auto mb-2">
                  <Scale className="h-6 w-6 text-blue-600" />
                </div>
                <p className="text-2xl font-bold">{totalPairs}</p>
                <p className="text-sm text-muted-foreground">Total Pairs</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-100 mx-auto mb-2">
                  <Scale className="h-6 w-6 text-red-600" />
                </div>
                <p className="text-2xl font-bold">{flaggedPairs}</p>
                <p className="text-sm text-muted-foreground">Flagged Pairs</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-orange-100 mx-auto mb-2">
                  <Scale className="h-6 w-6 text-orange-600" />
                </div>
                <p className="text-2xl font-bold">{(maxSimilarity * 100).toFixed(1)}%</p>
                <p className="text-sm text-muted-foreground">Max Similarity</p>
              </CardContent>
            </Card>
          </div>

          {/* Flagged Pairs List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Scale className="h-5 w-5" /> Plagiarism Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {pairs.length === 0 ? (
                <div className="flex items-center justify-center gap-2 py-8 text-green-600">
                  <CheckCircle className="h-5 w-5" />
                  <span className="font-medium">No plagiarism detected</span>
                </div>
              ) : (
                <div className="space-y-3">
                  {pairs.map((pair: any, i: number) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 p-4 rounded-lg border bg-background text-sm"
                    >
                      <Badge variant="outline" className="shrink-0">
                        Pair {i + 1}
                      </Badge>
                      <span className="text-muted-foreground">
                        {getStudentName(pair, "student_1_id")} ↔ {getStudentName(pair, "student_2_id")}
                      </span>
                      {pair.question_text && (
                        <span className="text-xs text-muted-foreground truncate max-w-xs">
                          Q: {pair.question_text}
                        </span>
                      )}
                      {pair.similarity !== undefined && (
                        <Badge className={`ml-auto ${getSimilarityColor(pair.similarity)}`}>
                          {(pair.similarity * 100).toFixed(1)}% similar
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
