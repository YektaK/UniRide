
"use client";

import React, { useEffect, useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BarChartHorizontal, Download, AlertCircle, CalendarRange } from "lucide-react";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
} from "@/components/ui/chart";
import { BarChart, CartesianGrid, XAxis, YAxis, Bar, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { format, getDay, startOfWeek, addDays, endOfWeek } from "date-fns";
import { tr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";
import { getUsers, getStudentSchedule } from "@/lib/database";
import type { User, ScheduleEntry } from "@/types";

interface ChartData {
  timeSlot: string;
  Wheelchair: number;
  Other: number;
}

const daysOrder: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const localizedDays: Record<ScheduleEntry["dayOfWeek"], string> = {
  monday: "Pazartesi",
  tuesday: "Salı",
  wednesday: "Çarşamba",
  thursday: "Perşembe",
  friday: "Cuma",
  saturday: "Cumartesi",
  sunday: "Pazar",
};


const processArrivalDataForChart = async (users: User[], targetDate: Date | undefined): Promise<ChartData[]> => {
  if (!targetDate) return [];
  const hourlyDemand: Record<string, { wheelchair: number; other: number }> = {};
  const students = users.filter(u => u.role === 'student');
  const dayIndex = getDay(targetDate);
  const targetDayName = daysOrder[dayIndex === 0 ? 6 : dayIndex - 1];

  // Process all students in parallel
  await Promise.all(students.map(async (student) => {
    if (student.weeklyScheduleId) {
      try {
        const schedule = await getStudentSchedule(student.weeklyScheduleId);
        if (schedule) {
          const entriesForTargetDay = schedule.entries
            .filter(entry => entry.dayOfWeek === targetDayName)
            .sort((a, b) => a.startTime.localeCompare(b.startTime));

          if (entriesForTargetDay.length > 0) {
            const firstArrivalTime = entriesForTargetDay[0].startTime;
            const hour = firstArrivalTime.substring(0, 2) + ":00";
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
      } catch (error) {
        console.error(`Error loading schedule for student ${student.id}:`, error);
      }
    }
  }));

  return Object.entries(hourlyDemand)
    .map(([timeSlot, counts]) => ({
      timeSlot,
      Wheelchair: counts.wheelchair,
      Other: counts.other,
    }))
    .sort((a, b) => a.timeSlot.localeCompare(b.timeSlot));
};

const processDepartureDataForChart = async (users: User[], targetDate: Date | undefined): Promise<ChartData[]> => {
  if (!targetDate) return [];
  const hourlyDemand: Record<string, { wheelchair: number; other: number }> = {};
  const students = users.filter(u => u.role === 'student');
  const dayIndex = getDay(targetDate);
  const targetDayName = daysOrder[dayIndex === 0 ? 6 : dayIndex - 1];

  // Process all students in parallel
  await Promise.all(students.map(async (student) => {
    if (student.weeklyScheduleId) {
      try {
        const schedule = await getStudentSchedule(student.weeklyScheduleId);
        if (schedule) {
          const entriesForTargetDay = schedule.entries
            .filter(entry => entry.dayOfWeek === targetDayName)
            .sort((a, b) => a.endTime.localeCompare(b.endTime));

          if (entriesForTargetDay.length > 0) {
            const lastDepartureTime = entriesForTargetDay[entriesForTargetDay.length - 1].endTime;
            const hour = lastDepartureTime.substring(0, 2) + ":00";
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
      } catch (error) {
        console.error(`Error loading schedule for student ${student.id}:`, error);
      }
    }
  }));

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

const DEFAULT_Y_AXIS_MAX = 5;

interface DailyChartInfo {
  date: Date;
  dayNameKey: ScheduleEntry["dayOfWeek"];
  arrivalData: ChartData[];
  departureData: ChartData[];
}

export default function AdminReportsPage() {
  const { toast } = useToast();
  const [weeklyChartData, setWeeklyChartData] = useState<DailyChartInfo[]>([]);
  const [globalArrivalMaxY, setGlobalArrivalMaxY] = useState<number>(DEFAULT_Y_AXIS_MAX);
  const [globalDepartureMaxY, setGlobalDepartureMaxY] = useState<number>(DEFAULT_Y_AXIS_MAX);
  const [isLoading, setIsLoading] = useState(true);
  const [currentWeekDisplay, setCurrentWeekDisplay] = useState<string>("");

  useEffect(() => {
    const loadReports = async () => {
      try {
        const allUsers = await getUsers();
        const today = new Date();
        const weekStart = startOfWeek(today, { weekStartsOn: 1, locale: tr });

        setCurrentWeekDisplay(
          `${format(weekStart, "dd MMMM", { locale: tr })} - ${format(addDays(weekStart, 6), "dd MMMM yyyy", { locale: tr })}`
        );

        const daysInWeek: Date[] = [];
        for (let i = 0; i < 7; i++) {
          daysInWeek.push(addDays(weekStart, i));
        }

        let maxArrivalForWeek = 0;
        let maxDepartureForWeek = 0;

        // Process all days in parallel
        const processedDataForWeek = await Promise.all(daysInWeek.map(async (date) => {
          const dayIndex = getDay(date);
          const dayNameKey = daysOrder[dayIndex === 0 ? 6 : dayIndex - 1];

          const [arrivalData, departureData] = await Promise.all([
            processArrivalDataForChart(allUsers, date),
            processDepartureDataForChart(allUsers, date),
          ]);

          if (arrivalData.length > 0) {
            const dayMaxArrival = Math.max(...arrivalData.map(d => d.Wheelchair + d.Other));
            if (dayMaxArrival > maxArrivalForWeek) maxArrivalForWeek = dayMaxArrival;
          }
          if (departureData.length > 0) {
            const dayMaxDeparture = Math.max(...departureData.map(d => d.Wheelchair + d.Other));
            if (dayMaxDeparture > maxDepartureForWeek) maxDepartureForWeek = dayMaxDeparture;
          }

          return { date, dayNameKey, arrivalData, departureData };
        }));

        setWeeklyChartData(processedDataForWeek);
        setGlobalArrivalMaxY(maxArrivalForWeek > 0 ? maxArrivalForWeek + 1 : DEFAULT_Y_AXIS_MAX);
        setGlobalDepartureMaxY(maxDepartureForWeek > 0 ? maxDepartureForWeek + 1 : DEFAULT_Y_AXIS_MAX);
      } catch (error) {
        console.error("Error loading reports:", error);
        toast({
          title: "Rapor Yükleme Hatası",
          description: "Rapor verileri yüklenirken bir hata oluştu.",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };
    loadReports();
  }, []);

  const handleDownloadWeekly = () => {
    toast({
      title: "İndirme Başlatıldı (Simülasyon)",
      description: "Haftalık tüm ders programlarının ve yoğunluk verilerinin indirilmesi özelliği yakında aktif olacaktır.",
    });
  };

  const hasAnyDataForWeek = useMemo(() => {
    return weeklyChartData.some(dayInfo => dayInfo.arrivalData.length > 0 || dayInfo.departureData.length > 0);
  }, [weeklyChartData]);

  return (
    <div className="space-y-8">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2">
            <BarChartHorizontal className="text-primary" /> Haftalık Servis Raporları
          </CardTitle>
          <CardDescription>
            İçinde bulunulan hafta ({currentWeekDisplay}) için günlük servis kullanım yoğunluklarını görüntüleyin ve programları indirin.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <section className="space-y-4 p-4 border rounded-lg bg-muted/30">
            <h3 className="text-lg font-semibold">Haftalık Program İndirme</h3>
            <div className="flex flex-col sm:flex-row gap-4 items-start">
              <Button onClick={handleDownloadWeekly} variant="outline" className="w-full sm:w-auto">
                <Download className="mr-2 h-4 w-4" /> Haftalık Verileri İndir (CSV)
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Not: İndirme işlevi şu anda simülasyon modundadır.</p>
          </section>
        </CardContent>
      </Card>

      {/* Combined Daily Arrival and Departure Charts Section */}
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-xl flex items-center gap-2">
            <CalendarRange className="text-primary" /> Günlük Servis Yoğunlukları ({currentWeekDisplay})
          </CardTitle>
          <CardDescription>Öğrencilerin hafta boyunca günlük ilk ders başlangıç ve son ders bitiş saatlerine göre dağılımı.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading ? (
            <p>Haftalık grafik verileri yükleniyor...</p>
          ) : !hasAnyDataForWeek ? (
            <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground border border-dashed rounded-md">
              <AlertCircle className="h-12 w-12 mb-4" />
              <p>Bu hafta için görüntülenecek program verisi bulunmamaktadır.</p>
            </div>
          ) : (
            weeklyChartData.map(({ date, dayNameKey, arrivalData, departureData }) => {
              if (arrivalData.length === 0 && departureData.length === 0) {
                return null; // Hide day if no arrival and no departure data
              }
              return (
                <Card key={dayNameKey} className="flex flex-col shadow-md">
                  <CardHeader className="pb-2 border-b">
                    <CardTitle className="text-lg font-semibold text-primary">
                      {localizedDays[dayNameKey]} - {format(date, "dd MMMM yyyy", { locale: tr })}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-6">
                      {/* Arrival Chart for the day */}
                      <div className="space-y-2">
                        <h3 className="text-md font-medium text-center">Varış Yoğunluğu</h3>
                        {arrivalData.length === 0 ? (
                          <div className="h-[250px] flex flex-col items-center justify-center text-muted-foreground border border-dashed rounded-md">
                            <AlertCircle className="h-8 w-8 mb-2" />
                            <p className="text-xs">Varış verisi yok</p>
                          </div>
                        ) : (
                          <ChartContainer config={chartConfig} className="h-[250px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={arrivalData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="timeSlot" tickLine={false} axisLine={false} tickMargin={8} fontSize={10} />
                                <YAxis allowDecimals={false} tickLine={false} axisLine={false} tickMargin={8} domain={[0, globalArrivalMaxY]} fontSize={10} />
                                <Tooltip cursorStyle={{ fill: 'hsl(var(--muted))', opacity: 0.5 }} content={<ChartTooltipContent indicator="dot" />} />
                                <Legend content={<ChartLegendContent className="text-xs mt-1" />} wrapperStyle={{ fontSize: '10px' }} />
                                <Bar dataKey="Wheelchair" stackId="arrival" fill="var(--color-Wheelchair)" radius={[2, 2, 0, 0]} barSize={15} />
                                <Bar dataKey="Other" stackId="arrival" fill="var(--color-Other)" radius={[2, 2, 0, 0]} barSize={15} />
                              </BarChart>
                            </ResponsiveContainer>
                          </ChartContainer>
                        )}
                        <p className="text-xs text-muted-foreground text-center pt-1">İlk ders başlangıç saatlerine göre.</p>
                      </div>

                      {/* Departure Chart for the day */}
                      <div className="space-y-2">
                        <h3 className="text-md font-medium text-center">Ayrılış Yoğunluğu</h3>
                        {departureData.length === 0 ? (
                          <div className="h-[250px] flex flex-col items-center justify-center text-muted-foreground border border-dashed rounded-md">
                            <AlertCircle className="h-8 w-8 mb-2" />
                            <p className="text-xs">Ayrılış verisi yok</p>
                          </div>
                        ) : (
                          <ChartContainer config={chartConfig} className="h-[250px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={departureData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="timeSlot" tickLine={false} axisLine={false} tickMargin={8} fontSize={10} />
                                <YAxis allowDecimals={false} tickLine={false} axisLine={false} tickMargin={8} domain={[0, globalDepartureMaxY]} fontSize={10} />
                                <Tooltip cursorStyle={{ fill: 'hsl(var(--muted))', opacity: 0.5 }} content={<ChartTooltipContent indicator="dot" />} />
                                <Legend content={<ChartLegendContent className="text-xs mt-1" />} wrapperStyle={{ fontSize: '10px' }} />
                                <Bar dataKey="Wheelchair" stackId="departure" fill="var(--color-Wheelchair)" radius={[2, 2, 0, 0]} barSize={15} />
                                <Bar dataKey="Other" stackId="departure" fill="var(--color-Other)" radius={[2, 2, 0, 0]} barSize={15} />
                              </BarChart>
                            </ResponsiveContainer>
                          </ChartContainer>
                        )}
                        <p className="text-xs text-muted-foreground text-center pt-1">Son ders bitiş saatlerine göre.</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })
          )}
          <p className="text-xs text-muted-foreground pt-4">Bu grafikler, öğrencilerin haftanın her günü için ilk ders başlangıç ve son ders bitiş saatlerini baz alarak saatlik varış ve ayrılış yoğunluğunu gösterir.</p>
        </CardContent>
      </Card>
    </div>
  );
}
