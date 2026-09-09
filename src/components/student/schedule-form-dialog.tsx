
"use client";

import { useTranslations } from "next-intl";
import type { ScheduleEntry } from "@/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useEffect } from "react";
import { isDudulluCampus } from "@/services/daily-planning";
import { DUDULLU_CAMPUS } from "@/services/dudullu-campus";

interface ScheduleFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (entryData: Omit<ScheduleEntry, 'id'>, entryId?: string) => void;
  entry: ScheduleEntry | null;
}

const dayOfWeekSchema = z.enum(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]);

const scheduleEntrySchema = z.object({
  dayOfWeek: dayOfWeekSchema,
  courseName: z.string().optional(),
  startTime: z.string().regex(/^([01]\d|2[0-3]):([0-5]\d)$/, { message: "Saat SS:DD formatında olmalıdır." }),
  endTime: z.string().regex(/^([01]\d|2[0-3]):([0-5]\d)$/, { message: "Saat SS:DD formatında olmalıdır." }),
  location: z.enum(["Dudullu", "Çengelköy"], { required_error: "Lütfen bir konum seçin." }),
}).refine(data => data.startTime < data.endTime, {
  message: "Bitiş saati başlangıç saatinden sonra olmalıdır.",
  path: ["endTime"],
});

type ScheduleFormValues = z.infer<typeof scheduleEntrySchema>;

const daysOrder: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const locationOptions: ScheduleFormValues["location"][] = ["Dudullu", "Çengelköy"];

export function normalizeScheduleLocationForEditing(location: ScheduleEntry["location"]): string {
  return location && isDudulluCampus(location) ? DUDULLU_CAMPUS.scheduleLabel : location ?? "";
}

export default function ScheduleFormDialog({ isOpen, onClose, onSave, entry }: ScheduleFormDialogProps) {
  const t = useTranslations("page.student.schedule");
  const form = useForm<ScheduleFormValues>({
    resolver: zodResolver(scheduleEntrySchema),
    defaultValues: {
      dayOfWeek: "monday",
      courseName: "",
      startTime: "",
      endTime: "",
      location: DUDULLU_CAMPUS.scheduleLabel,
    },
  });

  useEffect(() => {
    if (isOpen) {
      if (entry) {
        form.reset({ ...entry, location: normalizeScheduleLocationForEditing(entry.location) as ScheduleFormValues["location"] });
      } else {
        form.reset({
          dayOfWeek: "monday",
          courseName: "",
          startTime: "",
          endTime: "",
          location: DUDULLU_CAMPUS.scheduleLabel,
        });
      }
    }
  }, [entry, form, isOpen]);

  const handleSubmit = (data: ScheduleFormValues) => {
    onSave(data, entry?.id);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{entry ? t("editTitle") : t("addTitle")}</DialogTitle>
          <DialogDescription>
            {t("dialogDescription")}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-4">
            <FormField
              control={form.control}
              name="dayOfWeek"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("dayLabel")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("dayPlaceholder")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {daysOrder.map((day) => (
                        <SelectItem key={day} value={day}>{t(day)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="courseName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("courseLabel")}</FormLabel>
                  <FormControl>
                    <Input placeholder={t("coursePlaceholder")} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="startTime"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("startTimeLabel")}</FormLabel>
                    <FormControl>
                      <Input type="time" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="endTime"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("endTimeLabel")}</FormLabel>
                    <FormControl>
                      <Input type="time" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("locationLabel")}</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("locationPlaceholder")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {locationOptions.map((loc) => (
                        <SelectItem key={loc} value={loc}>{loc}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                {t("cancel")}
              </Button>
              <Button type="submit">{t("save")}</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
