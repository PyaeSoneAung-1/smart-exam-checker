import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

export function formatDateTime(date: string | Date): string {
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatTime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function getRoleColor(role: string): string {
  switch (role) {
    case 'student': return 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-950';
    case 'teacher': return 'text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950';
    case 'admin': return 'text-purple-600 bg-purple-50 dark:text-purple-400 dark:bg-purple-950';
    default: return 'text-gray-600 bg-gray-50';
  }
}

export function getRoleBadgeVariant(role: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (role) {
    case 'student': return 'default';
    case 'teacher': return 'secondary';
    case 'admin': return 'destructive';
    default: return 'outline';
  }
}

export function getScoreColor(score: number, max: number): string {
  const pct = (score / max) * 100;
  if (pct >= 80) return 'text-emerald-600 dark:text-emerald-400';
  if (pct >= 60) return 'text-blue-600 dark:text-blue-400';
  if (pct >= 40) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

export function getScoreBg(score: number, max: number): string {
  const pct = (score / max) * 100;
  if (pct >= 80) return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300';
  if (pct >= 60) return 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300';
  if (pct >= 40) return 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300';
  return 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300';
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}
