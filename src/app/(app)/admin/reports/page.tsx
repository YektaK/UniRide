
"use client";

import React, { useEffect, useState, useMemo } from "react";
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
import { format, getDay } from "date-fns";
import { tr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";
import { getUsers, getStudentSchedule } from "@/lib/mock-database";
import type { User, ScheduleEntry } from "@/types";

interface ChartData {
  timeSlot: string;
  Wheelchair: number;
  Other: number;
}

const daysOrder: ScheduleEntry["dayOfWeek"][] = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];

const processArrivalDataForChart = (users: User[], targetDate: Date | undefined): ChartData[] => {
  if (!targetDate) return [];
  const hourlyDemand: Record<string, { wheelchair: number; other: number }> = {};
  const students = users.filter(u => u.role === 'student');
  const targetDayName = daysOrder[getDay(targetDate)];

  students.forEach(student => {
    if (student.weeklyScheduleId) {
      const schedule = getStudentSchedule(student.weeklyScheduleId);
      if (schedule) {
        const entriesForTargetDay = schedule.entries
          .filter(entry => entry.dayOfWeek === targetDayName)
          .sort((a, b) => a.startTime.localeCompare(b.startTime));

        if (entriesForTargetDay.length > 0) {
          const firstArrivalTime = entriesForTargetDay[0].startTime;
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

const processDepartureDataForChart = (users: User[], targetDate: Date | undefined): ChartData[] => {
  if (!targetDate) return [];
  const hourlyDemand: Record<string, { wheelchair: number; other: number }> = {};
  const students = users.filter(u => u.role === 'student');
  const targetDayName = daysOrder[getDay(targetDate)];

  students.forEach(student => {
    if (student.weeklyScheduleId) {
      const schedule = getStudentSchedule(student.weeklyScheduleId);
      if (schedule) {
        const entriesForTargetDay = schedule.entries
          .filter(entry => entry.dayOfWeek === targetDayName)
          .sort((a, b) => a.endTime.localeCompare(b.endTime)); // Sort by end time for departure

        if (entriesForTargetDay.length > 0) {
          const lastDepartureTime = entriesForTargetDay[entriesForTargetDay.length - 1].endTime;
          const hour = lastDepartureTime.substring(0, 2) + ":00"; // Group by hour
          if (!hourlyDemand[hour]) {
            hourlyDemand[hour] = { wheelchair: 0, other: 0 };
          }
          if (student.accessibilityNeeds?.includes("wheelchair")) {
            hourlyDemand[hour].wheelchair++;
          } else {
            hourlyDemand[hour].other++;
          }
        }
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
  const [arrivalChartData, setArrivalChartData] = useState<ChartData[]>([]);
  const [departureChartData, setDepartureChartData] = useState<ChartData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (selectedDate) {
      setIsLoading(true);
      const allUsers = getUsers();
      const processedArrivalData = processArrivalDataForChart(allUsers, selectedDate);
      const processedDepartureData = processDepartureDataForChart(allUsers, selectedDate);
      setArrivalChartData(processedArrivalData);
      setDepartureChartData(processedDepartureData);
      setIsLoading(false);
    } else {
      setArrivalChartData([]);
      setDepartureChartData([]);
      setIsLoading(false);
    }
  }, [selectedDate]);

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
  
  const formattedSelectedDate = useMemo(() => {
    return selectedDate ? format(selectedDate, "dd MMMM yyyy, EEEE", { locale: tr }) : "Tarih Seçilmedi";
  }, [selectedDate]);

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <BarChartHorizontal className="text-primary" /> Servis Raporları
          </CardTitle>
          <CardDescription>
            Seçili tarihe göre servis kullanım yoğunluklarını görüntüleyin ve programları indirin.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          <section className="space-y-4 p-4 border rounded-lg bg-muted/30">
            <h3 className="text-lg font-semibold">Rapor Tarihi ve İndirme</h3>
            <div className="flex flex-col sm:flex-row gap-4 items-start">
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant={"outline"}
                      className="w-full sm:w-[280px] justify-start text-left font-normal"
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
                <Button onClick={handleDownloadDateSpecific} disabled={!selectedDate} className="w-full sm:w-auto">
                  <Download className="mr-2 h-4 w-4" /> Seçili Tarih İçin İndir (CSV)
                </Button>
                 <Button onClick={handleDownloadWeekly} variant="outline" className="w-full sm:w-auto">
                    <Download className="mr-2 h-4 w-4" /> Haftalık Tüm Programları İndir (CSV)
                </Button>
            </div>
            <p className="text-xs text-muted-foreground">Not: İndirme işlevleri şu anda simülasyon modundadır.</p>
          </section>

          {/* Arrival Chart Section */}
          <section className="space-y-4 p-4 border rounded-lg">
            <h3 className="text-lg font-semibold">Saatlik Varış Yoğunluğu ({formattedSelectedDate})</h3>
            <CardDescription>Öğrencilerin seçili gün içindeki ilk ders başlangıç saatlerine göre dağılımı.</CardDescription>
            {isLoading ? (
              <p>Varış grafiği verileri yükleniyor...</p>
            ) : arrivalChartData.length === 0 ? (
               <div className="my-6 p-4 border border-dashed rounded-lg aspect-[16/7] bg-muted flex flex-col items-center justify-center">
                <AlertCircle className="h-12 w-12 text-muted-foreground mb-3" />
                <p className="text-muted-foreground">Seçili tarih için varış verisi bulunamadı.</p>
              </div>
            ) : (
              <ChartContainer config={chartConfig} className="h-[400px] w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={arrivalChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
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
                      <Bar dataKey="Wheelchair" stackId="arrival" fill="var(--color-Wheelchair)" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="Other" stackId="arrival" fill="var(--color-Other)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
              </ChartContainer>
            )}
             <p className="text-xs text-muted-foreground pt-2">Bu grafik, öğrencilerin seçilen gündeki ilk ders başlangıç saatlerini baz alarak saatlik varış yoğunluğunu gösterir.</p>
          </section>

          {/* Departure Chart Section */}
          <section className="space-y-4 p-4 border rounded-lg">
            <h3 className="text-lg font-semibold">Saatlik Ayrılış Yoğunluğu ({formattedSelectedDate})</h3>
            <CardDescription>Öğrencilerin seçili gün içindeki son ders bitiş saatlerine göre dağılımı.</CardDescription>
            {isLoading ? (
              <p>Ayrılış grafiği verileri yükleniyor...</p>
            ) : departureChartData.length === 0 ? (
               <div className="my-6 p-4 border border-dashed rounded-lg aspect-[16/7] bg-muted flex flex-col items-center justify-center">
                <AlertCircle className="h-12 w-12 text-muted-foreground mb-3" />
                <p className="text-muted-foreground">Seçili tarih için ayrılış verisi bulunamadı.</p>
              </div>
            ) : (
              <ChartContainer config={chartConfig} className="h-[400px] w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={departureChartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
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
                      <Bar dataKey="Wheelchair" stackId="departure" fill="var(--color-Wheelchair)" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="Other" stackId="departure" fill="var(--color-Other)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
              </ChartContainer>
            )}
             <p className="text-xs text-muted-foreground pt-2">Bu grafik, öğrencilerin seçilen gündeki son ders bitiş saatlerini baz alarak saatlik ayrılış yoğunluğunu gösterir.</p>
          </section>

        </CardContent>
      </Card>
    </div>
  );
}


    