"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import DashboardLayout from "@/components/layout/DashboardLayout";

export default function DashLayout({ children }: { children: React.ReactNode }) {
  const { user, fetchUser, token, _hydrated } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!_hydrated) return;
    if (!token) {
      router.push("/login");
      return;
    }
    // If user is already in store, we're ready immediately
    if (user) {
      setReady(true);
      return;
    }
    // Fetch user but don't block rendering on failure
    fetchUser().finally(() => setReady(true));
  }, [_hydrated, token]); // Only run on hydration/token change

  // Role guard — only redirect when we have a confirmed user
  useEffect(() => {
    if (!ready || !user) return;
    const role = pathname.split("/")[1];
    if (role && role !== user.role && ["student", "teacher", "admin"].includes(role)) {
      router.push(`/${user.role}`);
    }
  }, [ready, user, pathname, router]);

  // Not hydrated yet
  if (!_hydrated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  // No token
  if (!token) return null;

  // Still loading user — show layout with sidebar (user from localStorage)
  return <DashboardLayout>{children}</DashboardLayout>;
}
