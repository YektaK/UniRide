"use client";

import { useTranslations } from 'next-intl';
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

export default function VehicleFormDialog({ isOpen, onClose, onSave, vehicle }: VehicleFormDialogProps) {
  const t = useTranslations('component.adminVehicleForm');
  const tc = useTranslations('common');

  const vehicleFormSchema = z.object({
    id: z.string().optional(),
    name: z.string().min(2, { message: t('nameMinError') }),
    type: z.enum(["minibus", "bus", "van"], { required_error: t('typeRequired') }),
    plateNumber: z.string().optional(),
    wheelchairCapacity: z.coerce.number().min(0, { message: t('capacityMinError') }),
    seatingCapacity: z.coerce.number().min(0, { message: t('capacityMinError') }),
    cooldownMinutes: z.number().min(0).max(60).default(10),
    status: z.enum(["active", "inactive", "maintenance"], { required_error: t('statusPlaceholder') }),
  }).refine(
    (data) => data.wheelchairCapacity > 0 || data.seatingCapacity > 0,
    {
      message: t('capacityZeroError'),
      path: ["wheelchairCapacity"],
    }
  );

  type VehicleFormValues = z.infer<typeof vehicleFormSchema>;

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
          <DialogTitle>{vehicle ? t('editTitle') : t('addTitle')}</DialogTitle>
          <DialogDescription>
            {vehicle ? t('editDesc') : t('addDesc')}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('nameLabel')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('namePlaceholder')} {...field} />
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
                  <FormLabel>{t('plateLabel')}</FormLabel>
                  <FormControl>
                    <Input placeholder={t('platePlaceholder')} {...field} />
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
                    <FormLabel>{t('typeLabel')}</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder={t('typePlaceholder')} />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="minibus">{t('typeMinibus')}</SelectItem>
                        <SelectItem value="bus">{t('typeBus')}</SelectItem>
                        <SelectItem value="van">{t('typeVan')}</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">
                      {field.value === "minibus" && t('defaultHint', { sw: 4, so: 5 })}
                      {field.value === "bus" && t('defaultHint', { sw: 8, so: 15 })}
                      {field.value === "van" && t('defaultHint', { sw: 2, so: 3 })}
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
                    <FormLabel>{t('statusLabel')}</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder={t('statusPlaceholder')} />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="active">{t('statusActive')}</SelectItem>
                        <SelectItem value="inactive">{t('statusInactive')}</SelectItem>
                        <SelectItem value="maintenance">{t('statusMaintenance')}</SelectItem>
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
                    <FormLabel>{t('wheelchairCapacityLabel')}</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        min={0}
                        {...field} 
                        onChange={event => field.onChange(+event.target.value)} 
                      />
                    </FormControl>
                    <p className="text-xs text-muted-foreground">{t('wheelchairSubtitle')}</p>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="seatingCapacity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('seatingCapacityLabel')}</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        min={0}
                        {...field} 
                        onChange={event => field.onChange(+event.target.value)} 
                      />
                    </FormControl>
                    <p className="text-xs text-muted-foreground">{t('seatingSubtitle')}</p>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Capacity Validation Error */}
            {hasCapacityError && (
              <div className="flex items-center gap-2 text-sm text-red-500 bg-red-50 p-2 rounded">
                <AlertCircle className="h-4 w-4" />
                <span>{t('capacityZeroError')}</span>
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
                    {t('cooldownLabel')}
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
                        <span className="text-xs text-muted-foreground">{t('cooldownMin')}</span>
                        <span className="text-sm font-medium bg-primary/10 text-primary px-2 py-1 rounded">
                          {t('cooldownValue', { value: field.value })}
                        </span>
                        <span className="text-xs text-muted-foreground">{t('cooldownMax')}</span>
                      </div>
                    </div>
                  </FormControl>
                  <p className="text-xs text-muted-foreground">
                    {t('cooldownDesc', { default: 10 })}
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                {tc('cancel')}
              </Button>
              <Button type="submit" disabled={hasCapacityError}>
                {tc('save')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
