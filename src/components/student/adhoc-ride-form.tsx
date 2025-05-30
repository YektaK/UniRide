
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
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

interface AdhocRideFormProps {
  userId: string;
  defaultPickupAddress?: string;
}

const adhocRideFormSchema = z.object({
  rideDate: z.date({ required_error: "Lütfen bir tarih seçin." }),
  pickupTime: z.string().regex(/^([01]\d|2[0-3]):([0-5]\d)$/, { message: "Saat SS:DD formatında olmalıdır." }),
  pickupAddress: z.string().min(5, { message: "Alınış adresi en az 5 karakter olmalıdır." }),
  dropoffAddress: z.string().min(5, { message: "Bırakılış adresi en az 5 karakter olmalıdır." }), // Default to university or allow input
  notes: z.string().optional(),
});

type AdhocRideFormValues = z.infer<typeof adhocRideFormSchema>;

export default function AdhocRideForm({ userId, defaultPickupAddress }: AdhocRideFormProps) {
  const { toast } = useToast();
  const form = useForm<AdhocRideFormValues>({
    resolver: zodResolver(adhocRideFormSchema),
    defaultValues: {
      pickupAddress: defaultPickupAddress || "",
      dropoffAddress: "ODTÜ Kampüsü, Ana Giriş", // Example default
      // rideDate and pickupTime will be empty initially
    },
  });

  function onSubmit(data: AdhocRideFormValues) {
    // Combine date and time for requestedPickupTime
    const requestedPickupDateTime = new Date(data.rideDate);
    const [hours, minutes] = data.pickupTime.split(":").map(Number);
    requestedPickupDateTime.setHours(hours, minutes);

    const rideRequestPayload = {
      userId,
      type: "adhoc",
      requestedPickupTime: requestedPickupDateTime.toISOString(),
      // requestedDropoffTime could be estimated or left for admin
      pickupLocation: { address: data.pickupAddress },
      dropoffLocation: { address: data.dropoffAddress },
      status: "pending_admin_approval",
      notes: data.notes,
      createdAt: new Date().toISOString(),
    };

    console.log("Ad-hoc Ride Request:", rideRequestPayload);
    // In a real app, send this to an API
    toast({
      title: "Servis Talebi Gönderildi",
      description: "Talebiniz başarıyla alındı. Onay durumu için bildirimlerinizi kontrol edin.",
    });
    form.reset();
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
                        disabled={(date) => date < new Date(new Date().setHours(0,0,0,0)) } // Disable past dates
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
                <MapPin className="h-4 w-4"/> Genellikle ev adresiniz. Haritadan seçme özelliği yakında eklenecektir.
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
                <MapPin className="h-4 w-4"/> Genellikle okul veya özel bir konum. Haritadan seçme özelliği yakında eklenecektir.
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
