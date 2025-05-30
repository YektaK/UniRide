
"use client";

import type { User } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users as UsersIcon, PlusCircle, Edit, Trash2 } from "lucide-react";
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
import React, { useEffect, useState } from "react";
import { getUsers as dbGetUsers, updateUser as dbUpdateUser, createNewUserSchedule } from "@/lib/mock-database";
import UserFormDialog from "@/components/admin/user-form-dialog"; // Import the dialog
import { useToast } from "@/hooks/use-toast";


export default function AdminUsersPage() {
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUserFormOpen, setIsUserFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    setIsLoading(true);
    const usersFromDb = dbGetUsers();
    setAllUsers(usersFromDb);
    setIsLoading(false);
  }, []);

  const handleOpenEditDialog = (user: User) => {
    setEditingUser(user);
    setIsUserFormOpen(true);
  };

  const handleCloseUserFormDialog = () => {
    setIsUserFormOpen(false);
    setEditingUser(null);
  };

  const handleSaveUser = (updatedUserData: User) => {
    let userToUpdate = { ...updatedUserData };

    // Handle role change logic
    const originalUser = allUsers.find(u => u.id === updatedUserData.id);
    if (originalUser && originalUser.role === 'admin' && userToUpdate.role === 'student') {
      // Admin to Student: ensure studentNumber, create weeklyScheduleId if missing
      if (!userToUpdate.studentNumber) {
        // You might want to make studentNumber mandatory in the form if role is student
        // For now, let's assign a placeholder or leave it for the form validation to catch
        toast({title: "Hata", description: "Öğrenci rolü için öğrenci numarası zorunludur.", variant: "destructive"});
        return; // Or handle this more gracefully in the form
      }
      if (!userToUpdate.weeklyScheduleId) {
        userToUpdate.weeklyScheduleId = `schedule${Date.now()}${Math.random().toString(36).substring(2, 7)}`;
        createNewUserSchedule(userToUpdate.id, userToUpdate.weeklyScheduleId);
      }
    } else if (originalUser && originalUser.role === 'student' && userToUpdate.role === 'admin') {
      // Student to Admin: clear student-specific fields
      userToUpdate.studentNumber = undefined;
      userToUpdate.homeAddress = undefined;
      userToUpdate.accessibilityNeeds = [];
      // weeklyScheduleId can remain, or be cleared. Let's keep it.
    }


    if (dbUpdateUser(userToUpdate)) {
      setAllUsers(prevUsers => prevUsers.map(u => u.id === userToUpdate.id ? userToUpdate : u));
      toast({
        title: "Kullanıcı Güncellendi",
        description: `${userToUpdate.name} adlı kullanıcının bilgileri başarıyla güncellendi.`,
      });
    } else {
      toast({
        title: "Güncelleme Başarısız",
        description: "Kullanıcı güncellenirken bir hata oluştu.",
        variant: "destructive",
      });
    }
    handleCloseUserFormDialog();
  };


  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2"><UsersIcon className="text-primary"/>Kullanıcı Yönetimi</CardTitle>
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
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><UsersIcon className="text-primary"/>Kullanıcı Yönetimi</CardTitle>
            <CardDescription>
              Sistemde kayıtlı öğrenci ve admin hesaplarını görüntüleyin ve düzenleyin.
            </CardDescription>
          </div>
           <Button disabled> {/* TODO: Implement Add User functionality */}
            <PlusCircle className="mr-2 h-4 w-4" /> Yeni Kullanıcı Ekle
          </Button>
        </CardHeader>
        <CardContent>
          {allUsers.length === 0 ? (
            <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
              <UsersIcon className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Sistemde kayıtlı kullanıcı bulunmamaktadır.</p>
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
                  {allUsers.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell>{user.studentNumber || "-"}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Badge variant={user.role === "admin" ? "destructive" : "secondary"}>
                          {user.role === "admin" ? "Admin" : "Öğrenci"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" onClick={() => handleOpenEditDialog(user)} className="mr-2">
                          <Edit className="h-4 w-4" />
                          <span className="sr-only">Düzenle</span>
                        </Button>
                        <Button variant="ghost" size="icon" disabled> {/* TODO: Implement Delete User */}
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
    </div>
  );
}
