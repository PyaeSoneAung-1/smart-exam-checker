"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { getInitials, getRoleColor } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  GraduationCap, Moon, Sun, LogOut, User, Settings, Menu,
  ChevronRight, X, Home,
} from "lucide-react";
import { useTheme } from "next-themes";

interface NavbarProps {
  onToggleSidebar?: () => void;
}

function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length <= 1) return null;

  const crumbs = segments.map((seg, idx) => ({
    label: seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, " ").replace(/\[.*?\]/g, "…"),
    href: "/" + segments.slice(0, idx + 1).join("/"),
    isLast: idx === segments.length - 1,
  }));

  return (
    <nav className="hidden md:flex items-center gap-1 text-sm text-muted-foreground">
      <Link href={`/${segments[0]}`} className="hover:text-foreground transition-colors">
        <Home className="h-3.5 w-3.5" />
      </Link>
      {crumbs.map((crumb) => (
        <span key={crumb.href} className="flex items-center gap-1">
          <ChevronRight className="h-3.5 w-3.5" />
          {crumb.isLast ? (
            <span className="text-foreground font-medium">{crumb.label}</span>
          ) : (
            <Link href={crumb.href} className="hover:text-foreground transition-colors">
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}

function MobileMenu({
  isOpen,
  onClose,
  user,
  onLogout,
}: {
  isOpen: boolean;
  onClose: () => void;
  user: any;
  onLogout: () => void;
}) {
  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-[60] bg-black/50" onClick={onClose} />
      <div className="fixed right-0 top-0 z-[70] h-full w-72 bg-card border-l shadow-xl">
        <div className="flex items-center justify-between p-4 border-b">
          <span className="font-semibold">Menu</span>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <ScrollArea className="h-[calc(100%-64px)]">
          <div className="p-4 space-y-4">
            {user && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                <Avatar className="h-10 w-10">
                  <AvatarFallback className="bg-indigo-500 text-white">
                    {getInitials(user.name)}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-medium text-sm">{user.name}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                </div>
              </div>
            )}
            <div className="space-y-1">
              {user && (
                <>
                  {user.role === "student" && (
                    <Button variant="ghost" className="w-full justify-start" onClick={() => { onClose(); }}>
                      <User className="mr-3 h-4 w-4" />
                      Profile
                    </Button>
                  )}
                  {user.role === "admin" && (
                    <Button variant="ghost" className="w-full justify-start" onClick={() => { onClose(); }}>
                      <Settings className="mr-3 h-4 w-4" />
                      Settings
                    </Button>
                  )}
                </>
              )}
            </div>
            <div className="border-t pt-4">
              {user ? (
                <Button variant="ghost" className="w-full justify-start text-red-600" onClick={() => { onLogout(); onClose(); }}>
                  <LogOut className="mr-3 h-4 w-4" />
                  Log out
                </Button>
              ) : (
                <div className="space-y-2">
                  <Link href="/login" onClick={onClose}>
                    <Button variant="outline" className="w-full">Log in</Button>
                  </Link>
                  <Link href="/register" onClick={onClose}>
                    <Button className="w-full">Get Started</Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </ScrollArea>
      </div>
    </>
  );
}

export default function Navbar({ onToggleSidebar }: NavbarProps) {
  const { user, logout, isAuthenticated } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const dashboardPath = user ? `/${user.role}` : "/login";

  return (
    <>
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex h-16 items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-3">
            {isAuthenticated && (
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={onToggleSidebar}
              >
                <Menu className="h-5 w-5" />
              </Button>
            )}
            <Link href={isAuthenticated ? dashboardPath : "/"} className="flex items-center gap-2.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 ring-2 ring-indigo-500/40">
                <GraduationCap className="h-6 w-6" />
              </div>
              <span className="hidden text-lg font-bold tracking-tight sm:inline-block">
                SmartExam
              </span>
            </Link>
            {isAuthenticated && <Breadcrumbs />}
          </div>

          <div className="flex items-center gap-2">
            {isAuthenticated && user && (
              <Badge variant="outline" className={`hidden sm:flex ${getRoleColor(user.role)}`}>
                {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
              </Badge>
            )}

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="relative overflow-hidden"
              aria-label="Toggle theme"
            >
              <Sun className="h-5 w-5 rotate-0 scale-100 transition-all duration-500 ease-out dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all duration-500 ease-out dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>

            {isAuthenticated && user ? (
              <>
                {/* Desktop user menu */}
                <DropdownMenu>
                  <DropdownMenuTrigger className="hidden md:flex items-center justify-center h-9 w-9 rounded-full hover:bg-muted cursor-pointer">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="bg-indigo-500 text-white text-sm">
                        {getInitials(user.name)}
                      </AvatarFallback>
                    </Avatar>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <div className="flex items-center gap-2 p-2">
                      <div className="flex flex-col space-y-0.5">
                        <p className="text-sm font-medium">{user.name}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                    </div>
                    <DropdownMenuSeparator />
                    {user.role === "student" && (
                      <DropdownMenuItem onClick={() => router.push(`/${user.role}/profile`)}>
                        <User className="mr-2 h-4 w-4" />
                        Profile
                      </DropdownMenuItem>
                    )}
                    {user.role === "admin" && (
                      <DropdownMenuItem onClick={() => router.push(`/${user.role}/settings`)}>
                        <Settings className="mr-2 h-4 w-4" />
                        Settings
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                      <LogOut className="mr-2 h-4 w-4" />
                      Log out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* Mobile avatar (opens mobile menu) */}
                <Button
                  variant="ghost"
                  className="relative h-9 w-9 rounded-full md:hidden"
                  onClick={() => setMobileMenuOpen(true)}
                >
                  <Avatar className="h-9 w-9">
                    <AvatarFallback className="bg-indigo-500 text-white text-sm">
                      {getInitials(user.name)}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="hidden sm:inline-flex" onClick={() => router.push("/login")}>
                  Log in
                </Button>
                <Button size="sm" className="hidden sm:inline-flex" onClick={() => router.push("/register")}>
                  Get Started
                </Button>
                <Button variant="ghost" size="icon" className="sm:hidden" onClick={() => setMobileMenuOpen(true)}>
                  <Menu className="h-5 w-5" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      <MobileMenu
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        user={user}
        onLogout={handleLogout}
      />
    </>
  );
}
