
"use client";

import type { Vehicle } from "@/types";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PlusCircle, Bus } from "lucide-react";
import VehicleCard from "@/components/admin/vehicle-card";
import VehicleFormDialog from "@/components/admin/vehicle-form-dialog";

// Mock data for vehicles
const initialVehicles: Vehicle[] = [
  {
    id: "v001",
    name: "Servis Alpha",
    type: "minibus",
    plateNumber: "06 ABC 001",
    wheelchairCapacity: 2,
    seatingCapacity: 10,
    status: "active",
  },
  {
    id: "v002",
    name: "Servis Beta",
    type: "bus",
    plateNumber: "34 XYZ 789",
    wheelchairCapacity: 4,
    seatingCapacity: 25,
    status: "active",
  },
  {
    id: "v003",
    name: "Acil Destek Aracı",
    type: "van",
    wheelchairCapacity: 1,
    seatingCapacity: 3,
    status: "maintenance",
  },
];

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>(initialVehicles);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null);

  const handleAddVehicle = () => {
    setEditingVehicle(null);
    setIsDialogOpen(true);
  };

  const handleEditVehicle = (vehicle: Vehicle) => {
    setEditingVehicle(vehicle);
    setIsDialogOpen(true);
  };

  const handleDeleteVehicle = (vehicleId: string) => {
    setVehicles(vehicles.filter((v) => v.id !== vehicleId));
    // In a real app, call an API to delete
  };

  const handleSaveVehicle = (vehicleData: Vehicle) => {
    if (editingVehicle) {
      setVehicles(
        vehicles.map((v) => (v.id === vehicleData.id ? vehicleData : v))
      );
    } else {
      setVehicles([...vehicles, { ...vehicleData, id: `v${Date.now()}` }]);
    }
    // In a real app, call an API to save
    setIsDialogOpen(false);
    setEditingVehicle(null);
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-2xl flex items-center gap-2"><Bus className="text-primary"/>Araç Yönetimi</CardTitle>
            <CardDescription>
              Mevcut servis araçlarını görüntüleyin, yeni araç ekleyin veya düzenleyin.
            </CardDescription>
          </div>
          <Button onClick={handleAddVehicle}>
            <PlusCircle className="mr-2 h-4 w-4" /> Yeni Araç Ekle
          </Button>
        </CardHeader>
        <CardContent>
          {vehicles.length === 0 ? (
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
