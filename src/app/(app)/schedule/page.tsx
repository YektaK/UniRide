
"use client";

import React, { useState, useEffect } from "react";
import type { WeeklySchedule, ScheduleEntry } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarDays, PlusCircle } from "lucide-react";
import ScheduleDisplay from "@/components/student/schedule-display";
import ScheduleFormDialog from "@/components/student/schedule-form-dialog";
import { getStudentSchedule, updateStudentScheduleEntries, createNewUserSchedule } from "@/lib/mock-database";

const allPossibleDays: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export default function SchedulePage() {
  const { user } = useAuth();
  const [schedule, setSchedule] = useState<WeeklySchedule | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ScheduleEntry | null>(null);

  useEffect(() => {
    setIsLoading(true);
    if (user && user.role === "student" && user.weeklyScheduleId) {
      let userSchedule = getStudentSchedule(user.weeklyScheduleId);
      if (!userSchedule) {
        // If schedule doesn't exist in mock DB (e.g. for a newly registered student not in initial mocks)
        // create a new empty schedule for them.
        // For this demo, we'll assume weeklyScheduleId is always pre-assigned and exists or we create it.
        userSchedule = createNewUserSchedule(user.id, user.weeklyScheduleId);
      }
      setSchedule(userSchedule || null);
    }
    setIsLoading(false);
  }, [user]);

  const handleAddEntry = () => {
    setEditingEntry(null);
    setIsFormOpen(true);
  };

  const handleEditEntry = (entry: ScheduleEntry) => {
    setEditingEntry(entry);
    setIsFormOpen(true);
  };

  const handleDeleteEntry = (entryId: string) => {
    if (schedule && user && user.weeklyScheduleId && window.confirm("Bu ders girişini silmek istediğinizden emin misiniz?")) {
        const updatedEntries = schedule.entries.filter(e => e.id !== entryId);
        // No need to sort here, updateStudentScheduleEntries will handle it.
        if (updateStudentScheduleEntries(user.weeklyScheduleId, updatedEntries)) {
            setSchedule(prevSchedule => prevSchedule ? {...prevSchedule, entries: updatedEntries, lastUpdated: new Date().toISOString()} : null);
        } else {
            // Handle error - e.g. schedule not found in mock DB
            console.error("Error deleting entry: Schedule not found in mock DB");
        }
    }
  };
  
  const handleSaveEntry = (entryData: Omit<ScheduleEntry, 'id'>, entryId?: string) => {
    if (schedule && user && user.weeklyScheduleId) {
      let updatedEntries;
      if (entryId) { 
        updatedEntries = schedule.entries.map(e => e.id === entryId ? { ...e, ...entryData, id: entryId } : e);
      } else { 
        const newEntry: ScheduleEntry = {
          ...entryData,
          id: `se${Date.now()}${Math.random().toString(36).substring(2, 7)}`
        };
        updatedEntries = [...schedule.entries, newEntry];
      }
      
      // The sort will be handled by updateStudentScheduleEntries
      if (updateStudentScheduleEntries(user.weeklyScheduleId, updatedEntries)) {
         // Fetch the potentially sorted schedule from the "DB" to ensure consistency
        const latestScheduleFromDb = getStudentSchedule(user.weeklyScheduleId);
        if (latestScheduleFromDb) {
            setSchedule(latestScheduleFromDb);
        }
      } else {
          // Handle error
          console.error("Error saving entry: Schedule not found in mock DB");
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
          <p>Haftalık ders programınız henüz oluşturulmamış veya yüklenemedi. Lütfen ekleyin.</p>
          <Button onClick={handleAddEntry} className="mt-4">
            <PlusCircle className="mr-2 h-4 w-4" /> Program Oluştur / Ders Ekle
          </Button>
        </CardContent>
      </Card>
    );
  }
  
  // Ensure entries are sorted for display after any modification
  const displayEntries = [...schedule.entries].sort((a,b) => allPossibleDays.indexOf(a.dayOfWeek) - allPossibleDays.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime));

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
            scheduleEntries={displayEntries} 
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
