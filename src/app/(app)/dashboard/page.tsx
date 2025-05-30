
"use client";

import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ArrowRight, CalendarCheck, BusFront, UserCog, Settings } from "lucide-react"; // Added Settings icon
import ScheduleConfirmationCard from "@/components/student/schedule-confirmation-card"; // For student notifications

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Yükleniyor...</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Kullanıcı bilgileri yükleniyor, lütfen bekleyin.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Mock AI data for ScheduleConfirmationCard
  const mockAiNotification = {
    studentName: user.name,
    pickupTime: "08:15",
    dropoffTime: "17:45",
    notificationMessage: `Merhaba ${user.name}, yarınki ders programınıza göre servisiniz planlanmıştır. Tahmini alınış saatiniz 08:15, okuldan ayrılış saatiniz ise 17:45'tir.`,
    relevantDate: new Date(new Date().setDate(new Date().getDate() + 1)).toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-3xl">Hoş Geldiniz, {user.name}!</CardTitle>
          <CardDescription>
            UniRide Assist kontrol paneline hoş geldiniz. Buradan ilgili işlemleri yapabilirsiniz.
          </CardDescription>
        </CardHeader>
      </Card>

      {user.role === "student" && (
        <>
          <ScheduleConfirmationCard {...mockAiNotification} />
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><CalendarCheck className="text-primary"/>Hızlı İşlemler</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Link href="/schedule" passHref>
                <Button variant="outline" className="w-full justify-between py-6 text-left">
                  <div>
                    <h3 className="font-semibold">Ders Programım</h3>
                    <p className="text-sm text-muted-foreground">Haftalık programını görüntüle ve düzenle.</p>
                  </div>
                  <ArrowRight />
                </Button>
              </Link>
              <Link href="/request-ride" passHref>
                <Button variant="outline" className="w-full justify-between py-6 text-left">
                  <div>
                    <h3 className="font-semibold">Anlık Servis Talebi</h3>
                    <p className="text-sm text-muted-foreground">Program dışı servis ihtiyacın için talep oluştur.</p>
                  </div>
                  <ArrowRight />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </>
      )}

      {user.role === "admin" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><UserCog className="text-primary"/>Yönetim Paneli</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link href="/admin/vehicles" passHref>
              <Button variant="outline" className="w-full justify-between py-6 text-left">
                 <div>
                    <h3 className="font-semibold">Araç Yönetimi</h3>
                    <p className="text-sm text-muted-foreground">Servis araçlarını yönet.</p>
                  </div>
                  <BusFront />
              </Button>
            </Link>
            <Link href="/admin/users" passHref>
               <Button variant="outline" className="w-full justify-between py-6 text-left">
                 <div>
                    <h3 className="font-semibold">Kullanıcı Yönetimi</h3>
                    <p className="text-sm text-muted-foreground">Öğrenci ve admin hesaplarını yönet.</p>
                  </div>
                  <UserCog />
              </Button>
            </Link>
             <Link href="/admin/ride-requests" passHref>
               <Button variant="outline" className="w-full justify-between py-6 text-left">
                 <div>
                    <h3 className="font-semibold">Servis Talepleri</h3>
                    <p className="text-sm text-muted-foreground">Gelen servis taleplerini onayla/reddet.</p>
                  </div>
                  <CalendarCheck />
              </Button>
            </Link>
            <Link href="/admin/settings" passHref>
               <Button variant="outline" className="w-full justify-between py-6 text-left">
                 <div>
                    <h3 className="font-semibold">Genel Ayarlar</h3>
                    <p className="text-sm text-muted-foreground">Bildirim ve sistem ayarlarını yapılandır.</p>
                  </div>
                  <Settings />
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
