
"use client";

import type { User } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users as UsersIcon, PlusCircle, Edit, Trash2 } from "lucide-react"; // Renamed Users to UsersIcon
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

// Mock users - these should ideally come from a service or context in a real app
// Replicating the users from auth-context for display purposes here.
const mockUsers: User[] = [
  {
    id: "admin001",
    name: "Admin Kullanıcısı",
    email: "admin@uniride.com",
    role: "admin",
    homeAddress: "Üniversite Yönetim Binası",
  },
  {
    id: "student001",
    name: "Öğrenci Ayşe",
    email: "student@uniride.com",
    role: "student",
    studentNumber: "202003002001",
    homeAddress: "123 Lale Sokak, Çankaya, Ankara",
    accessibilityNeeds: ["wheelchair"],
    weeklyScheduleId: "schedule001",
  },
  {
    id: "student002",
    name: "Öğrenci Veli",
    email: "veli@uniride.com",
    role: "student",
    studentNumber: "202003002002",
    homeAddress: "456 Menekşe Caddesi, Yenimahalle, Ankara",
    accessibilityNeeds: [],
    weeklyScheduleId: "schedule002",
  },
  {
    id: "student003",
    name: "Öğrenci Zeynep",
    email: "zeynep@uniride.com",
    role: "student",
    studentNumber: "202003002003",
    homeAddress: "789 Gül Apartmanı, Keçiören, Ankara",
    accessibilityNeeds: ["visual_impairment"],
    weeklyScheduleId: "schedule003",
  },
];

// Passwords are intentionally not displayed here.
// For student login, use the passwords defined in auth-context.tsx:
// Öğrenci Ayşe (student@uniride.com): studentpassword
// Öğrenci Veli (veli@uniride.com): velipassword
// Öğrenci Zeynep (zeynep@uniride.com): zeyneppassword

export default function AdminUsersPage() {
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
           <Button disabled>
            <PlusCircle className="mr-2 h-4 w-4" /> Yeni Kullanıcı Ekle
          </Button>
        </CardHeader>
        <CardContent>
          {mockUsers.length === 0 ? (
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
                  {mockUsers.map((user) => (
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
                        <Button variant="ghost" size="icon" disabled className="mr-2">
                          <Edit className="h-4 w-4" />
                          <span className="sr-only">Düzenle</span>
                        </Button>
                        <Button variant="ghost" size="icon" disabled>
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
            Not: Şifreler güvenlik nedeniyle burada gösterilmemektedir. Öğrenci girişleri için:
            Ayşe (student@uniride.com) - Şifre: studentpassword,
            Veli (veli@uniride.com) - Şifre: velipassword,
            Zeynep (zeynep@uniride.com) - Şifre: zeyneppassword.
          </CardDescription>
        </CardContent>
      </Card>
    </div>
  );
}
