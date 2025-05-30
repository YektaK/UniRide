
"use client";

import type { User } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users as UsersIcon, PlusCircle, Edit, Trash2, Search } from "lucide-react"; // Added Search
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
import { Input } from "@/components/ui/input"; // Added Input
import React, { useEffect, useState } from "react";
import { getUsers as dbGetUsers, updateUser as dbUpdateUser } from "@/lib/mock-database";
import UserFormDialog from "@/components/admin/user-form-dialog"; 
import { useToast } from "@/hooks/use-toast";


export default function AdminUsersPage() {
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUserFormOpen, setIsUserFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [searchTerm, setSearchTerm] = useState(""); // State for the search term
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
    const userToSave = { ...updatedUserData };

    if (dbUpdateUser(userToSave)) {
      setAllUsers(prevUsers => prevUsers.map(u => u.id === userToSave.id ? userToSave : u));
      toast({
        title: "Kullanıcı Güncellendi",
        description: `${userToSave.name} adlı kullanıcının bilgileri başarıyla güncellendi.`,
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

  // Filter users based on search term
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
        <CardHeader className="md:flex md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><UsersIcon className="text-primary"/>Kullanıcı Yönetimi</CardTitle>
            <CardDescription>
              Sistemde kayıtlı öğrenci ve admin hesaplarını görüntüleyin, düzenleyin ve filtreleyin.
            </CardDescription>
          </div>
           <Button disabled className="mt-4 md:mt-0"> {/* TODO: Implement Add User functionality */}
            <PlusCircle className="mr-2 h-4 w-4" /> Yeni Kullanıcı Ekle
          </Button>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Ad, Öğrenci No veya E-posta ile Ara..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 w-full md:w-1/2 lg:w-1/3"
              />
            </div>
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
