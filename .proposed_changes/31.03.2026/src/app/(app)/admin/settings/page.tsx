
"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings as SettingsIcon } from "lucide-react"; // Renamed to avoid conflict
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";

export default function AdminSettingsPage() {
  const { toast } = useToast();

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // In a real app, save these settings
    toast({
      title: "Ayarlar Kaydedildi (Simülasyon)",
      description: "Sistem ayarları başarıyla güncellendi.",
    });
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><SettingsIcon className="text-primary"/>Genel Sistem Ayarları</CardTitle>
          <CardDescription>
            Bildirim zamanlamalarını, mesaj şablonlarını ve diğer sistem ayarlarını buradan yapılandırın.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="notificationTime">Bildirim Saati (Örn: 20:00 veya Ziyaretten X saat önce)</Label>
              <Input id="notificationTime" defaultValue="20:00" />
              <p className="text-sm text-muted-foreground">Öğrencilere bir sonraki günün servis planı için bildirim gönderilme zamanı.</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="arrivalNotificationTemplate">Varış Bildirim Şablonu</Label>
              <Textarea id="arrivalNotificationTemplate" defaultValue="Merhaba {studentName}, yarınki dersiniz için tahmini varış saatiniz: {arrivalTime}. Okul konumu: {location}." rows={3}/>
               <p className="text-sm text-muted-foreground">Kullanılabilir değişkenler: {"{studentName}, {arrivalTime}, {location}"}</p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="departureNotificationTemplate">Ayrılış Bildirim Şablonu</Label>
              <Textarea id="departureNotificationTemplate" defaultValue="Merhaba {studentName}, bugünkü dersleriniz sona erdi. Tahmini ayrılış saatiniz: {departureTime}. Alınış konumu: {pickupLocation}." rows={3}/>
              <p className="text-sm text-muted-foreground">Kullanılabilir değişkenler: {"{studentName}, {departureTime}, {pickupLocation}"}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="departureReminderTime">Ayrılış Hatırlatma Zamanı (Örn: 2 saat önce)</Label>
              <Input id="departureReminderTime" defaultValue="2 saat önce" />
              <p className="text-sm text-muted-foreground">Okuldan ayrılış saatinden ne kadar önce hatırlatma yapılacağı.</p>
            </div>
            
            <Button type="submit">Ayarları Kaydet</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
