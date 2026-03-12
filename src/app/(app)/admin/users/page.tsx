
"use client";

import type { User } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users as UsersIcon, PlusCircle, Edit, Trash2, Search, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import React, { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import UserFormDialog from "@/components/admin/user-form-dialog";
import AddUserDialog from "@/components/admin/add-user-dialog";
import { useToast } from "@/hooks/use-toast";


export default function AdminUsersPage() {
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUserFormOpen, setIsUserFormOpen] = useState(false);
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  // Password reset dialog state
  const [passwordResetUser, setPasswordResetUser] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    setIsLoading(true);
    const loadUsers = async () => {
      try {
        const usersFromDb = await adminApi.users.getAll();
        // Convert snake_case to camelCase
        const convertedUsers = usersFromDb.map((u: any) => ({
          id: u.id,
          name: u.name,
          email: u.email,
          role: u.role,
          studentNumber: u.student_number,
          homeAddress: u.home_address,
          accessibilityNeeds: u.accessibility_needs,
          weeklyScheduleId: u.weekly_schedule_id,
        }));
        setAllUsers(convertedUsers);
      } catch (error) {
        console.error("Error loading users:", error);
        toast({
          title: "Yükleme Hatası",
          description: "Kullanıcılar yüklenirken bir hata oluştu.",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };
    loadUsers();
    // Removed toast from dependency array to prevent unnecessary re-runs
    // toast is guaranteed to be stable or we only want to load once on mount
  }, []);

  const handleOpenEditDialog = (user: User) => {
    setEditingUser(user);
    setIsUserFormOpen(true);
  };

  const handleCloseUserFormDialog = () => {
    setIsUserFormOpen(false);
    setEditingUser(null);
  };

  const handleSaveUser = async (updatedUserData: User) => {
    try {
      const { id, ...updates } = updatedUserData;
      await adminApi.users.update(id, updates);

      setAllUsers(prevUsers => prevUsers.map(u => u.id === id ? updatedUserData : u));
      toast({
        title: "Kullanıcı Güncellendi",
        description: `${updatedUserData.name} adlı kullanıcının bilgileri başarıyla güncellendi.`,
      });
      handleCloseUserFormDialog();
    } catch (error) {
      console.error("Error updating user:", error);
      toast({
        title: "Güncelleme Başarısız",
        description: "Kullanıcı güncellenirken bir hata oluştu.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteUser = async (userId: string, userName: string) => {
    if (!confirm(`${userName} adlı kullanıcıyı silmek istediğinize emin misiniz?`)) {
      return;
    }

    try {
      await adminApi.users.delete(userId);
      setAllUsers(prevUsers => prevUsers.filter(u => u.id !== userId));
      toast({
        title: "Kullanıcı Silindi",
        description: `${userName} adlı kullanıcı başarıyla silindi.`,
      });
    } catch (error) {
      console.error("Error deleting user:", error);
      toast({
        title: "Silme Başarısız",
        description: "Kullanıcı silinirken bir hata oluştu.",
        variant: "destructive",
      });
    }
  };

  const handleOpenPasswordReset = (user: User) => {
    setPasswordResetUser(user);
    setNewPassword("");
  };

  const handlePasswordReset = async () => {
    if (!passwordResetUser || newPassword.length < 6) {
      toast({ title: "Hata", description: "Şifre en az 6 karakter olmalıdır.", variant: "destructive" });
      return;
    }
    setIsResettingPassword(true);
    try {
      await adminApi.users.resetPassword(passwordResetUser.id, newPassword);
      toast({ title: "Başarılı", description: `${passwordResetUser.name} için şifre güncellendi.` });
      setPasswordResetUser(null);
    } catch (err: any) {
      toast({ title: "Hata", description: err.message, variant: "destructive" });
    } finally {
      setIsResettingPassword(false);
    }
  };

  const handleAddUser = async (userData: {
    email: string;
    password: string;
    name: string;
    role: string;
    studentNumber?: string;
  }) => {
    try {
      const newUser = await adminApi.users.create(userData);
      // Convert snake_case to camelCase
      const convertedUser = {
        id: newUser.id,
        name: newUser.name,
        email: newUser.email,
        role: newUser.role,
        studentNumber: newUser.student_number,
        homeAddress: newUser.home_address,
        accessibilityNeeds: newUser.accessibility_needs,
        weeklyScheduleId: newUser.weekly_schedule_id,
      };
      setAllUsers(prevUsers => [...prevUsers, convertedUser]);
      toast({
        title: "Kullanıcı Eklendi",
        description: `${userData.name} adlı kullanıcı başarıyla oluşturuldu.`,
      });
    } catch (error: any) {
      console.error("Error adding user:", error);
      toast({
        title: "Ekleme Başarısız",
        description: error.message || "Kullanıcı eklenirken bir hata oluştu.",
        variant: "destructive",
      });
      throw error; // Re-throw to let dialog know it failed
    }
  };
  const filteredUsers = allUsers.filter(user =>
    user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.studentNumber && user.studentNumber.toLowerCase().includes(searchTerm.toLowerCase())) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );


  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2"><UsersIcon className="text-primary" />Kullanıcı Yönetimi</CardTitle>
            <CardDescription>Kullanıcılar yükleniyor...</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Lütfen bekleyin...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><UsersIcon className="text-primary" />Kullanıcı Yönetimi</CardTitle>
            <CardDescription>
              Sistemde kayıtlı öğrenci ve admin hesaplarını görüntüleyin, düzenleyin ve filtreleyin.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row justify-between items-center mb-6 space-y-3 md:space-y-0 md:space-x-4">
            <div className="relative w-full md:flex-grow">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Ad, Öğrenci No veya E-posta ile Ara..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 w-full"
              />
            </div>
            <Button onClick={() => setIsAddUserOpen(true)} className="w-full md:w-auto">
              <PlusCircle className="mr-2 h-4 w-4" /> Yeni Kullanıcı Ekle
            </Button>
          </div>

          {allUsers.length === 0 ? (
            <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
              <UsersIcon className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Sistemde kayıtlı kullanıcı bulunmamaktadır.</p>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
              <Search className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Arama kriterlerinize uygun kullanıcı bulunamadı.</p>
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ad Soyad</TableHead>
                    <TableHead>Öğrenci No</TableHead>
                    <TableHead>E-posta</TableHead>
                    <TableHead>Rol</TableHead>
                    <TableHead className="text-right">İşlemler</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell>{user.studentNumber || "-"}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Badge
                          variant={user.role === "admin" ? "destructive" : user.role === "driver" ? "default" : "secondary"}
                          className={user.role === "driver" ? "bg-blue-600 hover:bg-blue-700" : ""}
                        >
                          {user.role === "admin" ? "Admin" : user.role === "driver" ? "Şoför" : "Öğrenci"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" onClick={() => handleOpenEditDialog(user)} className="mr-1" title="Düzenle">
                          <Edit className="h-4 w-4" />
                          <span className="sr-only">Düzenle</span>
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleOpenPasswordReset(user)} className="mr-1 text-amber-600 hover:text-amber-700" title="Şifre Değiştir">
                          <KeyRound className="h-4 w-4" />
                          <span className="sr-only">Şifre Değiştir</span>
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDeleteUser(user.id, user.name)} className="text-destructive hover:text-destructive" title="Sil">
                          <Trash2 className="h-4 w-4" />
                          <span className="sr-only">Sil</span>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <CardDescription className="mt-4 text-xs">
            Not: Şifreler güvenlik nedeniyle burada gösterilmemektedir.
          </CardDescription>
        </CardContent>
      </Card>
      <UserFormDialog
        isOpen={isUserFormOpen}
        onClose={handleCloseUserFormDialog}
        onSave={handleSaveUser}
        user={editingUser}
      />
      <AddUserDialog
        isOpen={isAddUserOpen}
        onClose={() => setIsAddUserOpen(false)}
        onSave={handleAddUser}
      />

      {/* Password Reset Dialog */}
      <Dialog open={!!passwordResetUser} onOpenChange={(open) => !open && setPasswordResetUser(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-amber-500" /> Şifre Değiştir</DialogTitle>
            <DialogDescription>
              <strong>{passwordResetUser?.name}</strong> ({passwordResetUser?.email}) için yeni bir şifre belirleyin.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-2">
            <Label htmlFor="new-password">Yeni Şifre (min. 6 karakter)</Label>
            <Input
              id="new-password"
              type="password"
              placeholder="Yeni şifreyi girin..."
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handlePasswordReset()}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasswordResetUser(null)}>İptal</Button>
            <Button onClick={handlePasswordReset} disabled={isResettingPassword} className="bg-amber-600 hover:bg-amber-700">
              {isResettingPassword ? "Güncelleniyor..." : "Şifreyi Güncelle"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
