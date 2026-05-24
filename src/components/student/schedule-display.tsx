
"use client";

import { useTranslations } from "next-intl";
import type { ScheduleEntry } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Edit, Trash2, Clock, MapPinIcon } from "lucide-react";

interface ScheduleDisplayProps {
  scheduleEntries: ScheduleEntry[];
  onEdit: (entry: ScheduleEntry) => void;
  onDelete: (entryId: string) => void;
}

const daysOrder: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export default function ScheduleDisplay({ scheduleEntries, onEdit, onDelete }: ScheduleDisplayProps) {
  const t = useTranslations("page.student.schedule");
  const groupedEntries = scheduleEntries.reduce((acc, entry) => {
    (acc[entry.dayOfWeek] = acc[entry.dayOfWeek] || []).push(entry);
    return acc;
  }, {} as Record<ScheduleEntry["dayOfWeek"], ScheduleEntry[]>);

  return (
    <div className="space-y-6">
      {daysOrder.map((day) => {
        const entriesForDay = groupedEntries[day]?.sort((a,b) => a.startTime.localeCompare(b.startTime));
        if (!entriesForDay || entriesForDay.length === 0) {
          return null;
        }
        return (
          <Card key={day} className="shadow-md">
            <CardHeader>
              <CardTitle className="text-xl text-primary">{t(day)}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {entriesForDay.map((entry) => (
                <div key={entry.id} className="p-4 border rounded-lg bg-muted/30 hover:bg-muted/60 transition-colors">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold text-lg">{entry.courseName || t("defaultCourseName")}</h4>
                      <p className="text-sm text-muted-foreground flex items-center gap-1">
                        <Clock className="h-4 w-4" /> {entry.startTime} - {entry.endTime}
                      </p>
                      {entry.location && (
                        <p className="text-sm text-muted-foreground flex items-center gap-1">
                          <MapPinIcon className="h-4 w-4" /> {entry.location}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="icon" onClick={() => onEdit(entry)} aria-label={t("editAria", { courseName: entry.courseName || t("defaultCourseName") })}>
                        <Edit className="h-5 w-5 text-blue-600 hover:text-blue-800" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => onDelete(entry.id)} aria-label={t("deleteAria", { courseName: entry.courseName || t("defaultCourseName") })}>
                        <Trash2 className="h-5 w-5 text-red-600 hover:text-red-800" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        );
      })}
      {scheduleEntries.length === 0 && (
        <p className="text-center text-muted-foreground py-8">{t("displayEmpty")}</p>
      )}
    </div>
  );
}
