
"use client";

import { useEffect, useState } from "react";
import type { WeeklySchedule, ScheduleEntry } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ArrowRight, CalendarCheck, BusFront, UserCog, Settings as SettingsIcon } from "lucide-react";
import ScheduleConfirmationCard from "@/components/student/schedule-confirmation-card";
import { format, addDays } from 'date-fns';
import { tr } from 'date-fns/locale';

interface NextRideInfo {
  studentName: string;
  pickupTime: string;
  dropoffTime: string;
  notificationMessage: string;
  relevantDate: string;
  hasRide: boolean;
}

const daysOrder: ScheduleEntry["dayOfWeek"][] = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];


export default function DashboardPage() {
  const { user, isLoading: authIsLoading } = useAuth();
  const [nextRideInfo, setNextRideInfo] = useState<NextRideInfo | null>(null);
  const [isScheduleLoading, setIsScheduleLoading] = useState(true);

  useEffect(() => {
    if (user && user.role === "student" && user.weeklyScheduleId) {
      setIsScheduleLoading(true);
      try {
        const storedScheduleJson = localStorage.getItem(`schedule_${user.weeklyScheduleId}`);
        let studentSchedule: WeeklySchedule | null = null;
        if (storedScheduleJson) {
          studentSchedule = JSON.parse(storedScheduleJson);
        }

        const tomorrow = addDays(new Date(), 1);
        const tomorrowDayName = daysOrder[tomorrow.getDay()];
        const relevantDateFormatted = format(tomorrow, "dd MMMM yyyy, EEEE", { locale: tr });
        
        let pickupTime = "";
        let dropoffTime = "";
        let notificationMessage = `Merhaba ${user.name}, yarın (${relevantDateFormatted}) için planlanmış bir servisiniz bulunmamaktadır.`;
        let hasRide = false;

        if (studentSchedule && studentSchedule.entries.length > 0) {
          const tomorrowEntries = studentSchedule.entries
            .filter(entry => entry.dayOfWeek === tomorrowDayName)
            .sort((a, b) => a.startTime.localeCompare(b.startTime));

          if (tomorrowEntries.length > 0) {
            pickupTime = tomorrowEntries[0].startTime;
            dropoffTime = tomorrowEntries[tomorrowEntries.length - 1].endTime; // This is class end, not necessarily shuttle dropoff
            // For simplicity, we'll use class times. A real app would use AI to estimate shuttle times.
            notificationMessage = `Merhaba ${user.name}, yarın (${relevantDateFormatted}) için servisiniz planlanmıştır. Tahmini okulda olma saatiniz ${pickupTime}, okuldan ayrılış saatiniz ise ${dropoffTime} olacaktır. Lütfen servis saatleri için ayrıca onayınızı bekleyin.`;
            hasRide = true;
          }
        }
        
        setNextRideInfo({
          studentName: user.name,
          pickupTime: hasRide ? pickupTime : "N/A", // Placeholder if no ride
          dropoffTime: hasRide ? dropoffTime : "N/A", // Placeholder if no ride
          notificationMessage,
          relevantDate: relevantDateFormatted,
          hasRide,
        });

      } catch (error) {
        console.error("Error processing schedule for dashboard:", error);
        setNextRideInfo({
          studentName: user.name,
          pickupTime: "Hata",
          dropoffTime: "Hata",
          notificationMessage: `Merhaba ${user.name}, servis bilgileriniz yüklenirken bir sorun oluştu.`,
          relevantDate: format(addDays(new Date(), 1), "dd MMMM yyyy, EEEE", { locale: tr }),
          hasRide: false,
        });
      } finally {
        setIsScheduleLoading(false);
      }
    } else if (user && user.role !== "student") {
      setIsScheduleLoading(false); // No schedule to load for admin
    }
  }, [user]);


  if (authIsLoading) {
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
  
  if (!user) return null; // Should be redirected by layout if no user

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
          {isScheduleLoading && <Card><CardContent><p>Servis bilgileriniz yükleniyor...</p></CardContent></Card>}
          {!isScheduleLoading && nextRideInfo && nextRideInfo.hasRide && (
            <ScheduleConfirmationCard {...nextRideInfo} />
          )}
          {!isScheduleLoading && nextRideInfo && !nextRideInfo.hasRide && (
             <Card className="bg-muted/50 border-border">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-xl">
                    <CalendarCheck className="h-6 w-6 text-muted-foreground" />
                    Servis Planı: {nextRideInfo.relevantDate}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p>{nextRideInfo.notificationMessage}</p>
                </CardContent>
            </Card>
          )}
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
                  <SettingsIcon /> {/* Renamed from Settings */}
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

    