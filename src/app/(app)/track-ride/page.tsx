import { getTranslations } from "next-intl/server";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Map, Route } from "lucide-react";
import Image from "next/image";

export default async function TrackRidePage() {
  const t = await getTranslations("page.trackRide");
  const tc = await getTranslations("common");

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><Route className="text-primary"/>{tc("sidebar.trackRide")}</CardTitle>
          <CardDescription>
            {t("description")}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
            <Map className="h-16 w-16 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">{t("placeholder")}</p>
             <Image 
                src="https://placehold.co/600x400.png" 
                alt={t("mapAlt")} 
                width={600} 
                height={400} 
                className="mt-4 rounded-md object-cover opacity-50"
                data-ai-hint="map route" 
            />
          </div>
          <p className="text-muted-foreground">
            {t("noActiveRide")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
