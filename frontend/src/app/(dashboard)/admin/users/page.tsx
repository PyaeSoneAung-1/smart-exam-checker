"use client";

import { useEffect, useRef, useState } from "react";
import { usersApi, asApiError } from "@/lib/api";
import type { User } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Search, Plus, Trash2, UserCheck, UserX, Users, Upload, FileUp, X } from "lucide-react";
import { toast } from "sonner";

interface CsvUser {
  name: string;
  email: string;
  password: string;
  role: string;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [csvDialogOpen, setCsvDialogOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "student" as string });
  const [csvUsers, setCsvUsers] = useState<CsvUser[]>([]);
  const [csvFileName, setCsvFileName] = useState("");
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await usersApi.getAll({ limit: 500 });
      setUsers(res.data.items || []);
    } catch (err) {
      console.error(err);
      toast.error("Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleAdd = async () => {
    if (!form.name || !form.email || !form.password) {
      toast.error("All fields required");
      return;
    }
    try {
      await usersApi.create({
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role,
      });
      toast.success(`User ${form.name} created`);
      setForm({ name: "", email: "", password: "", role: "student" });
      setDialogOpen(false);
      fetchUsers();
    } catch (err) {
      const msg = asApiError(err)?.response?.data?.detail; toast.error(typeof msg === "string" ? msg : "Failed to create user");
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      if (user.is_active) {
        await usersApi.delete(user.id);
        toast.success(`${user.name} deactivated`);
      } else {
        await usersApi.activate(user.id);
        toast.success(`${user.name} activated`);
      }
      fetchUsers();
    } catch {
      toast.error("Failed to update user");
    }
  };

  const handleDelete = async (user: User) => {
    if (!confirm(`Delete ${user.name}?`)) return;
    try {
      await usersApi.delete(user.id);
      toast.success(`${user.name} deleted`);
      fetchUsers();
    } catch {
      toast.error("Failed to delete user");
    }
  };

  const parseCsv = (text: string): CsvUser[] => {
    const lines = text.trim().split("\n");
    if (lines.length < 2) return [];

    const header = lines[0].toLowerCase().split(",").map(h => h.trim());
    const nameIdx = header.findIndex(h => h === "name");
    const emailIdx = header.findIndex(h => h === "email");
    const passwordIdx = header.findIndex(h => h === "password");
    const roleIdx = header.findIndex(h => h === "role");

    if (nameIdx === -1 || emailIdx === -1 || passwordIdx === -1) {
      toast.error("CSV must have columns: name, email, password, role");
      return [];
    }

    const users: CsvUser[] = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(",").map(c => c.trim());
      if (cols.length < 3) continue;
      const name = cols[nameIdx];
      const email = cols[emailIdx];
      const password = cols[passwordIdx];
      const role = roleIdx >= 0 ? cols[roleIdx] : "student";
      if (name && email && password) {
        users.push({ name, email, password, role: role || "student" });
      }
    }
    return users;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const parsed = parseCsv(text);
      if (parsed.length === 0) {
        toast.error("No valid users found in CSV");
        return;
      }
      setCsvUsers(parsed);
      toast.success(`Found ${parsed.length} users in CSV`);
    };
    reader.readAsText(file);
  };

  const handleBulkImport = async () => {
    if (csvUsers.length === 0) return;
    setImporting(true);
    let successCount = 0;
    let errorCount = 0;

    for (const user of csvUsers) {
      try {
        await usersApi.create({
          name: user.name,
          email: user.email,
          password: user.password,
          role: user.role || "student",
        });
        successCount++;
      } catch {
        errorCount++;
      }
    }

    setImporting(false);
    setCsvUsers([]);
    setCsvFileName("");
    if (fileInputRef.current) fileInputRef.current.value = "";

    if (successCount > 0) {
      toast.success(`Imported ${successCount} users${errorCount > 0 ? `, ${errorCount} failed` : ""}`);
      fetchUsers();
    } else {
      toast.error("Failed to import any users");
    }
    setCsvDialogOpen(false);
  };

  const removeCsvUser = (idx: number) => {
    setCsvUsers(csvUsers.filter((_, i) => i !== idx));
  };

  const filtered = users.filter((u) => {
    const matchSearch = u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter === "all" || u.role === roleFilter;
    return matchSearch && matchRole;
  });

  const getRoleBadge = (role: string) => {
    const colors: Record<string, string> = {
      student: "bg-blue-100 text-blue-700",
      teacher: "bg-green-100 text-green-700",
      admin: "bg-purple-100 text-purple-700",
    };
    return colors[role] || "";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Users className="h-8 w-8" /> Users Management
        </h1>
        <div className="flex gap-2">
          {/* CSV Import Button */}
          <Dialog open={csvDialogOpen} onOpenChange={setCsvDialogOpen}>
            <DialogTrigger
              render={
                <Button variant="outline">
                  <Upload className="h-4 w-4 mr-2" /> Import CSV
                </Button>
              }
            />
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Bulk Import Users</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Upload a CSV file with columns: <code className="bg-muted px-1 rounded">name</code>,{" "}
                  <code className="bg-muted px-1 rounded">email</code>,{" "}
                  <code className="bg-muted px-1 rounded">password</code>,{" "}
                  <code className="bg-muted px-1 rounded">role</code> (optional, defaults to student)
                </p>
                <div className="flex items-center gap-3">
                  <Input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="flex-1"
                  />
                </div>
                {csvFileName && (
                  <p className="text-sm text-muted-foreground">
                    <FileUp className="inline h-4 w-4 mr-1" />
                    {csvFileName} — {csvUsers.length} users found
                  </p>
                )}
                {csvUsers.length > 0 && (
                  <>
                    <div className="text-sm font-medium">Preview ({csvUsers.length} users):</div>
                    <div className="max-h-60 overflow-y-auto border rounded-md">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Email</TableHead>
                            <TableHead>Role</TableHead>
                            <TableHead className="w-10"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {csvUsers.map((u, idx) => (
                            <TableRow key={idx}>
                              <TableCell>{u.name}</TableCell>
                              <TableCell>{u.email}</TableCell>
                              <TableCell>
                                <Badge className={getRoleBadge(u.role)}>{u.role}</Badge>
                              </TableCell>
                              <TableCell>
                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeCsvUser(idx)}>
                                  <X className="h-3 w-3" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    <Button onClick={handleBulkImport} disabled={importing} className="w-full">
                      {importing ? "Importing..." : `Import ${csvUsers.length} Users`}
                    </Button>
                  </>
                )}
              </div>
            </DialogContent>
          </Dialog>

          {/* Single Add Button */}
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger
              render={
                <Button><Plus className="h-4 w-4 mr-2" /> Add User</Button>
              }
            />
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New User</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>Name</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="John Doe" />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="john@example.com" />
                </div>
                <div>
                  <Label>Password</Label>
                  <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="••••••" />
                </div>
                <div>
                  <Label>Role</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v ?? "student" })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="student">Student</SelectItem>
                      <SelectItem value="teacher">Teacher</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleAdd} className="w-full">Create User</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search users..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <Select value={roleFilter} onValueChange={(v) => setRoleFilter(v ?? "all")}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Role" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Roles</SelectItem>
            <SelectItem value="student">Students</SelectItem>
            <SelectItem value="teacher">Teachers</SelectItem>
            <SelectItem value="admin">Admins</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="pt-6 text-center"><p className="text-2xl font-bold">{users.length}</p><p className="text-sm text-muted-foreground">Total Users</p></CardContent></Card>
        <Card><CardContent className="pt-6 text-center"><p className="text-2xl font-bold text-blue-600">{users.filter(u => u.role === "student").length}</p><p className="text-sm text-muted-foreground">Students</p></CardContent></Card>
        <Card><CardContent className="pt-6 text-center"><p className="text-2xl font-bold text-green-600">{users.filter(u => u.role === "teacher").length}</p><p className="text-sm text-muted-foreground">Teachers</p></CardContent></Card>
        <Card><CardContent className="pt-6 text-center"><p className="text-2xl font-bold text-purple-600">{users.filter(u => u.role === "admin").length}</p><p className="text-sm text-muted-foreground">Admins</p></CardContent></Card>
      </div>

      {/* Table */}
      <Card>
        <CardHeader><CardTitle>All Users ({filtered.length})</CardTitle></CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-center py-8 text-muted-foreground">Loading...</p>
          ) : filtered.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No users found</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.name}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell><Badge className={getRoleBadge(u.role)}>{u.role}</Badge></TableCell>
                    <TableCell>
                      {u.is_active ? (
                        <Badge className="bg-green-100 text-green-700">Active</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">{new Date(u.created_at).toLocaleDateString()}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleToggleActive(u)}>
                          {u.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(u)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
