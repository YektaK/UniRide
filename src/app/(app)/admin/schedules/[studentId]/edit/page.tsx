
"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import type { WeeklySchedule, ScheduleEntry, User } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CalendarDays, PlusCircle, ArrowLeft, AlertCircle } from "lucide-react";
import ScheduleDisplay from "@/components/student/schedule-display";
import ScheduleFormDialog from "@/components/student/schedule-form-dialog";
import { getStudentSchedule, updateStudentScheduleEntries, getUserById, createNewUserSchedule } from "@/lib/database";

const allPossibleDays: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export default function AdminEditStudentSchedulePage() {
  const { user: adminUser, isLoading: authLoading } = useAuth();
  const params = useParams();
  const router = useRouter();
  const studentId = params.studentId as string;

  const [student, setStudent] = useState<User | null>(null);
  const [schedule, setSchedule] = useState<WeeklySchedule | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<ScheduleEntry | null>(null);

  const fetchStudentAndSchedule = useCallback(async () => {
    if (!studentId) return;
    setIsLoading(true);

    try {
      const fetchedStudent = await getUserById(studentId);
      if (!fetchedStudent || fetchedStudent.role !== 'student') {
        setStudent(null);
        setSchedule(null);
        setIsLoading(false);
        return;
      }
      setStudent(fetchedStudent);

      let studentSchedule;
      if (fetchedStudent.weeklyScheduleId) {
        studentSchedule = await getStudentSchedule(fetchedStudent.weeklyScheduleId);
        if (!studentSchedule) {
          // If schedule ID exists but schedule doesn't, create it
          studentSchedule = await createNewUserSchedule(fetchedStudent.id, fetchedStudent.weeklyScheduleId);
        }
      } else {
        // Should not happen if user management ensures students have schedule IDs
        // but as a fallback, create one.
        const newScheduleId = `schedule_admin_create_${Date.now()}`;
        studentSchedule = await createNewUserSchedule(fetchedStudent.id, newScheduleId);
        // Update user with the new schedule ID
        const { updateUser } = await import("@/lib/database");
        await updateUser(fetchedStudent.id, { weeklyScheduleId: newScheduleId });
        setStudent({ ...fetchedStudent, weeklyScheduleId: newScheduleId });
      }
      setSchedule(studentSchedule || null);
    } catch (error) {
      console.error("Error loading student and schedule:", error);
      setStudent(null);
      setSchedule(null);
    } finally {
      setIsLoading(false);
    }
  }, [studentId]);

  useEffect(() => {
    if (adminUser && adminUser.role === 'admin') {
      fetchStudentAndSchedule();
    }
  }, [adminUser, fetchStudentAndSchedule]);

  const handleAddEntry = () => {
    setEditingEntry(null);
    setIsFormOpen(true);
  };

  const handleEditEntry = (entry: ScheduleEntry) => {
    setEditingEntry(entry);
    setIsFormOpen(true);
  };

  const handleDeleteEntry = async (entryId: string) => {
    if (schedule && student?.weeklyScheduleId && window.confirm("Bu ders girişini silmek istediğinizden emin misiniz?")) {
      try {
        const updatedEntries = schedule.entries.filter(e => e.id !== entryId);
        const success = await updateStudentScheduleEntries(student.weeklyScheduleId, updatedEntries);
        if (success) {
          // Reload schedule from database
          const updatedSchedule = await getStudentSchedule(student.weeklyScheduleId);
          if (updatedSchedule) {
            setSchedule(updatedSchedule);
          }
        } else {
          console.error("Error deleting entry: Failed to update schedule.");
        }
      } catch (error) {
        console.error("Error deleting entry:", error);
      }
    }
  };

  const handleSaveEntry = async (entryData: Omit<ScheduleEntry, 'id'>, entryId?: string) => {
    if (schedule && student?.weeklyScheduleId) {
      try {
        let updatedEntries;
        if (entryId) {
          updatedEntries = schedule.entries.map(e => e.id === entryId ? { ...e, ...entryData, id: entryId } : e);
        } else {
          const newEntry: ScheduleEntry = {
            ...entryData,
            id: `se_admin_${Date.now()}${Math.random().toString(36).substring(2, 7)}`
          };
          updatedEntries = [...schedule.entries, newEntry];
        }

        const success = await updateStudentScheduleEntries(student.weeklyScheduleId, updatedEntries);
        if (success) {
          const latestScheduleFromDb = await getStudentSchedule(student.weeklyScheduleId);
          if (latestScheduleFromDb) {
            setSchedule(latestScheduleFromDb);
          }
        } else {
          console.error("Error saving entry: Failed to update schedule.");
        }
      } catch (error) {
        console.error("Error saving entry:", error);
      }
    }
    setIsFormOpen(false);
    setEditingEntry(null);
  };

  if (authLoading || isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Yükleniyor...</CardTitle></CardHeader>
        <CardContent><p>Öğrenci ders programı bilgileri yükleniyor.</p></CardContent>
      </Card>
    );
  }

  if (!adminUser || adminUser.role !== "admin") {
    return (
      <Card className="border-destructive">
        <CardHeader><CardTitle className="text-destructive flex items-center gap-2"><AlertCircle /> Erişim Reddedildi</CardTitle></CardHeader>
        <CardContent><p>Bu sayfayı görüntüleme yetkiniz yok.</p></CardContent>
      </Card>
    );
  }

  if (!student) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Öğrenci Bulunamadı</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Belirtilen ID ile bir öğrenci bulunamadı veya bu ID bir öğrenciye ait değil.</p>
          <Button onClick={() => router.push('/admin/schedules')} className="mt-4">
            <ArrowLeft className="mr-2 h-4 w-4" /> Program Listesine Dön
          </Button>
        </CardContent>
      </Card>
    );
  }
  
  if (!schedule) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{student.name} için Ders Programı Bulunamadı</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Bu öğrencinin haftalık ders programı henüz oluşturulmamış veya yüklenemedi.</p>
          <Button onClick={handleAddEntry} className="mt-4">
            <PlusCircle className="mr-2 h-4 w-4" /> Program Oluştur / Ders Ekle
          </Button>
           <Button variant="outline" onClick={() => router.push('/admin/schedules')} className="mt-4 ml-2">
            <ArrowLeft className="mr-2 h-4 w-4" /> Program Listesine Dön
          </Button>
        </CardContent>
      </Card>
    );
  }
  
  // Ensure entries are sorted for display
  const displayEntries = [...schedule.entries].sort((a,b) => allPossibleDays.indexOf(a.dayOfWeek) - allPossibleDays.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime));

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><CalendarDays className="text-primary"/>{student.name} - Ders Programı</CardTitle>
            <CardDescription>
              {student.name} adlı öğrencinin ders programını görüntüleyin ve düzenleyin.
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push('/admin/schedules')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Geri
            </Button>
            <Button onClick={handleAddEntry}>
                <PlusCircle className="mr-2 h-4 w-4" /> Yeni Ders Ekle
            </Button>
          </div>
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

