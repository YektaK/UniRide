
"use client";

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
import { format, addHours } from "date-fns"; // addHours eklendi
import { tr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { addRideRequest } from "@/lib/database";
import type { RideRequest } from "@/types"; // RideRequest tipi import edildi

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
  const { toast } = useToast();
  const form = useForm<AdhocRideFormValues>({
    resolver: zodResolver(adhocRideFormSchema),
    defaultValues: {
      rideDate: undefined,
      pickupTime: "",
      pickupAddress: defaultPickupAddress || "",
      dropoffAddress: "Yıldız Teknik Üniversitesi, Davutpaşa Kampüsü",
      notes: "",
    },
  });

  async function onSubmit(data: AdhocRideFormValues) {
    try {
      const requestedPickupDateTime = new Date(data.rideDate);
      const [hours, minutes] = data.pickupTime.split(":").map(Number);
      requestedPickupDateTime.setHours(hours, minutes, 0, 0); // Saniye ve milisaniyeyi sıfırla

      // Bırakılış saati için basit bir tahmin: Alınıştan 2 saat sonrası (örnek)
      const requestedDropoffDateTime = addHours(requestedPickupDateTime, 2);

      // Omit<RideRequest, 'id' | 'createdAt'> tipine uygun bir nesne oluştur
      const rideRequestPayload: Omit<RideRequest, 'id' | 'createdAt'> = {
        userId,
        type: "adhoc",
        requestedPickupTime: requestedPickupDateTime.toISOString(),
        requestedDropoffTime: requestedDropoffDateTime.toISOString(), // Örnek bırakılış saati
        pickupLocation: { address: data.pickupAddress },
        dropoffLocation: { address: data.dropoffAddress },
        status: "pending_admin_approval",
        notes: data.notes || "", // Notlar boşsa boş string ata
      };

      await addRideRequest(rideRequestPayload); // Supabase'e ekle

      toast({
        title: "Servis Talebi Gönderildi",
        description: "Talebiniz başarıyla alındı. Onay durumu için bildirimlerinizi ve taleplerim sayfasını kontrol edin.",
      });
      form.reset({
        rideDate: undefined,
        pickupTime: "",
        pickupAddress: defaultPickupAddress || "",
        dropoffAddress: "Yıldız Teknik Üniversitesi, Davutpaşa Kampüsü",
        notes: "",
      });
    } catch (error) {
      console.error("Error creating ride request:", error);
      toast({
        title: "Talep Oluşturulamadı",
        description: "Servis talebi oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.",
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
                <FormLabel>Servis Tarihi</FormLabel>
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
                          <span>Tarih seçin</span>
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
                <FormLabel>Alınış Saati</FormLabel>
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
              <FormLabel>Alınış Adresi</FormLabel>
              <FormControl>
                <Input placeholder="Tam alınış adresiniz" {...field} />
              </FormControl>
              <FormDescription className="flex items-center gap-1">
                <MapPin className="h-4 w-4" /> Genellikle ev adresiniz.
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
              <FormLabel>Bırakılış Adresi</FormLabel>
              <FormControl>
                <Input placeholder="Tam bırakılış adresiniz (örn: Üniversite Kampüsü)" {...field} />
              </FormControl>
              <FormDescription className="flex items-center gap-1">
                <MapPin className="h-4 w-4" /> Genellikle okul veya özel bir konum.
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
              <FormLabel>Ek Notlar (Opsiyonel)</FormLabel>
              <FormControl>
                <Textarea placeholder="Sürücüye iletmek istediğiniz özel bir durum veya notunuz varsa..." {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full sm:w-auto">
          <Send className="mr-2 h-4 w-4" /> Talep Gönder
        </Button>
      </form>
    </Form>
  );
}

