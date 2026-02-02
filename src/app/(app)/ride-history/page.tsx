
"use client";

import type { RideRequest, RideStatus } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ListChecks, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import React, { useEffect, useState } from "react"; // useState eklendi
import { cn } from "@/lib/utils";
import { getRideRequests as dbGetRideRequests } from "@/lib/database";

const statusDisplayMap: Record<RideStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }> = {
  pending_student_confirmation: { label: "Öğrenci Onayı Bekliyor", variant: "outline", className: "border-yellow-500 text-yellow-700" },
  confirmed: { label: "Onaylandı", variant: "default", className: "bg-green-600 hover:bg-green-700 text-white" },
  cancelled_by_student: { label: "İptal Ettiniz", variant: "destructive" },
  cancelled_by_admin: { label: "Admin İptal Etti", variant: "destructive", className: "bg-red-700 text-white" },
  in_progress: { label: "Yolda", variant: "default", className: "bg-blue-500 hover:bg-blue-600 text-white" },
  completed: { label: "Tamamlandı", variant: "secondary", className: "bg-gray-500 text-white" },
  pending_admin_approval: { label: "Admin Onayı Bekliyor", variant: "outline", className: "border-orange-500 text-orange-700" },
};


export default function RideHistoryPage() {
  const { user, isLoading } = useAuth();
  const [userRequests, setUserRequests] = useState<RideRequest[]>([]); // useState kullanıldı
  const [isDataLoading, setIsDataLoading] = useState(true); // Yeni state eklendi

  useEffect(() => {
    if (user && !isLoading) {
      setIsDataLoading(true);
      const loadRequests = async () => {
        try {
          const allRequests = await dbGetRideRequests({ userId: user.id });
          setUserRequests(allRequests);
        } catch (error) {
          console.error("Error loading ride requests:", error);
          setUserRequests([]);
        } finally {
          setIsDataLoading(false);
        }
      };
      loadRequests();
    } else if (!user && !isLoading) {
      setIsDataLoading(false);
    }
  }, [user, isLoading]);

  if (isLoading || isDataLoading) { // Her iki yükleme durumu da kontrol ediliyor
    return <Card><CardHeader><CardTitle>Yükleniyor...</CardTitle></CardHeader><CardContent><p>Servis talepleriniz yükleniyor.</p></CardContent></Card>;
  }

  if (!user || user.role !== "student") {
     return (
      <Card className="shadow-lg border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2"><AlertCircle /> Erişim Reddedildi</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Bu sayfayı görüntüleme yetkiniz yok. Lütfen öğrenci hesabınızla giriş yapın.</p>
        </CardContent>
      </Card>
     );
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><ListChecks className="text-primary"/>Servis Taleplerim</CardTitle>
          <CardDescription>
            Geçmiş ve mevcut servis taleplerinizi ve durumlarını buradan takip edebilirsiniz.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {userRequests.length === 0 ? (
            <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
              <ListChecks className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Henüz oluşturulmuş bir servis talebiniz bulunmamaktadır.</p>
               <p className="text-sm text-muted-foreground mt-2">Yeni bir talep oluşturmak için "Servis Talebi" sayfasına gidebilirsiniz.</p>
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Talep Tarihi</TableHead>
                    <TableHead>Alınış Saati</TableHead>
                    <TableHead>Alınış Yeri</TableHead>
                    <TableHead>Bırakılış Yeri</TableHead>
                    <TableHead className="text-center">Durum</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {userRequests.sort((a,b) => new Date(b.requestedPickupTime).getTime() - new Date(a.requestedPickupTime).getTime() ).map((request) => (
                    <TableRow key={request.id}>
                      <TableCell>
                        {format(new Date(request.requestedPickupTime), "dd MMMM yyyy", { locale: tr })}
                      </TableCell>
                      <TableCell>
                        {format(new Date(request.requestedPickupTime), "HH:mm", { locale: tr })}
                      </TableCell>
                      <TableCell>{request.pickupLocation.address}</TableCell>
                      <TableCell>{request.dropoffLocation.address}</TableCell>
                      <TableCell className="text-center">
                        <Badge 
                          variant={statusDisplayMap[request.status].variant}
                          className={cn("font-semibold", statusDisplayMap[request.status].className)}
                        >
                          {statusDisplayMap[request.status].label}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

    