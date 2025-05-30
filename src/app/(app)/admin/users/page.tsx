
"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PlusCircle } from "lucide-react";

export default function AdminUsersPage() {
  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><Users className="text-primary"/>Kullanıcı Yönetimi</CardTitle>
            <CardDescription>
              Öğrenci ve admin hesaplarını yönetin. Bu özellik yakında kullanıma sunulacaktır.
            </CardDescription>
          </div>
           <Button disabled>
            <PlusCircle className="mr-2 h-4 w-4" /> Yeni Kullanıcı Ekle
          </Button>
        </CardHeader>
        <CardContent className="text-center">
          <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
            <Users className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Kullanıcı listesi ve yönetim araçları burada yer alacaktır.</p>
          </div>
          <p className="text-muted-foreground">
            Bu özellik geliştirme aşamasındadır.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
