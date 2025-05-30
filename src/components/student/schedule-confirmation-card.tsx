
"use client";

// This component simulates the AI-powered notification for schedule confirmation.
// In a real app, the props would come from the analyzeSchedule GenAI flow.

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Edit3, BellRing, CalendarClock } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ScheduleConfirmationCardProps {
  studentName: string;
  pickupTime: string; // e.g., "08:15"
  dropoffTime: string; // e.g., "17:45"
  notificationMessage: string;
  relevantDate: string; // e.g., "Yarın (15 Mayıs 2024, Çarşamba)"
}

export default function ScheduleConfirmationCard({
  studentName,
  pickupTime,
  dropoffTime,
  notificationMessage,
  relevantDate,
}: ScheduleConfirmationCardProps) {
  const { toast } = useToast();

  const handleConfirm = () => {
    toast({
      title: "Servis Onaylandı",
      description: `${relevantDate} için servisiniz başarıyla onaylandı. Alınış: ${pickupTime}, Bırakılış: ${dropoffTime}.`,
    });
    // Add API call to confirm the ride
  };

  const handleChange = () => {
    toast({
      title: "Değişiklik Talebi",
      description: "Servis saatlerinde değişiklik yapma özelliği yakında eklenecektir. Lütfen yetkililerle iletişime geçin.",
      variant: "default",
    });
    // Navigate to a change request form or open a dialog
  };

  const handleCancel = () => {
    toast({
      title: "Servis İptal Edildi",
      description: `${relevantDate} için servisiniz iptal edildi.`,
      variant: "destructive",
    });
    // Add API call to cancel the ride
  };

  return (
    <Card className="bg-accent/10 border-accent shadow-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <BellRing className="h-6 w-6 text-accent" />
          Servis Planı Onayı: {relevantDate}
        </CardTitle>
        <CardDescription>
          Aşağıda {relevantDate} için önerilen servis saatleriniz bulunmaktadır. Lütfen kontrol edip onaylayın.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm">{notificationMessage}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-3 bg-background/50 rounded-md">
            <div className="font-medium">
                <p className="text-muted-foreground text-xs">Tahmini Alınış Saati:</p>
                <p className="text-lg text-primary flex items-center gap-1"><CalendarClock className="h-5 w-5"/>{pickupTime}</p>
            </div>
            <div className="font-medium">
                <p className="text-muted-foreground text-xs">Tahmini Bırakılış Saati (Eve):</p>
                <p className="text-lg text-primary flex items-center gap-1"><CalendarClock className="h-5 w-5"/>{dropoffTime}</p>
            </div>
        </div>
      </CardContent>
      <CardFooter className="flex flex-col sm:flex-row justify-end gap-2">
        <Button variant="outline" onClick={handleCancel} className="w-full sm:w-auto">
          <XCircle className="mr-2 h-4 w-4" /> İptal Et
        </Button>
        <Button variant="outline" onClick={handleChange} className="w-full sm:w-auto">
          <Edit3 className="mr-2 h-4 w-4" /> Değiştir
        </Button>
        <Button onClick={handleConfirm} className="bg-accent hover:bg-accent/90 text-accent-foreground w-full sm:w-auto">
          <CheckCircle className="mr-2 h-4 w-4" /> Onayla
        </Button>
      </CardFooter>
    </Card>
  );
}
