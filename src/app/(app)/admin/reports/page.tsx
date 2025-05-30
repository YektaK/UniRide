
"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { BarChartHorizontal, Download, Calendar as CalendarIcon, AlertCircle } from "lucide-react";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";
import { BarChart, CartesianGrid, XAxis, YAxis, Bar, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";
import { getUsers, getStudentSchedule } from "@/lib/mock-database";
import type { User, ScheduleEntry } from "@/types";

interface ChartData {
  timeSlot: string;
  Wheelchair: number;
  Other: number;
}

const processScheduleDataForChart = (users: User[]): ChartData[] => {
  const hourlyDemand: Record<string, { wheelchair: number; other: number }> = {};

  const students = users.filter(u => u.role === 'student');

  students.forEach(student => {
    if (student.weeklyScheduleId) {
      const schedule = getStudentSchedule(student.weeklyScheduleId);
      if (schedule) {
        const dailyFirstArrivals: Record<ScheduleEntry["dayOfWeek"], string | null> = {
          monday: null, tuesday: null, wednesday: null, thursday: null, friday: null, saturday: null, sunday: null
        };

        schedule.entries.forEach(entry => {
          if (!dailyFirstArrivals[entry.dayOfWeek] || entry.startTime < dailyFirstArrivals[entry.dayOfWeek]!) {
            dailyFirstArrivals[entry.dayOfWeek] = entry.startTime;
          }
        });
        
        Object.values(dailyFirstArrivals).forEach(firstArrivalTime => {
          if (firstArrivalTime) {
            const hour = firstArrivalTime.substring(0, 2) + ":00"; // Group by hour
            if (!hourlyDemand[hour]) {
              hourlyDemand[hour] = { wheelchair: 0, other: 0 };
            }
            if (student.accessibilityNeeds?.includes("wheelchair")) {
              hourlyDemand[hour].wheelchair++;
            } else {
              hourlyDemand[hour].other++;
            }
          }
        });
      }
    }
  });

  return Object.entries(hourlyDemand)
    .map(([timeSlot, counts]) => ({
      timeSlot,
      Wheelchair: counts.wheelchair,
      Other: counts.other,
    }))
    .sort((a, b) => a.timeSlot.localeCompare(b.timeSlot));
};


const chartConfig = {
  Wheelchair: {
    label: "Tekerlekli Sandalye",
    color: "hsl(var(--chart-1))",
  },
  Other: {
    label: "Diğer",
    color: "hsl(var(--chart-2))",
  },
};

export default function AdminReportsPage() {
  const { toast } = useToast();
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    const allUsers = getUsers();
    const processedData = processScheduleDataForChart(allUsers);
    setChartData(processedData);
    setIsLoading(false);
  }, []);

  const handleDownloadWeekly = () => {
    toast({
      title: "İndirme Başlatıldı (Simülasyon)",
      description: "Haftalık tüm ders programlarının indirilmesi özelliği yakında aktif olacaktır.",
    });
  };

  const handleDownloadDateSpecific = () => {
    if (!selectedDate) {
      toast({
        title: "Tarih Seçilmedi",
        description: "Lütfen indirmek için bir tarih seçin.",
        variant: "destructive",
      });
      return;
    }
    toast({
      title: "İndirme Başlatıldı (Simülasyon)",
      description: `${format(selectedDate, "dd MMMM yyyy", { locale: tr })} tarihli programların indirilmesi özelliği yakında aktif olacaktır.`,
    });
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <BarChartHorizontal className="text-primary" /> Servis Raporları
          </CardTitle>
          <CardDescription>
            Servis kullanımı ve ders programı yoğunlukları hakkında raporları görüntüleyin ve indirin.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          <section className="space-y-4 p-4 border rounded-lg bg-muted/30">
            <h3 className="text-lg font-semibold">Program İndirme</h3>
            <div className="flex flex-col sm:flex-row gap-4 items-start">
              <Button onClick={handleDownloadWeekly} variant="outline">
                <Download className="mr-2 h-4 w-4" /> Haftalık Tüm Programları İndir (CSV)
              </Button>
              <div className="flex items-center gap-2">
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant={"outline"}
                      className="w-[240px] justify-start text-left font-normal"
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {selectedDate ? format(selectedDate, "PPP", { locale: tr }) : <span>Tarih Seçin</span>}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={selectedDate}
                      onSelect={setSelectedDate}
                      initialFocus
                      locale={tr}
                    />
                  </PopoverContent>
                </Popover>
                <Button onClick={handleDownloadDateSpecific} disabled={!selectedDate}>
                  <Download className="mr-2 h-4 w-4" /> Seçili Tarih İçin İndir (CSV)
                </Button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">Not: İndirme işlevleri şu anda simülasyon modundadır.</p>
          </section>

          <section className="space-y-4 p-4 border rounded-lg">
            <h3 className="text-lg font-semibold">Saatlik Varış Yoğunluğu (Tüm Günler Ortalaması)</h3>
            <CardDescription>Öğrencilerin gün içindeki ilk ders başlangıç saatlerine göre dağılımı.</CardDescription>
            {isLoading ? (
              <p>Grafik verileri yükleniyor...</p>
            ) : chartData.length === 0 ? (
               <div className="my-6 p-4 border border-dashed rounded-lg aspect-[16/7] bg-muted flex flex-col items-center justify-center">
                <AlertCircle className="h-12 w-12 text-muted-foreground mb-3" />
                <p className="text-muted-foreground">Görüntülenecek yeterli ders programı verisi bulunamadı.</p>
              </div>
            ) : (
              <div className="h-[400px] w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis 
                        dataKey="timeSlot" 
                        tickLine={false} 
                        axisLine={false} 
                        tickMargin={8}
                        />
                      <YAxis 
                        allowDecimals={false} 
                        tickLine={false} 
                        axisLine={false} 
                        tickMargin={8}
                        />
                      <Tooltip
                        cursorStyle={{ fill: 'hsl(var(--muted))', opacity: 0.5 }}
                        content={<ChartTooltipContent indicator="dot" />}
                      />
                      <Legend content={<ChartLegendContent />} />
                      <Bar dataKey="Wheelchair" stackId="a" fill="var(--color-Wheelchair)" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="Other" stackId="a" fill="var(--color-Other)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
              </div>
            )}
             <p className="text-xs text-muted-foreground pt-2">Bu grafik, öğrencilerin haftalık ders programlarındaki her gün için ilk ders başlangıç saatlerini baz alarak saatlik yoğunluğu gösterir. 'Tekerlekli Sandalye' ve 'Diğer' olarak öğrenci sayıları ayrıştırılmıştır.</p>
          </section>
        </CardContent>
      </Card>
    </div>
  );
}

