
import type { Vehicle } from "@/types";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Edit, Trash2, Users, Accessibility, Dot } from "lucide-react";

interface VehicleCardProps {
  vehicle: Vehicle;
  onEdit: (vehicle: Vehicle) => void;
  onDelete: (vehicleId: string) => void;
}

const statusMap: Record<Vehicle["status"], { label: string; color: "bg-green-500" | "bg-yellow-500" | "bg-red-500" }> = {
    active: { label: "Aktif", color: "bg-green-500" },
    inactive: { label: "Pasif", color: "bg-red-500" },
    maintenance: { label: "Bakımda", color: "bg-yellow-500" },
};


export default function VehicleCard({ vehicle, onEdit, onDelete }: VehicleCardProps) {
  const statusInfo = statusMap[vehicle.status] || { label: "Bilinmiyor", color: "bg-gray-500"};
  return (
    <Card className="flex flex-col justify-between shadow-md hover:shadow-lg transition-shadow duration-200">
      <CardHeader>
        <div className="flex justify-between items-start">
            <CardTitle className="text-xl">{vehicle.name}</CardTitle>
            <div className="flex items-center space-x-1">
                <Dot className={`h-5 w-5 ${statusInfo.color.replace('bg-', 'text-')}`} />
                <Badge variant={vehicle.status === "active" ? "default" : (vehicle.status === "maintenance" ? "secondary" : "destructive")} 
                       className={`${statusInfo.color} text-white`}>
                  {statusInfo.label}
                </Badge>
            </div>
        </div>
        <CardDescription>{vehicle.plateNumber || "Plaka Yok"} - Tipi: {vehicle.type}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center text-sm text-muted-foreground">
          <Accessibility className="mr-2 h-4 w-4 text-primary" />
          Tekerlekli Sandalye Kapasitesi: {vehicle.wheelchairCapacity}
        </div>
        <div className="flex items-center text-sm text-muted-foreground">
          <Users className="mr-2 h-4 w-4 text-primary" />
          Oturma Kapasitesi: {vehicle.seatingCapacity}
        </div>
      </CardContent>
      <CardFooter className="flex justify-end gap-2 border-t pt-4 mt-auto">
        <Button variant="outline" size="sm" onClick={() => onEdit(vehicle)} aria-label={`Düzenle ${vehicle.name}`}>
          <Edit className="mr-2 h-4 w-4" /> Düzenle
        </Button>
        <Button variant="destructive" size="sm" onClick={() => onDelete(vehicle.id)} aria-label={`Sil ${vehicle.name}`}>
          <Trash2 className="mr-2 h-4 w-4" /> Sil
        </Button>
      </CardFooter>
    </Card>
  );
}
