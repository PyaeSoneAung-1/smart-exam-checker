"use client";

import { GraduationCap } from "lucide-react";
import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Left decorative panel */}
      <div className="hidden w-1/2 bg-cyan-600 lg:flex lg:flex-col lg:items-center lg:justify-center lg:p-12">
        <div className="max-w-md text-center text-white">
          <div className="mx-auto mb-8 flex h-20 w-20 items-center justify-center rounded-2xl bg-white/20 ring-2 ring-white/30 backdrop-blur-sm">
            <GraduationCap className="h-10 w-10" />
          </div>
          <h1 className="mb-4 text-4xl font-bold">SmartExam</h1>
          <p className="text-lg text-white/80">
            AI-powered answer checking system that provides instant, accurate grading
            with keyword matching and intelligent feedback.
          </p>
          <div className="mt-12 grid grid-cols-3 gap-6">
            {[
              { label: "Instant", desc: "Grading" },
              { label: "Smart", desc: "Feedback" },
              { label: "Multi", desc: "Role Support" },
            ].map((f) => (
              <div key={f.label} className="rounded-xl bg-white/10 p-4 backdrop-blur-sm">
                <p className="text-xl font-bold">{f.label}</p>
                <p className="text-sm text-white/70">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex w-full flex-col items-center justify-center p-6 lg:w-1/2 lg:p-12">
        <div className="w-full max-w-md">
          <Link href="/" className="mb-8 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            ← Back to home
          </Link>
          {children}
        </div>
      </div>
    </div>
  );
}
