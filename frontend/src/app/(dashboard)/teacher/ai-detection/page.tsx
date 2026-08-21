"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";
import { examsApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Bot, Loader2, Search, AlertTriangle, CheckCircle, Shield,
  Brain, Users, TrendingUp,
} from "lucide-react";
import { toast } from "sonner";

/* ── Types ───────────────────────────────────────────────── */

interface ScanResult {
  student_id: number;
  student_name: string;
  ai_probability: number;
  perplexity: number;
  burstiness: number;
  vocabulary_richness: number;
  ai_phrases_found: string[];
  answer_count: number;
  verdict: string;
}

interface ScanSummary {
  total: number;
  ai_detected: number;
  uncertain: number;
  human: number;
}

interface DetectionResult {
  ai_probability: number;
  perplexity: number;
  burstiness: number;
  vocabulary_richness: number;
  ai_phrases_found: string[];
  verdict?: string;
}

/* ── Main Page ───────────────────────────────────────────── */

export default function TeacherAIDetectionPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bot className="h-6 w-6" /> AI Detection
        </h1>
        <p className="text-muted-foreground">
          Detect AI-generated content in student answers using multi-signal analysis
        </p>
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>
            Results are a statistical signal, not proof. Short or technical answers can
            be misjudged — always review suspicious answers manually before acting.
          </span>
        </div>
      </div>

      <Tabs defaultValue="scan" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="scan" className="gap-1.5">
            <Users className="h-4 w-4" /> Auto Scan (Exam)
          </TabsTrigger>
          <TabsTrigger value="single" className="gap-1.5">
            <Search className="h-4 w-4" /> Single Text
          </TabsTrigger>
        </TabsList>

        <TabsContent value="scan"><AutoScanTab /></TabsContent>
        <TabsContent value="single"><SingleTextTab /></TabsContent>
      </Tabs>
    </div>
  );
}

/* ── Auto Scan Tab ───────────────────────────────────────── */

