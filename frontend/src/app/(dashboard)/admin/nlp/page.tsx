"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";
import { settingsApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Brain, Shield, CheckCircle, AlertCircle, Scale, Settings, Bot, FileText,
} from "lucide-react";

export default function AdminNLPPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Brain className="h-6 w-6" /> NLP Engine Dashboard
        </h1>
        <p className="text-muted-foreground">Natural Language Processing system status and configuration</p>
      </div>

      <SystemStatus />
      <ActiveFeatures />
      <ScoringConfig />
      <AntiCheatingThresholds />
    </div>
  );
}

/* ── System Status ─────────────────────────────────────────── */

interface SystemHealth {
  version: string;
  anti_cheating_status: string;
}

function SystemStatus() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get("/health/system");
        setHealth(res.data);
      } catch {
        setHealth(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardContent className="pt-6 text-center">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-100 mx-auto mb-2">
            <Brain className="h-6 w-6 text-blue-600" />
          </div>
          <p className="text-2xl font-bold">{loading ? "..." : (health?.version || "NLP v2.0")}</p>
          <p className="text-sm text-muted-foreground">Engine Version</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6 text-center">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-green-100 mx-auto mb-2">
            <CheckCircle className="h-6 w-6 text-green-600" />
          </div>
          <p className="text-2xl font-bold">4</p>
          <p className="text-sm text-muted-foreground">Active Features</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6 text-center">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-purple-100 mx-auto mb-2">
            <Shield className="h-6 w-6 text-purple-600" />
          </div>
          <p className="text-2xl font-bold">{loading ? "..." : (health?.anti_cheating_status || "Active")}</p>
          <p className="text-sm text-muted-foreground">Anti-Cheating Module</p>
        </CardContent>
      </Card>
    </div>
  );
}

/* ── Active Features ───────────────────────────────────────── */

function ActiveFeatures() {
  const features = [
    { name: "Plagiarism Detection", desc: "Cross-answer TF-IDF cosine similarity", icon: Scale, status: "Active", role: "Teacher" },
    { name: "AI Content Detection", desc: "8-signal analysis (phrases, perplexity, burstiness)", icon: Bot, status: "Active", role: "Teacher" },
    { name: "AI Auto Scan", desc: "Batch scan all students per exam", icon: Bot, status: "Active", role: "Teacher" },
    { name: "AI Feedback", desc: "Template-based answer feedback generation", icon: FileText, status: "Active", role: "Teacher" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5" /> Active NLP Features
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2">
          {features.map((f) => (
            <div key={f.name} className="flex items-start gap-3 p-3 rounded-lg border">
              <f.icon className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{f.name}</span>
                  <Badge variant="outline" className="text-xs bg-green-50 text-green-700">{f.status}</Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{f.desc}</p>
                <p className="text-xs text-muted-foreground">Role: {f.role}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Scoring Configuration ─────────────────────────────────── */

function ScoringConfig() {
  const [weights, setWeights] = useState({ keyword: 30, semantic: 25, grammar: 15, completeness: 30 });

  useEffect(() => {
    settingsApi.getAll().then((res) => {
      const data = res.data;
      setWeights({
        keyword: parseInt(data.keyword_weight) || 30,
        semantic: parseInt(data.similarity_weight) || 25,
        grammar: parseInt(data.grammar_weight) || 15,
        completeness: parseInt(data.completeness_weight) || 30,
      });
    }).catch(() => {});
  }, []);

  const items = [
    { label: "Keyword Matching", key: "keyword" as const, color: "bg-blue-500" },
    { label: "Semantic Similarity", key: "semantic" as const, color: "bg-purple-500" },
    { label: "Grammar Quality", key: "grammar" as const, color: "bg-green-500" },
    { label: "Completeness", key: "completeness" as const, color: "bg-orange-500" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Settings className="h-5 w-5" /> Scoring Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {items.map((item) => (
            <div key={item.label} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{item.label}</span>
                <span className="text-muted-foreground">{weights[item.key]}%</span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${item.color} transition-all`} style={{ width: `${weights[item.key]}%` }} />
              </div>
            </div>
          ))}
          <p className="text-xs text-muted-foreground mt-2">
            Configure weights in <a href="/admin/settings" className="underline text-primary">Settings</a> page.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Anti-Cheating Thresholds ──────────────────────────────── */

function AntiCheatingThresholds() {
  const [thresholds, setThresholds] = useState({ plagiarism: 60, low_score: 30, pass_percentage: 40 });

  useEffect(() => {
    settingsApi.getAll().then((res) => {
      const data = res.data;
      setThresholds({
        plagiarism: parseInt(data.plagiarism) || 60,
        low_score: parseInt(data.low_score) || 30,
        pass_percentage: parseInt(data.pass_percentage) || 40,
      });
    }).catch(() => {});
  }, []);

  const items = [
    { label: "Plagiarism Flag", value: `≥ ${thresholds.plagiarism}% similarity`, color: "text-orange-600", icon: Scale },
    { label: "Low Score Alert", value: `< ${thresholds.low_score}% total score`, color: "text-yellow-600", icon: AlertCircle },
    { label: "Pass Percentage", value: `≥ ${thresholds.pass_percentage}% to pass`, color: "text-emerald-600", icon: CheckCircle },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><AlertCircle className="h-5 w-5" /> Anti-Cheating Thresholds</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {items.map((t) => (
            <div key={t.label} className="flex items-center justify-between p-3 rounded-lg border">
              <div className="flex items-center gap-2">
                <t.icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t.label}</span>
              </div>
              <span className={`text-sm font-bold ${t.color}`}>{t.value}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
