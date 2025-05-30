
"use client";

import React, { useState, useEffect } from "react";
import type { WeeklySchedule, ScheduleEntry } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarDays, PlusCircle } from "lucide-react";
import ScheduleDisplay from "@/components/student/schedule-display";
import ScheduleFormDialog from "@/components/student/schedule-form-dialog"; // Import the new dialog

// Mock data for student schedule
const mockScheduleEntriesStudent1: ScheduleEntry[] = [
  { id: "se001", dayOfWeek: "monday", courseName: "MAT101 Calculus I", startTime: "09:00", endTime: "11:50", location: "Dudullu" },
  { id: "se002", dayOfWeek: "monday", courseName: "PHY101 Physics I", startTime: "14:00", endTime: "16:50", location: "Dudullu" },
  { id: "se003", dayOfWeek: "tuesday", courseName: "ENG101 English Comp.", startTime: "10:00", endTime: "11:50", location: "Dudullu" },
  { id: "se004", dayOfWeek: "wednesday", courseName: "MAT101 Calculus I", startTime: "09:00", endTime: "11:50", location: "Dudullu" },
  { id: "se005", dayOfWeek: "thursday", courseName: "CS101 Intro to CS", startTime: "13:00", endTime: "15:50", location: "Dudullu" },
  { id: "se006", dayOfWeek: "friday", courseName: "PHY101 Physics I", startTime: "14:00", endTime: "16:50", location: "Dudullu" },
];

const initialSchedules: Record<string, WeeklySchedule> = {
  "schedule001": { // For student001 (Ayşe)
    id: "schedule001",
    userId: "student001",
    entries: mockScheduleEntriesStudent1,
    lastUpdated: new Date().toISOString(),
  },
  "schedule002": { // For student002 (Veli) - empty initially
    id: "schedule002",
    userId: "student002",
    entries: [],
    lastUpdated: new Date().toISOString(),
  },
  "schedule003": { // For student003 (Zeynep) - one entry
    id: "schedule003",
    userId: "student003",
    entries: [
        { id: "se007", dayOfWeek: "wednesday", courseName: "TURK101 Turkish Lang.", startTime: "10:00", endTime: "11:50", location: "Dudullu" }
    ],
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
      // Load schedule from localStorage if exists, otherwise from initialSchedules
      const storedScheduleJson = localStorage.getItem(`schedule_${user.weeklyScheduleId}`);
      if (storedScheduleJson) {
        const storedSchedule = JSON.parse(storedScheduleJson);
        // Ensure locations in stored schedule are valid, default to "Dudullu" if not
        const updatedEntries = storedSchedule.entries.map((entry: ScheduleEntry) => ({
            ...entry,
            location: (entry.location === "Dudullu" || entry.location === "Çengelköy") ? entry.location : "Dudullu"
        }));
        setSchedule({...storedSchedule, entries: updatedEntries});

      } else if (initialSchedules[user.weeklyScheduleId]) {
         // Ensure locations in initialSchedules are valid (already done in mock data, but good practice)
        const initialSched = initialSchedules[user.weeklyScheduleId];
        const updatedEntries = initialSched.entries.map((entry: ScheduleEntry) => ({
            ...entry,
            location: (entry.location === "Dudullu" || entry.location === "Çengelköy") ? entry.location : "Dudullu"
        }));
        setSchedule({...initialSched, entries: updatedEntries});

      } else {
         // Fallback for new students not in initialSchedules
        setSchedule({
            id: user.weeklyScheduleId,
            userId: user.id,
            entries: [],
            lastUpdated: new Date().toISOString()
        });
      }
    }
    setIsLoading(false);
  }, [user]);

  // Save schedule to localStorage whenever it changes
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
      if (entryId) { // Editing existing entry
        setSchedule({
          ...schedule,
          entries: schedule.entries.map(e => e.id === entryId ? { ...e, ...entryData, id: entryId } : e), // ensure id is preserved
          lastUpdated: new Date().toISOString()
        });
      } else { // Adding new entry
        const newEntry: ScheduleEntry = {
          ...entryData,
          id: `se${Date.now()}` // Simple unique ID generation
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
