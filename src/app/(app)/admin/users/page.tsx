
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
import { getUsers } from "@/lib/mock-database"; // Import from mock DB

export default function AdminUsersPage() {
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    const usersFromDb = getUsers();
    setAllUsers(usersFromDb);
    setIsLoading(false);
  }, []);

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
              Sistemde kayıtlı öğrenci ve admin hesaplarını görüntüleyin.
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
                        <Button variant="ghost" size="icon" disabled className="mr-2"> {/* TODO: Implement Edit User */}
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
            Not: Şifreler güvenlik nedeniyle burada gösterilmemektedir. Öğrenci girişleri için şifreler:
            Ayşe (student@uniride.com) - Şifre: studentpassword,
            Veli (veli@uniride.com) - Şifre: velipassword,
            Zeynep (zeynep@uniride.com) - Şifre: zeyneppassword.
            Yeni eklenen kullanıcıların şifreleri kayıt sırasında belirlenir.
          </CardDescription>
        </CardContent>
      </Card>
    </div>
  );
}