function AutoScanTab() {
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExam, setSelectedExam] = useState("");
  const [results, setResults] = useState<ScanResult[] | null>(null);
  const [summary, setSummary] = useState<ScanSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    examsApi.getAll({ limit: 100 }).then((res) => {
      setExams(res.data.items || []);
    }).catch(() => {});
  }, []);

  const handleScan = async () => {
    if (!selectedExam) { toast.error("Select an exam"); return; }
    setLoading(true);
    setResults(null);
    setSummary(null);
    try {
      const res = await api.post("/nlp/ai-auto-scan", { exam_id: parseInt(selectedExam) });
      setResults(res.data.results || []);
      setSummary(res.data.summary || null);
      const total = res.data.summary?.total || 0;
      const ai = res.data.summary?.ai_detected || 0;
      toast.success(`Scan complete: ${total} students analyzed, ${ai} AI detected`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || "AI scan failed");
    } finally {
      setLoading(false);
    }
  };

  const getVerdictColor = (verdict: string) => {
    if (verdict === "AI Detected") return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    if (verdict === "Uncertain") return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
    return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
  };

  const getVerdictIcon = (verdict: string) => {
    if (verdict === "AI Detected") return <AlertTriangle className="h-3.5 w-3.5" />;
    if (verdict === "Uncertain") return <Shield className="h-3.5 w-3.5" />;
    return <CheckCircle className="h-3.5 w-3.5" />;
  };

  return (
    <div className="space-y-4">
      {/* Exam Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Select Exam to Scan</CardTitle>
        </CardHeader>
        <CardContent>
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
            <Button onClick={handleScan} disabled={loading || !selectedExam}>
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Bot className="h-4 w-4 mr-2" />}
              {loading ? "Scanning..." : "Run AI Scan"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6 text-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-100 mx-auto mb-2">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <p className="text-2xl font-bold">{summary.total}</p>
              <p className="text-sm text-muted-foreground">Total Scanned</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-100 mx-auto mb-2">
                <AlertTriangle className="h-6 w-6 text-red-600" />
              </div>
              <p className="text-2xl font-bold text-red-600">{summary.ai_detected}</p>
              <p className="text-sm text-muted-foreground">AI Detected</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-yellow-100 mx-auto mb-2">
                <Shield className="h-6 w-6 text-yellow-600" />
              </div>
              <p className="text-2xl font-bold text-yellow-600">{summary.uncertain}</p>
              <p className="text-sm text-muted-foreground">Uncertain</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-green-100 mx-auto mb-2">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <p className="text-2xl font-bold text-green-600">{summary.human}</p>
              <p className="text-sm text-muted-foreground">Likely Human</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Results Table */}
      {results && results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" /> Detection Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {results.map((r) => (
                <div
                  key={r.student_id}
                  className="flex items-center gap-4 p-4 rounded-lg border bg-background"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{r.student_name}</span>
                      <Badge className={getVerdictColor(r.verdict)}>
                        {getVerdictIcon(r.verdict)}
                        <span className="ml-1">{r.verdict}</span>
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <span>Perplexity: {r.perplexity}</span>
                      <span>Burstiness: {r.burstiness}</span>
                      <span>Vocab: {r.vocabulary_richness}</span>
                      <span>Answers: {r.answer_count}</span>
                    </div>
                    {r.ai_phrases_found && r.ai_phrases_found.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {r.ai_phrases_found.slice(0, 5).map((phrase, i) => (
                          <Badge key={i} variant="outline" className="text-xs bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400">
                            {phrase}
                          </Badge>
                        ))}
                        {r.ai_phrases_found.length > 5 && (
                          <Badge variant="outline" className="text-xs">+{r.ai_phrases_found.length - 5} more</Badge>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className="relative w-16 h-16">
                      <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
                        <path
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="currentColor"
                          className="text-muted"
                          strokeWidth="3"
                        />
                        <path
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="currentColor"
                          className={
                            r.ai_probability >= 45 ? "text-red-500" :
                            r.ai_probability >= 25 ? "text-yellow-500" : "text-green-500"
                          }
                          strokeWidth="3"
                          strokeDasharray={`${r.ai_probability}, 100`}
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-sm font-bold">{r.ai_probability}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {results && results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-4" />
            <p className="font-medium">No student answers found for this exam</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ── Single Text Tab ─────────────────────────────────────── */

function SingleTextTab() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleDetect = async () => {
    if (!text.trim()) { toast.error("Please enter text to analyze"); return; }
    setLoading(true);
    setResult(null);
    try {
      const res = await api.post("/nlp/ai-detection", { text: text.trim() });
      setResult(res.data);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || "Detection failed");
    } finally {
      setLoading(false);
    }
  };

  const getVerdict = (prob: number): string => {
    if (prob >= 45) return "AI Detected";
    if (prob >= 25) return "Uncertain";
    return "Likely Human";
  };

  const getVerdictColor = (prob: number) => {
    if (prob >= 45) return "text-red-600";
    if (prob >= 25) return "text-yellow-600";
    return "text-green-600";
  };

  // Backend returns ai_probability as 0-1; convert to 0-100 for display.
  // (defensive: if a backend ever sends 0-100 already, pass it through)
  const aiPercent = result
    ? Math.max(0, Math.min(100, result.ai_probability > 1 ? result.ai_probability : result.ai_probability * 100))
    : 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Analyze Text for AI Content</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste student answer text here to analyze..."
            rows={8}
            className="resize-y"
          />
          <div className="flex items-center gap-4">
            <Button onClick={handleDetect} disabled={loading || !text.trim()}>
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Bot className="h-4 w-4 mr-2" />}
              {loading ? "Analyzing..." : "Analyze Text"}
            </Button>
            <span className="text-sm text-muted-foreground">{text.length} characters</span>
          </div>
        </CardContent>
      </Card>

      {result && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Verdict Card */}
          <Card>
            <CardContent className="pt-6 text-center">
              <div className="relative w-24 h-24 mx-auto mb-4">
                <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none" stroke="currentColor" className="text-muted" strokeWidth="3"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none" stroke="currentColor"
                    className={aiPercent >= 45 ? "text-red-500" : aiPercent >= 25 ? "text-yellow-500" : "text-green-500"}
                    strokeWidth="3" strokeDasharray={`${aiPercent}, 100`}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xl font-bold">{aiPercent.toFixed(1)}%</span>
                </div>
              </div>
              <p className={`text-lg font-bold ${getVerdictColor(aiPercent)}`}>
                {getVerdict(aiPercent)}
              </p>
            </CardContent>
          </Card>

          {/* Metrics Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="h-4 w-4" /> Detection Metrics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: "Perplexity", value: result.perplexity?.toFixed(2), desc: "Lower = more predictable (AI-like)" },
                { label: "Burstiness", value: result.burstiness?.toFixed(2), desc: "Higher = more varied sentence length" },
                { label: "Vocabulary Richness", value: result.vocabulary_richness?.toFixed(2), desc: "Higher = more diverse word usage" },
              ].map((m) => (
                <div key={m.label} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium">{m.label}</p>
                    <p className="text-xs text-muted-foreground">{m.desc}</p>
                  </div>
                  <span className="text-sm font-bold">{m.value}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* AI Phrases Found */}
          {result.ai_phrases_found && result.ai_phrases_found.length > 0 && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-500" /> AI Phrases Detected
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {result.ai_phrases_found.map((phrase, i) => (
                    <Badge key={i} variant="outline" className="bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400">
                      "{phrase}"
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
