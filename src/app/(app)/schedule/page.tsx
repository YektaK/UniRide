
"use client";

import React, { useState } from "react";
import type { WeeklySchedule, ScheduleEntry } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarDays, PlusCircle, Edit } from "lucide-react";
import ScheduleDisplay from "@/components/student/schedule-display";
// Placeholder for ScheduleFormDialog or similar component
// import ScheduleFormDialog from "@/components/student/schedule-form-dialog";

// Mock data for student schedule
const mockScheduleEntries: ScheduleEntry[] = [
  { id: "se001", dayOfWeek: "monday", courseName: "MAT101 Calculus I", startTime: "09:00", endTime: "11:50", location: "Mühendislik B-101" },
  { id: "se002", dayOfWeek: "monday", courseName: "PHY101 Physics I", startTime: "14:00", endTime: "16:50", location: "Fen Fak. Z-05" },
  { id: "se003", dayOfWeek: "tuesday", courseName: "ENG101 English Comp.", startTime: "10:00", endTime: "11:50", location: "Edebiyat K-203" },
  { id: "se004", dayOfWeek: "wednesday", courseName: "MAT101 Calculus I", startTime: "09:00", endTime: "11:50", location: "Mühendislik B-101" },
  { id: "se005", dayOfWeek: "thursday", courseName: "CS101 Intro to CS", startTime: "13:00", endTime: "15:50", location: "Bilgisayar Lab 1" },
  { id: "se006", dayOfWeek: "friday", courseName: "PHY101 Physics I", startTime: "14:00", endTime: "16:50", location: "Fen Fak. Z-05" },
];

const initialStudentSchedule: WeeklySchedule = {
  id: "schedule001",
  userId: "student001", // Corresponds to mockStudent
  entries: mockScheduleEntries,
  lastUpdated: new Date().toISOString(),
};


export default function SchedulePage() {
  const { user } = useAuth();
  const [schedule, setSchedule] = useState<WeeklySchedule | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // const [isFormOpen, setIsFormOpen] = useState(false);
  // const [editingEntry, setEditingEntry] = useState<ScheduleEntry | null>(null);

  React.useEffect(() => {
    if (user && user.role === "student") {
      // In a real app, fetch schedule based on user.weeklyScheduleId
      if (user.weeklyScheduleId === initialStudentSchedule.id) {
        setSchedule(initialStudentSchedule);
      } else {
        setSchedule({
            id: user.weeklyScheduleId || `new-${user.id}`,
            userId: user.id,
            entries: [],
            lastUpdated: new Date().toISOString()
        });
      }
    }
    setIsLoading(false);
  }, [user]);

  const handleAddEntry = () => {
    // setEditingEntry(null);
    // setIsFormOpen(true);
    alert("Yeni ders programı girişi özelliği yakında eklenecektir.");
  };

  const handleEditEntry = (entry: ScheduleEntry) => {
    // setEditingEntry(entry);
    // setIsFormOpen(true);
     alert(`"${entry.courseName || entry.dayOfWeek}" dersini düzenleme özelliği yakında eklenecektir.`);
  };

  const handleDeleteEntry = (entryId: string) => {
    if (schedule) {
        // setSchedule({
        //     ...schedule,
        //     entries: schedule.entries.filter(e => e.id !== entryId),
        //     lastUpdated: new Date().toISOString()
        // });
        alert("Ders silme özelliği yakında eklenecektir.");
    }
  };
  
  const handleSaveEntry = (entry: ScheduleEntry) => {
    // Logic to save entry (add if new, update if existing)
    // setIsFormOpen(false);
    // setEditingEntry(null);
     alert("Ders kaydetme özelliği yakında eklenecektir.");
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
              Mevcut ders programınızı görüntüleyin ve gerektiğinde güncelleyin.
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
      {/* 
      <ScheduleFormDialog
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        onSave={handleSaveEntry}
        entry={editingEntry}
      />
      */}
    </div>
  );
}

