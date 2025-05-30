
"use client";

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

interface ScheduleFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (entryData: Omit<ScheduleEntry, 'id'>, entryId?: string) => void;
  entry: ScheduleEntry | null; // null for new entry, ScheduleEntry object for editing
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

const dayTranslations: Record<ScheduleEntry["dayOfWeek"], string> = {
  monday: "Pazartesi",
  tuesday: "Salı",
  wednesday: "Çarşamba",
  thursday: "Perşembe",
  friday: "Cuma",
  saturday: "Cumartesi",
  sunday: "Pazar",
};

const locationOptions: ScheduleFormValues["location"][] = ["Dudullu", "Çengelköy"];

export default function ScheduleFormDialog({ isOpen, onClose, onSave, entry }: ScheduleFormDialogProps) {
  const form = useForm<ScheduleFormValues>({
    resolver: zodResolver(scheduleEntrySchema),
    defaultValues: {
      dayOfWeek: "monday",
      courseName: "",
      startTime: "",
      endTime: "",
      location: "Dudullu",
    },
  });

  useEffect(() => {
    if (isOpen) {
      if (entry) {
        const validLocation = locationOptions.includes(entry.location as ScheduleFormValues["location"]) ? entry.location : "Dudullu";
        form.reset({...entry, location: validLocation as ScheduleFormValues["location"]});
      } else {
        form.reset({
          dayOfWeek: "monday",
          courseName: "",
          startTime: "",
          endTime: "",
          location: "Dudullu",
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
          <DialogTitle>{entry ? "Ders Girişini Düzenle" : "Yeni Ders Girişi Ekle"}</DialogTitle>
          <DialogDescription>
            Haftalık ders programınıza yeni bir ders veya etkinlik ekleyin/düzenleyin.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-4">
            <FormField
              control={form.control}
              name="dayOfWeek"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Gün</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Gün seçin" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {Object.entries(dayTranslations).map(([value, label]) => (
                        <SelectItem key={value} value={value}>{label}</SelectItem>
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
                  <FormLabel>Ders Adı / Etkinlik (Opsiyonel)</FormLabel>
                  <FormControl>
                    <Input placeholder="Örn: MAT101 Calculus I" {...field} />
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
                    <FormLabel>Başlangıç Saati</FormLabel>
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
                    <FormLabel>Bitiş Saati</FormLabel>
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
                  <FormLabel>Konum</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Konum seçin" />
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
                İptal
              </Button>
              <Button type="submit">Kaydet</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
