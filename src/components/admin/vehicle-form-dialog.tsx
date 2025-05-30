
"use client";

import type { Vehicle } from "@/types";
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

interface VehicleFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (vehicle: Vehicle) => void;
  vehicle: Vehicle | null;
}

const vehicleFormSchema = z.object({
  id: z.string().optional(),
  name: z.string().min(2, { message: "Araç adı en az 2 karakter olmalıdır." }),
  type: z.enum(["minibus", "bus", "van"], { required_error: "Araç tipi seçilmelidir." }),
  plateNumber: z.string().optional(),
  wheelchairCapacity: z.coerce.number().min(0, { message: "Kapasite 0 veya daha büyük olmalıdır." }),
  seatingCapacity: z.coerce.number().min(0, { message: "Kapasite 0 veya daha büyük olmalıdır." }),
  status: z.enum(["active", "inactive", "maintenance"], { required_error: "Durum seçilmelidir." }),
});

type VehicleFormValues = z.infer<typeof vehicleFormSchema>;

export default function VehicleFormDialog({ isOpen, onClose, onSave, vehicle }: VehicleFormDialogProps) {
  const form = useForm<VehicleFormValues>({
    resolver: zodResolver(vehicleFormSchema),
    defaultValues: vehicle || {
      name: "",
      type: "minibus",
      wheelchairCapacity: 0,
      seatingCapacity: 0,
      status: "active",
    },
  });

  useEffect(() => {
    if (vehicle) {
      form.reset(vehicle);
    } else {
      form.reset({
        name: "",
        type: "minibus",
        plateNumber: "",
        wheelchairCapacity: 0,
        seatingCapacity: 0,
        status: "active",
      });
    }
  }, [vehicle, form, isOpen]);


  const handleSubmit = (data: VehicleFormValues) => {
    onSave(data as Vehicle); // Assuming ID is handled by onSave if new
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{vehicle ? "Aracı Düzenle" : "Yeni Araç Ekle"}</DialogTitle>
          <DialogDescription>
            {vehicle ? "Araç bilgilerini güncelleyin." : "Yeni bir servis aracı için bilgileri girin."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Araç Adı / Tanımı</FormLabel>
                  <FormControl>
                    <Input placeholder="Örn: Servis A, Mavi Minibüs" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="plateNumber"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Plaka Numarası (Opsiyonel)</FormLabel>
                  <FormControl>
                    <Input placeholder="Örn: 06 ABC 123" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-4">
                <FormField
                control={form.control}
                name="type"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Araç Tipi</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                        <SelectTrigger>
                            <SelectValue placeholder="Araç tipi seçin" />
                        </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                        <SelectItem value="minibus">Minibüs</SelectItem>
                        <SelectItem value="bus">Otobüs</SelectItem>
                        <SelectItem value="van">Van</SelectItem>
                        </SelectContent>
                    </Select>
                    <FormMessage />
                    </FormItem>
                )}
                />
                 <FormField
                control={form.control}
                name="status"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Durum</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                        <SelectTrigger>
                            <SelectValue placeholder="Durum seçin" />
                        </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                        <SelectItem value="active">Aktif</SelectItem>
                        <SelectItem value="inactive">Pasif</SelectItem>
                        <SelectItem value="maintenance">Bakımda</SelectItem>
                        </SelectContent>
                    </Select>
                    <FormMessage />
                    </FormItem>
                )}
                />
            </div>
             <div className="grid grid-cols-2 gap-4">
                <FormField
                control={form.control}
                name="wheelchairCapacity"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Tekerlekli Sandalye Kapasitesi</FormLabel>
                    <FormControl>
                        <Input type="number" {...field} onChange={event => field.onChange(+event.target.value)} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
                />
                <FormField
                control={form.control}
                name="seatingCapacity"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Oturma Kapasitesi</FormLabel>
                    <FormControl>
                        <Input type="number" {...field} onChange={event => field.onChange(+event.target.value)} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
                />
            </div>
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
