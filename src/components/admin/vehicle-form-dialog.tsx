"use client";

import type { Vehicle } from "@/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useWatch } from "react-hook-form";
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
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useEffect } from "react";
import { Clock, AlertCircle } from "lucide-react";

interface VehicleFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (vehicle: Vehicle) => void;
  vehicle: Vehicle | null;
}

// Default capacities by vehicle type
const defaultCapacities = {
  minibus: { wheelchairCapacity: 4, seatingCapacity: 5 },
  bus: { wheelchairCapacity: 8, seatingCapacity: 15 },
  van: { wheelchairCapacity: 2, seatingCapacity: 3 },
};

const vehicleFormSchema = z.object({
  id: z.string().optional(),
  name: z.string().min(2, { message: "Araç adı en az 2 karakter olmalıdır." }),
  type: z.enum(["minibus", "bus", "van"], { required_error: "Araç tipi seçilmelidir." }),
  plateNumber: z.string().optional(),
  wheelchairCapacity: z.coerce.number().min(0, { message: "Kapasite 0 veya daha büyük olmalıdır." }),
  seatingCapacity: z.coerce.number().min(0, { message: "Kapasite 0 veya daha büyük olmalıdır." }),
  cooldownMinutes: z.number().min(0).max(60).default(10),
  status: z.enum(["active", "inactive", "maintenance"], { required_error: "Durum seçilmelidir." }),
}).refine(
  (data) => data.wheelchairCapacity > 0 || data.seatingCapacity > 0,
  {
    message: "En az bir kapasite (Sw veya So) 0'dan büyük olmalıdır",
    path: ["wheelchairCapacity"],
  }
);

type VehicleFormValues = z.infer<typeof vehicleFormSchema>;

export default function VehicleFormDialog({ isOpen, onClose, onSave, vehicle }: VehicleFormDialogProps) {
  const form = useForm<VehicleFormValues>(
    {
      resolver: zodResolver(vehicleFormSchema),
      defaultValues: vehicle || {
        name: "",
        type: "minibus",
        plateNumber: "",
        wheelchairCapacity: 4,
        seatingCapacity: 5,
        cooldownMinutes: 10,
        status: "active",
      },
    }
  );

  // Watch type changes to auto-set default capacities for new vehicles
  const watchedType = useWatch({ control: form.control, name: "type" });
  const isNewVehicle = !vehicle;

  useEffect(() => {
    if (isNewVehicle && watchedType) {
      const defaults = defaultCapacities[watchedType];
      form.setValue("wheelchairCapacity", defaults.wheelchairCapacity);
      form.setValue("seatingCapacity", defaults.seatingCapacity);
    }
  }, [watchedType, isNewVehicle, form]);

  useEffect(() => {
    if (vehicle) {
      form.reset({
        id: vehicle.id,
        name: vehicle.name,
        type: vehicle.type,
        plateNumber: vehicle.plateNumber || "",
        wheelchairCapacity: vehicle.wheelchairCapacity,
        seatingCapacity: vehicle.seatingCapacity,
        cooldownMinutes: vehicle.cooldownMinutes ?? 10,
        status: vehicle.status,
      });
    } else {
      form.reset({
        name: "",
        type: "minibus",
        plateNumber: "",
        wheelchairCapacity: 4,
        seatingCapacity: 5,
        cooldownMinutes: 10,
        status: "active",
      });
    }
  }, [vehicle, form, isOpen]);

  const handleSubmit = (data: VehicleFormValues) => {
    onSave(data as Vehicle);
  };

  const wheelchairCapacity = form.watch("wheelchairCapacity");
  const seatingCapacity = form.watch("seatingCapacity");
  const hasCapacityError = wheelchairCapacity <= 0 && seatingCapacity <= 0;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[520px]">
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
                    <Select onValueChange={field.onChange} defaultValue={field.value} value={field.value}>
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
                    <p className="text-xs text-muted-foreground mt-1">
                      {field.value === "minibus" && "Varsayılan: 4 Sw + 5 So"}
                      {field.value === "bus" && "Varsayılan: 8 Sw + 15 So"}
                      {field.value === "van" && "Varsayılan: 2 Sw + 3 So"}
                    </p>
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
                    <Select onValueChange={field.onChange} defaultValue={field.value} value={field.value}>
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
            
            {/* Capacity Fields */}
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="wheelchairCapacity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sw Kapasitesi</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        min={0}
                        {...field} 
                        onChange={event => field.onChange(+event.target.value)} 
                      />
                    </FormControl>
                    <p className="text-xs text-muted-foreground">Tekerlekli sandalye</p>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="seatingCapacity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>So Kapasitesi</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        min={0}
                        {...field} 
                        onChange={event => field.onChange(+event.target.value)} 
                      />
                    </FormControl>
                    <p className="text-xs text-muted-foreground">Tekerlekli sandalye kullanmayan engelli</p>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Capacity Validation Error */}
            {hasCapacityError && (
              <div className="flex items-center gap-2 text-sm text-red-500 bg-red-50 p-2 rounded">
                <AlertCircle className="h-4 w-4" />
                <span>En az bir kapasite 0&apos;dan büyük olmalıdır</span>
              </div>
            )}

            {/* Cooldown Slider */}
            <FormField
              control={form.control}
              name="cooldownMinutes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Dönüş Arası Süre (Cooldown)
                  </FormLabel>
                  <FormControl>
                    <div className="space-y-3">
                      <Slider
                        value={[field.value]}
                        onValueChange={(value) => field.onChange(value[0])}
                        max={60}
                        min={0}
                        step={5}
                        className="w-full"
                      />
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-muted-foreground">0 dk</span>
                        <span className="text-sm font-medium bg-primary/10 text-primary px-2 py-1 rounded">
                          {field.value} dakika
                        </span>
                        <span className="text-xs text-muted-foreground">60 dk</span>
                      </div>
                    </div>
                  </FormControl>
                  <p className="text-xs text-muted-foreground">
                    Pickup ve dropoff rotaları arasındaki bekleme süresi (varsayılan: 10 dk)
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                İptal
              </Button>
              <Button type="submit" disabled={hasCapacityError}>
                Kaydet
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
