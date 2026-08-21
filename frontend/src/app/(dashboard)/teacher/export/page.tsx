"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { examsApi, exportApi } from "@/lib/api";
import type { Exam } from "@/types";
import ExportButton from "@/components/shared/ExportButton";
import { toast } from "sonner";
import { FileText, Table, Download, Eye, Loader2 } from "lucide-react";

export default function TeacherExportPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<any[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    const fetchExams = async () => {
      try {
        const res = await examsApi.getAll();
        setExams(res.data.items || []);
      } catch {
        toast.error("Failed to load exams");
      } finally {
        setLoading(false);
      }
    };
    fetchExams();
  }, []);

  const selectedExam = exams.find((e) => e.id === Number(selectedExamId));

  const handlePreview = async () => {
    if (!selectedExamId) return;
    setPreviewLoading(true);
    try {
      const res = await exportApi.exportResults(Number(selectedExamId));
      // If it returns JSON-like data for preview
      if (res.data instanceof Blob) {
        const text = await res.data.text();
        try {
          const data = JSON.parse(text);
          setPreview(Array.isArray(data) ? data : data.results || []);
        } catch {
          setPreview(null);
          toast.info("Preview not available for this format. Use download instead.");
        }
      } else {
        setPreview(Array.isArray(res.data) ? res.data : res.data.results || []);
      }
    } catch {
      toast.error("Failed to generate preview");
    } finally {
      setPreviewLoading(false);
    }
  };

  const generateCSV = async (): Promise<string> => {
    if (!selectedExamId) throw new Error("No exam selected");
    const res = await exportApi.exportResults(Number(selectedExamId));

    if (res.data instanceof Blob) {
      const text = await res.data.text();
      // If already CSV
      if (text.includes(",")) return text;
    }

    // Generate CSV from preview data
    if (!preview || preview.length === 0) {
      throw new Error("No data to export. Load preview first.");
    }

    const headers = Object.keys(preview[0]);
    const rows = preview.map((row) =>
      headers.map((h) => {
        const val = row[h];
        if (typeof val === "string" && (val.includes(",") || val.includes('"'))) {
          return `"${val.replace(/"/g, '""')}"`;
        }
        return String(val ?? "");
      }).join(",")
    );
    return [headers.join(","), ...rows].join("\n");
  };

  const handleExportPDF = async (): Promise<Blob | void> => {
    if (!selectedExamId) throw new Error("No exam selected");
    const res = await exportApi.exportResults(Number(selectedExamId));
    if (res.data instanceof Blob) return res.data;
    // If JSON, create a simple text blob
    const text = JSON.stringify(res.data, null, 2);
    return new Blob([text], { type: "application/pdf" });
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        <div className="h-64 bg-muted animate-pulse rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Export Results</h1>
        <p className="text-muted-foreground">Export exam results as PDF or CSV</p>
      </div>

      {/* Exam selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Exam</CardTitle>
          <CardDescription>Choose an exam to export its results</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Exam</Label>
            <Select value={selectedExamId} onValueChange={(v) => setSelectedExamId(v ?? "")}>
              <SelectTrigger>
                <SelectValue placeholder="Select an exam..." />
              </SelectTrigger>
              <SelectContent>
                {exams.map((exam) => (
                  <SelectItem key={exam.id} value={String(exam.id)}>
                    {exam.title} — {exam.total_marks} marks
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedExam && (
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{selectedExam.total_marks} marks</Badge>
              <Badge variant="outline">{selectedExam.time_limit_minutes} min</Badge>
              <Badge variant="outline">{selectedExam.is_active ? "Active" : "Inactive"}</Badge>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      {selectedExamId && (
        <Card>
          <CardHeader>
            <CardTitle>Export Options</CardTitle>
            <CardDescription>Preview or download the results</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" onClick={handlePreview} disabled={previewLoading}>
                {previewLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Eye className="mr-2 h-4 w-4" />
                )}
                Preview
              </Button>

              <ExportButton
                onExportPDF={handleExportPDF}
                onExportCSV={generateCSV}
              />
            </div>

            <Separator />

            {/* Export format descriptions */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex items-start gap-3 p-4 rounded-lg border">
                <FileText className="h-8 w-8 text-red-500 shrink-0" />
                <div>
                  <p className="font-medium">PDF Report Cards</p>
                  <p className="text-sm text-muted-foreground">
                    Individual report cards with scores, feedback, and performance breakdown per student.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-4 rounded-lg border">
                <Table className="h-8 w-8 text-green-500 shrink-0" />
                <div>
                  <p className="font-medium">CSV Spreadsheet</p>
                  <p className="text-sm text-muted-foreground">
                    Marks spreadsheet with all students, scores, and grades in tabular format.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Preview table */}
      {preview && preview.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Preview — {selectedExam?.title}</CardTitle>
            <CardDescription>{preview.length} records found</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    {Object.keys(preview[0]).map((key) => (
                      <th key={key} className="text-left p-3 font-medium text-muted-foreground">
                        {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.slice(0, 50).map((row, idx) => (
                    <tr key={idx} className="border-b hover:bg-muted/50">
                      {Object.values(row).map((val, col) => (
                        <td key={col} className="p-3 max-w-[200px] truncate">
                          {typeof val === "number" ? val.toFixed(2) : String(val ?? "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {preview.length > 50 && (
                <p className="text-center text-sm text-muted-foreground py-3">
                  Showing first 50 of {preview.length} records
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
