"use client";

import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2, GraduationCap, Eye, EyeOff, AlertCircle, Mail, Lock } from "lucide-react";

const container: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
};

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Start readOnly so the browser does NOT autofill saved credentials on load.
  // On first focus/click they become editable, and the browser shows its
  // saved-email / saved-password suggestions.
  const [emailActive, setEmailActive] = useState(false);
  const [passwordActive, setPasswordActive] = useState(false);
  const { login, isLoading } = useAuthStore();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please fill in your email and password.");
      return;
    }
    try {
      await login(email, password);
      const user = useAuthStore.getState().user;
      toast.success(`Welcome back, ${user?.name || ""}!`);
      router.push(`/${user?.role || "student"}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const message = detail || err?.message || "Login failed. Please try again.";
      setError(message);
      setEmail("");
      setPassword("");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-6">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="w-full max-w-md"
      >
        <Card className="border shadow-lg">
          <CardContent className="p-8">
            {/* Brand */}
            <motion.div variants={item} className="mb-8 flex flex-col items-center text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 ring-4 ring-indigo-500/20">
                <GraduationCap className="h-8 w-8" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight">Smart Exam Checker</h1>
              <p className="mt-1 text-sm text-muted-foreground">Sign in to your account</p>
            </motion.div>

            {/* Persistent error banner */}
            {error && (
              <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4" autoComplete="on">
              <motion.div variants={item} className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    name="email"
                    autoComplete="email"
                    readOnly={!emailActive}
                    onMouseDown={() => setEmailActive(true)}
                    onFocus={() => setEmailActive(true)}
                    placeholder="you@university.edu"
                    className="pl-10"
                    value={email}
                    onChange={(e) => { setEmail(e.target.value); setError(null); }}
                    required
                  />
                </div>
              </motion.div>

              <motion.div variants={item} className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    name="password"
                    autoComplete="current-password"
                    readOnly={!passwordActive}
                    onMouseDown={() => setPasswordActive(true)}
                    onFocus={() => setPasswordActive(true)}
                    placeholder="••••••••"
                    className="pl-10 pr-10"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setError(null); }}
                    required
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </motion.div>

              <motion.div variants={item}>
                <Button
                  type="submit"
                  className="w-full bg-indigo-600 text-white hover:bg-indigo-700"
                  disabled={isLoading}
                >
                  {isLoading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in...</> : "Sign In"}
                </Button>
              </motion.div>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
