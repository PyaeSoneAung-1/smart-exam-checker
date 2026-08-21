"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { dashboardApi, settingsApi } from "@/lib/api";
import type { AdminDashboard } from "@/types";
import { toast } from "sonner";
import {
  Settings, Server, Users, BookOpen, FileText, Activity,
  Save, Loader2, RotateCcw, Shield, Scale, AlertTriangle,
} from "lucide-react";

interface ScoringWeights {
  keyword: number;
  semantic: number;
  grammar: number;
  completeness: number;
}

interface Thresholds {
  plagiarism: number;
  low_score: number;
  pass_percentage: number;
}

const DEFAULT_WEIGHTS: ScoringWeights = { keyword: 30, semantic: 25, grammar: 15, completeness: 30 };
const DEFAULT_THRESHOLDS: Thresholds = { plagiarism: 60, low_score: 30, pass_percentage: 40 };

export default function AdminSettingsPage() {
  const [stats, setStats] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [weights, setWeights] = useState<ScoringWeights>(DEFAULT_WEIGHTS);
  const [thresholds, setThresholds] = useState<Thresholds>(DEFAULT_THRESHOLDS);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchInfo = async () => {
      try {
        const res = await dashboardApi.getAdmin();
        setStats(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchInfo();

    // Load scoring weights from backend API (with localStorage fallback)
    settingsApi.getAll().then((res) => {
      const data = res.data;
      // Load thresholds
      setThresholds({
        plagiarism: parseInt(data.plagiarism) || 60,
        low_score: parseInt(data.low_score) || 30,
        pass_percentage: parseInt(data.pass_percentage) || 40,
      });
      // Load scoring weights from backend
      const kw = parseInt(data.keyword_weight);
      const sw = parseInt(data.similarity_weight);
      const gw = parseInt(data.grammar_weight);
      const cw = parseInt(data.completeness_weight);
      if (kw || sw || gw || cw) {
        setWeights({
          keyword: kw || 30,
          semantic: sw || 40,
          grammar: gw || 15,
          completeness: cw || 15,
        });
      }
    }).catch(() => {
      // Fallback to localStorage
      try {
        const saved = localStorage.getItem("exam-thresholds");
        if (saved) setThresholds(JSON.parse(saved));
        const savedWeights = localStorage.getItem("exam-scoring-weights");
        if (savedWeights) setWeights(JSON.parse(savedWeights));
      } catch {}
    });
  }, []);

  const handleSave = async () => {
    // Validate weights sum to 100
    const total = weights.keyword + weights.semantic + weights.grammar + weights.completeness;
    if (Math.abs(total - 100) > 0.01) {
      toast.error(`Scoring weights must sum to 100% (currently ${total}%)`);
      return;
    }
    if (thresholds.pass_percentage < 0 || thresholds.pass_percentage > 100) {
      toast.error("Pass percentage must be between 0 and 100");
      return;
    }

    setSaving(true);
    try {
      // Save to localStorage as fallback
      localStorage.setItem("exam-scoring-weights", JSON.stringify(weights));
      localStorage.setItem("exam-thresholds", JSON.stringify(thresholds));

      // Save thresholds to backend API
      await settingsApi.updateThresholds({
        pass_percentage: thresholds.pass_percentage,
        plagiarism: thresholds.plagiarism,
        low_score: thresholds.low_score,
      });

      // Save scoring weights to backend API
      await settingsApi.updateWeights({
        keyword_weight: weights.keyword,
        similarity_weight: weights.semantic,
        grammar_weight: weights.grammar,
        completeness_weight: weights.completeness,
      });

      // Auto-rescore ALL existing answers with new weights
      try {
        const rescoreRes = await settingsApi.rescore();
        const { rescored, total: totalAnswers } = rescoreRes.data;
        toast.success(`Settings saved! ${rescored}/${totalAnswers} answers re-scored with new weights.`);
      } catch {
        toast.success("Settings saved! (Rescore failed — existing scores unchanged)");
      }
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setWeights(DEFAULT_WEIGHTS);
    setThresholds(DEFAULT_THRESHOLDS);
    localStorage.removeItem("exam-scoring-weights");
    localStorage.removeItem("exam-thresholds");
    toast.info("Settings reset to defaults");
  };

  const weightsTotal = weights.keyword + weights.semantic + weights.grammar + weights.completeness;
  const weightsValid = Math.abs(weightsTotal - 100) < 0.01;

  if (loading) {
    return <div className="text-center py-12 text-muted-foreground">Loading settings...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Settings className="h-6 w-6" /> System Settings
          </h1>
          <p className="text-muted-foreground">Configure scoring weights, thresholds, and view system info</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReset}>
            <RotateCcw className="h-4 w-4 mr-2" /> Reset Defaults
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            Save & Rescore
          </Button>
        </div>
      </div>

      {/* Scoring Weights */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" /> Scoring Weights
          </CardTitle>
          <CardDescription>
            Configure how NLP scoring components are weighted. Must sum to 100%.
            Saving will automatically re-score ALL existing answers.
            <Badge variant={weightsValid ? "default" : "destructive"} className="ml-2">
              Total: {weightsTotal}%
            </Badge>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              { key: "keyword" as const, label: "Keyword Matching", color: "text-blue-600", icon: "🔑" },
              { key: "semantic" as const, label: "Semantic Similarity", color: "text-purple-600", icon: "🧠" },
              { key: "grammar" as const, label: "Grammar Quality", color: "text-green-600", icon: "✍️" },
              { key: "completeness" as const, label: "Completeness", color: "text-orange-600", icon: "📋" },
            ].map(({ key, label, color, icon }) => (
              <div key={key} className="space-y-2">
                <Label className="flex items-center gap-2">
                  <span>{icon}</span>
                  <span className={color}>{label}</span>
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={weights[key]}
                    onChange={(e) => setWeights({ ...weights, [key]: parseInt(e.target.value) || 0 })}
                    className="w-24"
                  />
                  <span className="text-sm text-muted-foreground">%</span>
                  <div className="flex-1 h-3 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        key === "keyword" ? "bg-blue-500" :
                        key === "semantic" ? "bg-purple-500" :
                        key === "grammar" ? "bg-green-500" : "bg-orange-500"
                      }`}
                      style={{ width: `${weights[key]}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Anti-Cheating Thresholds */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" /> Anti-Cheating Thresholds
          </CardTitle>
          <CardDescription>Configure detection sensitivity thresholds</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Scale className="h-4 w-4 text-orange-500" />
                <span>Plagiarism Flag (≥)</span>
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={thresholds.plagiarism}
                  onChange={(e) => setThresholds({ ...thresholds, plagiarism: parseInt(e.target.value) || 0 })}
                  className="w-24"
                />
                <span className="text-sm text-muted-foreground">%</span>
                <Badge className="bg-orange-100 text-orange-700">Flag as Plagiarized</Badge>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <span>Low Score Alert (&lt;)</span>
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={thresholds.low_score}
                  onChange={(e) => setThresholds({ ...thresholds, low_score: parseInt(e.target.value) || 0 })}
                  className="w-24"
                />
                <span className="text-sm text-muted-foreground">%</span>
                <Badge className="bg-yellow-100 text-yellow-700">Alert</Badge>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-emerald-500" />
                <span>Pass Percentage (≥)</span>
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={thresholds.pass_percentage}
                  onChange={(e) => setThresholds({ ...thresholds, pass_percentage: parseInt(e.target.value) || 0 })}
                  className="w-24"
                />
                <span className="text-sm text-muted-foreground">%</span>
                <Badge className="bg-emerald-100 text-emerald-700">Pass/Fail</Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* System Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" /> System Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-sm text-muted-foreground">Version</span>
              <span className="text-sm font-medium">1.0.0</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-sm text-muted-foreground">Environment</span>
              <Badge variant="outline">{process.env.NODE_ENV || "development"}</Badge>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-sm text-muted-foreground">Average Score</span>
              <span className="text-sm font-medium">{(stats?.average_system_score ?? 0).toFixed(1)}%</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-sm text-muted-foreground">Recent Registrations (7d)</span>
              <span className="text-sm font-medium">{stats?.recent_registrations ?? 0}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" /> Total Statistics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { icon: Users, label: "Total Users", value: stats.total_users, color: "text-blue-600" },
                { icon: Users, label: "Students", value: stats.total_students, color: "text-green-600" },
                { icon: Users, label: "Teachers", value: stats.total_teachers, color: "text-purple-600" },
                { icon: BookOpen, label: "Subjects", value: stats.total_subjects, color: "text-orange-600" },
                { icon: FileText, label: "Exams", value: stats.total_exams, color: "text-cyan-600" },
                { icon: FileText, label: "Questions", value: stats.total_questions, color: "text-yellow-600" },
                { icon: Activity, label: "Submissions", value: stats.total_submissions, color: "text-pink-600" },
                { icon: Activity, label: "Avg Score", value: `${(stats.average_system_score ?? 0).toFixed(1)}%`, color: "text-emerald-600" },
              ].map(({ icon: Icon, label, value, color }) => (
                <div key={label} className="p-4 rounded-lg border text-center">
                  <Icon className={`h-5 w-5 mx-auto mb-2 ${color}`} />
                  <p className="text-2xl font-bold">{value ?? 0}</p>
                  <p className="text-xs text-muted-foreground">{label}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
