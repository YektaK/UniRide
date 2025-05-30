
"use client";

import React, { useState, useEffect } from "react";
import type { WeeklySchedule, ScheduleEntry, UserRole } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarDays, PlusCircle } from "lucide-react";
import ScheduleDisplay from "@/components/student/schedule-display";
import ScheduleFormDialog from "@/components/student/schedule-form-dialog";

const daysOfWeek: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday"];
const locations: ("Dudullu" | "Çengelköy")[] = ["Dudullu", "Çengelköy"];

const generateRandomTime = (minHour = 8, maxHour = 15): string => {
  const hour = Math.floor(Math.random() * (maxHour - minHour + 1)) + minHour;
  const minute = Math.random() < 0.5 ? 0 : 30;
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
};

const addHours = (time: string, hoursToAdd: number): string => {
  const [hour, minute] = time.split(':').map(Number);
  const date = new Date();
  date.setHours(hour, minute, 0, 0);
  date.setHours(date.getHours() + hoursToAdd);
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const generateRandomCourseCode = (): string => {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const numLetters = Math.random() < 0.5 ? 2 : 3;
  let code = "";
  for (let i = 0; i < numLetters; i++) {
    code += letters.charAt(Math.floor(Math.random() * letters.length));
  }
  for (let i = 0; i < 3; i++) {
    code += Math.floor(Math.random() * 10);
  }
  return code;
};

const generateRandomScheduleEntries = (): ScheduleEntry[] => {
  const entries: ScheduleEntry[] = [];
  const selectedDays = [...daysOfWeek].sort(() => 0.5 - Math.random()).slice(0, 4); // Select 4 random days

  selectedDays.forEach(day => {
    const numClasses = Math.floor(Math.random() * 3) + 1; // 1 to 3 classes
    let lastEndTime = "00:00";

    for (let i = 0; i < numClasses; i++) {
      let startTime: string;
      let endTime: string;
      let attempts = 0;

      // Try to find a non-overlapping time slot
      do {
        startTime = generateRandomTime(8, 14); // Ensure start time allows for duration
        const duration = Math.floor(Math.random() * 3) + 2; // 2 to 4 hours
        endTime = addHours(startTime, duration);
        attempts++;
      } while (startTime <= lastEndTime && endTime <= "19:00" && attempts < 10); // Prevent overlaps and late end times

      if (startTime > lastEndTime && endTime <= "19:00") { // Max end time 7 PM
        entries.push({
          id: `se${Date.now()}${i}${day}`,
          dayOfWeek: day,
          courseName: generateRandomCourseCode(),
          startTime,
          endTime,
          location: locations[Math.floor(Math.random() * locations.length)],
        });
        lastEndTime = endTime;
      }
    }
  });
  return entries.sort((a,b) => daysOfWeek.indexOf(a.dayOfWeek) - daysOfWeek.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime));
};


const initialSchedules: Record<string, WeeklySchedule> = {
  "schedule001": { // For student001 (Ayşe)
    id: "schedule001",
    userId: "student001",
    entries: generateRandomScheduleEntries(),
    lastUpdated: new Date().toISOString(),
  },
  "schedule002": { // For student002 (Veli)
    id: "schedule002",
    userId: "student002",
    entries: generateRandomScheduleEntries(),
    lastUpdated: new Date().toISOString(),
  },
  "schedule003": { // For student003 (Zeynep)
    id: "schedule003",
    userId: "student003",
    entries: generateRandomScheduleEntries(),
    lastUpdated: new Date().toISOString(),
  }
};


