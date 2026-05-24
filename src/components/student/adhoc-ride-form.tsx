
"use client";

import { useTranslations } from "next-intl";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { CalendarIcon, Send, MapPin } from "lucide-react";
import { format, addHours } from "date-fns";
import { tr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { addRideRequest } from "@/lib/database";
import type { RideRequest } from "@/types";

interface AdhocRideFormProps {
  userId: string;
  defaultPickupAddress?: string;
}

const adhocRideFormSchema = z.object({
  rideDate: z.date({ required_error: "Lütfen bir tarih seçin." }),
  pickupTime: z.string().regex(/^([01]\d|2[0-3]):([0-5]\d)$/, { message: "Saat SS:DD formatında olmalıdır." }),
  pickupAddress: z.string().min(5, { message: "Alınış adresi en az 5 karakter olmalıdır." }),
  dropoffAddress: z.string().min(5, { message: "Bırakılış adresi en az 5 karakter olmalıdır." }),
  notes: z.string().optional(),
});

type AdhocRideFormValues = z.infer<typeof adhocRideFormSchema>;

export default function AdhocRideForm({ userId, defaultPickupAddress }: AdhocRideFormProps) {
  const t = useTranslations("page.student.rideForm");
  const { toast } = useToast();
  const form = useForm<AdhocRideFormValues>({
    resolver: zodResolver(adhocRideFormSchema),
    defaultValues: {
      rideDate: undefined,
      pickupTime: "",
      pickupAddress: defaultPickupAddress || "",
      dropoffAddress: t("defaultDropoff"),
      notes: "",
    },
  });

  async function onSubmit(data: AdhocRideFormValues) {
    try {
      const requestedPickupDateTime = new Date(data.rideDate);
      const [hours, minutes] = data.pickupTime.split(":").map(Number);
      requestedPickupDateTime.setHours(hours, minutes, 0, 0);

      const requestedDropoffDateTime = addHours(requestedPickupDateTime, 2);

      const rideRequestPayload: Omit<RideRequest, 'id' | 'createdAt'> = {
        userId,
        type: "adhoc",
        requestedPickupTime: requestedPickupDateTime.toISOString(),
        requestedDropoffTime: requestedDropoffDateTime.toISOString(),
        pickupLocation: { address: data.pickupAddress },
        dropoffLocation: { address: data.dropoffAddress },
        status: "pending_admin_approval",
        notes: data.notes || "",
      };

      await addRideRequest(rideRequestPayload);

      toast({
        title: t("successTitle"),
        description: t("successDesc"),
      });
      form.reset({
        rideDate: undefined,
        pickupTime: "",
        pickupAddress: defaultPickupAddress || "",
        dropoffAddress: t("defaultDropoff"),
        notes: "",
      });
    } catch (error) {
      console.error("Error creating ride request:", error);
      toast({
        title: t("errorTitle"),
        description: t("errorDesc"),
        variant: "destructive",
      });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FormField
            control={form.control}
            name="rideDate"
            render={({ field }) => (
              <FormItem className="flex flex-col">
                <FormLabel>{t("dateLabel")}</FormLabel>
                <Popover>
                  <PopoverTrigger asChild>
                    <FormControl>
                      <Button
                        variant={"outline"}
                        className={cn(
                          "w-full pl-3 text-left font-normal",
                          !field.value && "text-muted-foreground"
                        )}
                      >
                        {field.value ? (
                          format(field.value, "PPP", { locale: tr })
                        ) : (
                          <span>{t("datePlaceholder")}</span>
                        )}
                        <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                      </Button>
                    </FormControl>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={field.value}
                      onSelect={field.onChange}
                      disabled={(date) => date < new Date(new Date().setHours(0, 0, 0, 0))}
                      initialFocus
                      locale={tr}
                    />
                  </PopoverContent>
                </Popover>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="pickupTime"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("pickupTimeLabel")}</FormLabel>
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
          name="pickupAddress"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("pickupAddressLabel")}</FormLabel>
              <FormControl>
                <Input placeholder={t("pickupPlaceholder")} {...field} />
              </FormControl>
              <FormDescription className="flex items-center gap-1">
                <MapPin className="h-4 w-4" /> {t("pickupAddressDesc")}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="dropoffAddress"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("dropoffAddressLabel")}</FormLabel>
              <FormControl>
                <Input placeholder={t("dropoffPlaceholder")} {...field} />
              </FormControl>
              <FormDescription className="flex items-center gap-1">
                <MapPin className="h-4 w-4" /> {t("dropoffAddressDesc")}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("notesLabel")}</FormLabel>
              <FormControl>
                <Textarea placeholder={t("notesPlaceholder")} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full sm:w-auto">
          <Send className="mr-2 h-4 w-4" /> {t("submitButton")}
        </Button>
      </form>
    </Form>
  );
}

