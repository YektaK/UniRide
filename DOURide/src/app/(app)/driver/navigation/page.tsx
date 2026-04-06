"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { Navigation, Map } from "lucide-react";

export default function DriverNavigationPage() {
    const { user } = useAuth();

    if (!user || user.role !== "driver") {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Erişim Reddedildi</CardTitle>
                </CardHeader>
                <CardContent>
                    <p>Bu sayfayı görüntüleme yetkiniz yok.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            <Card className="shadow-lg">
                <CardHeader>
                    <CardTitle className="text-2xl flex items-center gap-2">
                        <Navigation className="text-primary" />
                        Navigasyon
                    </CardTitle>
                    <CardDescription>
                        Aktif göreviniz için rota navigasyonu. Bu özellik yakında kullanıma sunulacaktır.
                    </CardDescription>
                </CardHeader>
                <CardContent className="text-center">
                    <div className="my-6 p-8 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
                        <Map className="h-16 w-16 text-muted-foreground mb-4" />
                        <p className="text-muted-foreground mb-2">
                            Navigasyon haritası burada görünecektir.
                        </p>
                        <p className="text-sm text-muted-foreground">
                            Aktif bir göreviniz olduğunda, optimum rota ve öğrenci konumları harita üzerinde gösterilecektir.
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
