"use client";

import { useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getInitials, getRoleColor, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import { Save, Loader2 } from "lucide-react";
import api from "@/lib/api";

export default function StudentProfilePage() {
  const { user, fetchUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");

  if (!user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      if (newPw) {
        if (newPw !== confirmPw) { toast.error("New passwords do not match"); setIsLoading(false); return; }
        if (!currentPw) { toast.error("Current password is required"); setIsLoading(false); return; }
        if (newPw.length < 6) { toast.error("Password must be at least 6 characters"); setIsLoading(false); return; }
        await api.put("/auth/change-password", { current_password: currentPw, new_password: newPw });
        setCurrentPw(""); setNewPw(""); setConfirmPw("");
        toast.success("Password changed successfully!");
      }
      if (name !== user.name || email !== user.email) {
        toast.info("Name/email updates require admin assistance");
      }
      await fetchUser();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || "Update failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">Manage your account settings</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardContent className="flex flex-col items-center p-6">
            <Avatar className="h-24 w-24">
              <AvatarFallback className="bg-blue-600 text-2xl text-white">
                {getInitials(user.name)}
              </AvatarFallback>
            </Avatar>
            <h2 className="mt-4 text-xl font-bold">{user.name}</h2>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            <Badge className={`mt-2 ${getRoleColor(user.role)}`}>{user.role}</Badge>
            <Separator className="my-4" />
            <div className="w-full space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Member since</span>
                <span>{formatDate(user.created_at)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Status</span>
                <Badge variant={user.is_active ? "default" : "destructive"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
            <CardDescription>Update your personal details</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name</Label>
                  <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
              </div>
              <Separator />
              <p className="text-sm font-medium text-muted-foreground">Change Password</p>
              <div className="space-y-2">
                <Label htmlFor="current-pw">Current Password</Label>
                <Input id="current-pw" type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} placeholder="Enter current password" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="new-pw">New Password</Label>
                  <Input id="new-pw" type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} placeholder="Enter new password" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm-pw">Confirm Password</Label>
                  <Input id="confirm-pw" type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} placeholder="Confirm new password" />
                </div>
              </div>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (<><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>) : (<><Save className="mr-2 h-4 w-4" /> Save Changes</>)}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
