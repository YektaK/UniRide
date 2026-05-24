
"use client";

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings as SettingsIcon } from "lucide-react"; // Renamed to avoid conflict
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";

export default function AdminSettingsPage() {
  const t = useTranslations('page.admin.settings');
  const tc = useTranslations('common');
  const { toast } = useToast();

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // In a real app, save these settings
    toast({
      title: tc('success'),
      description: tc('success'),
    });
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><SettingsIcon className="text-primary"/>{tc('sidebar.settings')}</CardTitle>
          <CardDescription>
            {tc('sidebar.settings')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="notificationTime">{tc('filter')}</Label>
              <Input id="notificationTime" defaultValue="20:00" />
              <p className="text-sm text-muted-foreground">{t('notificationTime')}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="arrivalNotificationTemplate">{tc('sidebar.settings')}</Label>
              <Textarea id="arrivalNotificationTemplate" defaultValue="Merhaba {studentName}, yarınki dersiniz için tahmini varış saatiniz: {arrivalTime}. Okul konumu: {location}." rows={3}/>
               <p className="text-sm text-muted-foreground">Kullanılabilir değişkenler: {"{studentName}, {arrivalTime}, {location}"}</p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="departureNotificationTemplate">{tc('sidebar.settings')}</Label>
              <Textarea id="departureNotificationTemplate" defaultValue="Merhaba {studentName}, bugünkü dersleriniz sona erdi. Tahmini ayrılış saatiniz: {departureTime}. Alınış konumu: {pickupLocation}." rows={3}/>
              <p className="text-sm text-muted-foreground">Kullanılabilir değişkenler: {"{studentName}, {departureTime}, {pickupLocation}"}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="departureReminderTime">{tc('filter')}</Label>
              <Input id="departureReminderTime" defaultValue="2 saat önce" />
              <p className="text-sm text-muted-foreground">Okuldan ayrılış saatinden ne kadar önce hatırlatma yapılacağı.</p>
            </div>
            
            <Button type="submit">{tc('save')}</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
