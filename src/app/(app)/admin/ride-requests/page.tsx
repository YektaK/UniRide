
"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ShieldAlert } from "lucide-react";

export default function AdminRideRequestsPage() {
  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><ShieldAlert className="text-primary"/>Servis Talepleri Yönetimi</CardTitle>
          <CardDescription>
            Öğrencilerden gelen anlık ve programlı servis taleplerini onaylayın veya reddedin. Bu özellik yakında kullanıma sunulacaktır.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
            <ShieldAlert className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Servis talepleri listesi ve yönetim araçları burada yer alacaktır.</p>
          </div>
          <p className="text-muted-foreground">
            Bu özellik geliştirme aşamasındadır.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
