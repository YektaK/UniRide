
"use client";

import React, { useState, useEffect } from "react";
import type { WeeklySchedule, ScheduleEntry } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarDays, PlusCircle } from "lucide-react";
import ScheduleDisplay from "@/components/student/schedule-display";
import ScheduleFormDialog from "@/components/student/schedule-form-dialog";
import { getStudentSchedule, updateStudentScheduleEntries, createNewUserSchedule } from "@/lib/database";

const allPossibleDays: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export default function SchedulePage() {
  const { user } = useAuth();
  const [schedule, setSchedule] = useState<WeeklySchedule | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ScheduleEntry | null>(null);

  useEffect(() => {
    const loadSchedule = async () => {
      if (user && user.role === "student" && user.weeklyScheduleId) {
        try {
          let userSchedule = await getStudentSchedule(user.weeklyScheduleId);
          if (!userSchedule) {
            // If schedule doesn't exist, create a new empty schedule
            userSchedule = await createNewUserSchedule(user.id, user.weeklyScheduleId);
          }
          setSchedule(userSchedule || null);
        } catch (error) {
          console.error("Error loading schedule:", error);
          setSchedule(null);
        }
      }
      setIsLoading(false);
    };
    loadSchedule();
  }, [user]);

  const handleAddEntry = () => {
    setEditingEntry(null);
    setIsFormOpen(true);
  };

  const handleEditEntry = (entry: ScheduleEntry) => {
    setEditingEntry(entry);
    setIsFormOpen(true);
  };

  const handleDeleteEntry = async (entryId: string) => {
    if (schedule && user && user.weeklyScheduleId && window.confirm("Bu ders girişini silmek istediğinizden emin misiniz?")) {
        try {
          const updatedEntries = schedule.entries.filter(e => e.id !== entryId);
          // No need to sort here, updateStudentScheduleEntries will handle it.
          const success = await updateStudentScheduleEntries(user.weeklyScheduleId, updatedEntries);
          if (success) {
            // Reload schedule from database to get updated version
            const updatedSchedule = await getStudentSchedule(user.weeklyScheduleId);
            if (updatedSchedule) {
              setSchedule(updatedSchedule);
            }
          } else {
            console.error("Error deleting entry: Failed to update schedule");
          }
        } catch (error) {
          console.error("Error deleting entry:", error);
        }
    }
  };
  
  const handleSaveEntry = async (entryData: Omit<ScheduleEntry, 'id'>, entryId?: string) => {
    if (schedule && user && user.weeklyScheduleId) {
      try {
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
        const success = await updateStudentScheduleEntries(user.weeklyScheduleId, updatedEntries);
        if (success) {
          // Fetch the potentially sorted schedule from the database to ensure consistency
          const latestScheduleFromDb = await getStudentSchedule(user.weeklyScheduleId);
          if (latestScheduleFromDb) {
            setSchedule(latestScheduleFromDb);
          }
        } else {
          console.error("Error saving entry: Failed to update schedule");
        }
      } catch (error) {
        console.error("Error saving entry:", error);
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