export default function SchedulePage() {
  const { user } = useAuth();
  const [schedule, setSchedule] = useState<WeeklySchedule | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ScheduleEntry | null>(null);

  useEffect(() => {
    if (user && user.role === "student" && user.weeklyScheduleId) {
      const storedScheduleJson = localStorage.getItem(`schedule_${user.weeklyScheduleId}`);
      if (storedScheduleJson) {
        const storedSchedule = JSON.parse(storedScheduleJson) as WeeklySchedule;
        const updatedEntries = storedSchedule.entries.map((entry: ScheduleEntry) => ({
            ...entry,
            location: (entry.location === "Dudullu" || entry.location === "Çengelköy") ? entry.location : "Dudullu"
        }));
        setSchedule({...storedSchedule, entries: updatedEntries});
      } else if (initialSchedules[user.weeklyScheduleId]) {
        const initialSched = initialSchedules[user.weeklyScheduleId];
         const updatedEntries = initialSched.entries.map((entry: ScheduleEntry) => ({
            ...entry,
            location: (entry.location === "Dudullu" || entry.location === "Çengelköy") ? entry.location : "Dudullu"
        }));
        setSchedule({...initialSched, entries: updatedEntries});
      } else {
        setSchedule({
            id: user.weeklyScheduleId,
            userId: user.id,
            entries: generateRandomScheduleEntries(), // Generate for new users not in initialSchedules
            lastUpdated: new Date().toISOString()
        });
      }
    }
    setIsLoading(false);
  }, [user]);

  useEffect(() => {
    if (schedule && user && user.role === "student" && user.weeklyScheduleId) {
      localStorage.setItem(`schedule_${user.weeklyScheduleId}`, JSON.stringify(schedule));
    }
  }, [schedule, user]);


  const handleAddEntry = () => {
    setEditingEntry(null);
    setIsFormOpen(true);
  };

  const handleEditEntry = (entry: ScheduleEntry) => {
    setEditingEntry(entry);
    setIsFormOpen(true);
  };

  const handleDeleteEntry = (entryId: string) => {
    if (schedule && window.confirm("Bu ders girişini silmek istediğinizden emin misiniz?")) {
        setSchedule({
            ...schedule,
            entries: schedule.entries.filter(e => e.id !== entryId),
            lastUpdated: new Date().toISOString()
        });
    }
  };
  
  const handleSaveEntry = (entryData: Omit<ScheduleEntry, 'id'>, entryId?: string) => {
    if (schedule) {
      if (entryId) { 
        setSchedule({
          ...schedule,
          entries: schedule.entries.map(e => e.id === entryId ? { ...e, ...entryData, id: entryId } : e),
          lastUpdated: new Date().toISOString()
        });
      } else { 
        const newEntry: ScheduleEntry = {
          ...entryData,
          id: `se${Date.now()}` 
        };
        setSchedule({
          ...schedule,
          entries: [...schedule.entries, newEntry],
          lastUpdated: new Date().toISOString()
        });
      }
    }
    setIsFormOpen(false);
    setEditingEntry(null);
  };


  if (isLoading) {
    return <Card><CardHeader><CardTitle>Yükleniyor...</CardTitle></CardHeader><CardContent><p>Ders programınız yükleniyor.</p></CardContent></Card>;
  }

  if (!user || user.role !== "student") {
    return <Card><CardHeader><CardTitle>Erişim Reddedildi</CardTitle></CardHeader><CardContent><p>Bu sayfayı görüntüleme yetkiniz yok.</p></CardContent></Card>;
  }

  if (!schedule) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ders Programı Bulunamadı</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Haftalık ders programınız henüz oluşturulmamış. Lütfen ekleyin.</p>
          <Button onClick={handleAddEntry} className="mt-4">
            <PlusCircle className="mr-2 h-4 w-4" /> Program Oluştur
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><CalendarDays className="text-primary"/>Haftalık Ders Programım</CardTitle>
            <CardDescription>
              Mevcut ders programınızı görüntüleyin ve gerektiğinde güncelleyin. Bu program, servis planlamanız için kullanılacaktır.
            </CardDescription>
          </div>
          <Button onClick={handleAddEntry}>
            <PlusCircle className="mr-2 h-4 w-4" /> Yeni Ders Ekle
          </Button>
        </CardHeader>
        <CardContent>
          <ScheduleDisplay 
            scheduleEntries={schedule.entries} 
            onEdit={handleEditEntry}
            onDelete={handleDeleteEntry}
          />
        </CardContent>
      </Card>
      
      <ScheduleFormDialog
        isOpen={isFormOpen}
        onClose={() => {
            setIsFormOpen(false);
            setEditingEntry(null);
        }}
        onSave={handleSaveEntry}
        entry={editingEntry}
      />
    </div>
  );
}

    