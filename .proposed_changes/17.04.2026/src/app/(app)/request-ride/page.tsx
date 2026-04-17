
"use client";

import AdhocRideForm from "@/components/student/adhoc-ride-form";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ClipboardList } from "lucide-react";

export default function RequestRidePage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <Card><CardHeader><CardTitle>Yükleniyor...</CardTitle></CardHeader><CardContent><p>Servis talep formu yükleniyor.</p></CardContent></Card>;
  }

  if (!user || user.role !== "student") {
     return <Card><CardHeader><CardTitle>Erişim Reddedildi</CardTitle></CardHeader><CardContent><p>Bu sayfayı görüntüleme yetkiniz yok.</p></CardContent></Card>;
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><ClipboardList className="text-primary"/>Anlık Servis Talebi</CardTitle>
          <CardDescription>
            Haftalık programınız dışında bir günde veya saatte servise ihtiyacınız varsa buradan talep oluşturabilirsiniz.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AdhocRideForm userId={user.id} defaultPickupAddress={user.homeAddress} />
        </CardContent>
      </Card>
    </div>
  );
}
