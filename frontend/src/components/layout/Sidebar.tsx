"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  LayoutDashboard, FileText, BarChart3, Users, Settings,
  ClipboardList, GraduationCap, UserCircle, X, Trophy, Brain, Scale, Bot,
} from "lucide-react";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  title: string;
  href: string;
  icon: React.ElementType;
}

const studentNav: NavItem[] = [
  { title: "Dashboard", href: "/student", icon: LayoutDashboard },
  { title: "Exams", href: "/student/exams", icon: FileText },
  { title: "Results", href: "/student/results", icon: BarChart3 },
  { title: "Profile", href: "/student/profile", icon: UserCircle },
];

const teacherNav: NavItem[] = [
  { title: "Dashboard", href: "/teacher", icon: LayoutDashboard },
  { title: "Subjects", href: "/teacher/subjects", icon: FileText },
  { title: "Exams", href: "/teacher/exams", icon: FileText },
  { title: "Marks", href: "/teacher/marks", icon: ClipboardList },
  { title: "Students", href: "/teacher/students", icon: Users },
  { title: "Plagiarism Check", href: "/teacher/plagiarism", icon: Scale },
  { title: "AI Detection", href: "/teacher/ai-detection", icon: Bot },
];

const adminNav: NavItem[] = [
  { title: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { title: "Users", href: "/admin/users", icon: Users },
  { title: "Subjects", href: "/admin/subjects", icon: FileText },
  { title: "Exams", href: "/admin/exams", icon: FileText },
  { title: "NLP Engine", href: "/admin/nlp", icon: Brain },
  { title: "Settings", href: "/admin/settings", icon: Settings },
];

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { user } = useAuthStore();
  const pathname = usePathname();

  if (!user) return null;

  const navItems = user.role === "admin" ? adminNav : user.role === "teacher" ? teacherNav : studentNav;

  const roleColor =
    user.role === "student"
      ? "bg-blue-600"
      : user.role === "teacher"
        ? "bg-emerald-600"
        : "bg-violet-600";

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={onClose} />
      )}

      <aside
        className={cn(
          "fixed left-0 top-0 z-50 flex h-full w-64 flex-col border-r bg-card transition-transform duration-300 md:static md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className={`flex h-16 items-center gap-3 ${roleColor} px-4 text-white`}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/20 ring-1 ring-white/30">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">{user.name}</p>
            <p className="text-xs opacity-80">{user.role.charAt(0).toUpperCase() + user.role.slice(1)}</p>
          </div>
          <Button variant="ghost" size="icon" className="text-white md:hidden hover:bg-white/20" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <ScrollArea className="flex-1 py-4">
          <nav className="space-y-1 px-3">
            {navItems.map((item) => {
              const isActive = pathname === item.href || (item.href !== `/${user.role}` && pathname.startsWith(item.href));
              return (
                <Link key={item.href} href={item.href} onClick={onClose}>
                  <Button
                    variant={isActive ? "secondary" : "ghost"}
                    className={cn(
                      "w-full justify-start gap-3 h-10",
                      isActive && "bg-primary/10 text-primary font-medium"
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.title}
                  </Button>
                </Link>
              );
            })}
          </nav>
        </ScrollArea>

        <div className="border-t p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Trophy className="h-3 w-3" />
            <span>SmartExam v1.0</span>
          </div>
        </div>
      </aside>
    </>
  );
}
