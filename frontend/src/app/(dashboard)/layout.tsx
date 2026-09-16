"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import DashboardLayout from "@/components/layout/DashboardLayout";

export default function DashLayout({ children }: { children: React.ReactNode }) {
  const { user, fetchUser, token, _hydrated } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  // Derived, not state: we are "ready" as soon as a user object is available.
  const ready = Boolean(user);

  useEffect(() => {
    if (!_hydrated) return;
    if (!token) {
      router.push("/login");
      return;
    }
    // Fetch the profile if it is not in the store yet; rendering is not blocked
    // on failure.
    if (!user) void fetchUser();
  }, [_hydrated, token, user, router, fetchUser]); // Only run on hydration/token/user change

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
