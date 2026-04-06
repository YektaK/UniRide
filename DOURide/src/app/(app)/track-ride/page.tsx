
"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Map, Route } from "lucide-react";
import Image from "next/image";

export default function TrackRidePage() {
  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><Route className="text-primary"/>Servis Takibi</CardTitle>
          <CardDescription>
            Aktif servisinizin konumunu harita üzerinden canlı olarak takip edin. Bu özellik yakında kullanıma sunulacaktır.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
            <Map className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Harita gösterimi burada yer alacaktır.</p>
             <Image 
                src="https://placehold.co/600x400.png" 
                alt="Harita Yeri" 
                width={600} 
                height={400} 
                className="mt-4 rounded-md object-cover opacity-50"
                data-ai-hint="map route" 
            />
          </div>
          <p className="text-muted-foreground">
            Şu anda aktif bir servis yolculuğunuz bulunmamaktadır veya bu özellik geliştirme aşamasındadır.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
