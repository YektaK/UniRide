
"use client";

import type { Vehicle } from "@/types";
import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PlusCircle, Bus } from "lucide-react";
import VehicleCard from "@/components/admin/vehicle-card";
import VehicleFormDialog from "@/components/admin/vehicle-form-dialog";
import { adminApi } from "@/lib/admin-api";
import { useToast } from "@/hooks/use-toast";

export default function VehiclesPage() {
  const { toast } = useToast();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null);

  useEffect(() => {
    setIsLoading(true);
    const loadVehicles = async () => {
      try {
        const fetchedVehicles = await adminApi.vehicles.getAll();
        // Convert snake_case to camelCase
        const convertedVehicles = fetchedVehicles.map((v: any) => ({
          id: v.id,
          name: v.name,
          type: v.type,
          plateNumber: v.plate_number,
          wheelchairCapacity: v.wheelchair_capacity,
          seatingCapacity: v.seating_capacity,
          status: v.status,
        }));
        setVehicles(convertedVehicles);
      } catch (error) {
        console.error("Error loading vehicles:", error);
        toast({
          title: "Yükleme Hatası",
          description: "Araçlar yüklenirken bir hata oluştu.",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };
    loadVehicles();
  }, [toast]);

  const handleAddVehicle = () => {
    setEditingVehicle(null);
    setIsDialogOpen(true);
  };

  const handleEditVehicle = (vehicle: Vehicle) => {
    setEditingVehicle(vehicle);
    setIsDialogOpen(true);
  };

  const handleDeleteVehicle = async (vehicleId: string) => {
    if (window.confirm("Bu aracı silmek istediğinizden emin misiniz?")) {
      try {
        await adminApi.vehicles.delete(vehicleId);
        setVehicles(vehicles.filter((v) => v.id !== vehicleId));
        toast({
          title: "Araç Silindi",
          description: "Araç başarıyla silindi.",
        });
      } catch (error) {
        console.error("Error deleting vehicle:", error);
        toast({
          title: "Silme Hatası",
          description: "Araç silinirken bir hata oluştu.",
          variant: "destructive",
        });
      }
    }
  };

  const handleSaveVehicle = async (vehicleData: Vehicle) => {
    try {
      if (editingVehicle) {
        // Update existing vehicle
        const { id, ...updates } = vehicleData;
        await adminApi.vehicles.update(id, updates);
        setVehicles(
          vehicles.map((v) => (v.id === vehicleData.id ? vehicleData : v))
        );
        toast({
          title: "Araç Güncellendi",
          description: `${vehicleData.name} başarıyla güncellendi.`,
        });
      } else {
        // Create new vehicle
        const { id, ...newVehicleData } = vehicleData;
        const createdVehicle = await adminApi.vehicles.create(newVehicleData);
        // Convert response to camelCase
        const convertedVehicle = {
          id: createdVehicle.id,
          name: createdVehicle.name,
          type: createdVehicle.type,
          plateNumber: createdVehicle.plate_number,
          wheelchairCapacity: createdVehicle.wheelchair_capacity,
          seatingCapacity: createdVehicle.seating_capacity,
          status: createdVehicle.status,
        };
        setVehicles([...vehicles, convertedVehicle]);
        toast({
          title: "Araç Eklendi",
          description: `${vehicleData.name} başarıyla eklendi.`,
        });
      }
      setIsDialogOpen(false);
      setEditingVehicle(null);
    } catch (error) {
      console.error("Error saving vehicle:", error);
      toast({
        title: "Kaydetme Hatası",
        description: "Araç kaydedilirken bir hata oluştu.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><Bus className="text-primary" />Araç Yönetimi</CardTitle>
            <CardDescription>
              Mevcut servis araçlarını görüntüleyin, yeni araç ekleyin veya düzenleyin.
            </CardDescription>
          </div>
          <Button onClick={handleAddVehicle}>
            <PlusCircle className="mr-2 h-4 w-4" /> Yeni Araç Ekle
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground text-center py-4">Araçlar yükleniyor...</p>
          ) : vehicles.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">Henüz kayıtlı araç bulunmamaktadır.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {vehicles.map((vehicle) => (
                <VehicleCard
                  key={vehicle.id}
                  vehicle={vehicle}
                  onEdit={handleEditVehicle}
                  onDelete={handleDeleteVehicle}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <VehicleFormDialog
        isOpen={isDialogOpen}
        onClose={() => {
          setIsDialogOpen(false);
          setEditingVehicle(null);
        }}
        onSave={handleSaveVehicle}
        vehicle={editingVehicle}
      />
    </div>
  );
}
