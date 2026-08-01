
"use client";

import { useTranslations } from "next-intl";
import type { RideRequest, RideStatus } from "@/types";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ListChecks, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import React, { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { getRideRequests as dbGetRideRequests } from "@/lib/database";

export default function RideHistoryPage() {
  const t = useTranslations("page.rideHistory");
  const tc = useTranslations("common");
  const { user, isLoading } = useAuth();
  const [userRequests, setUserRequests] = useState<RideRequest[]>([]);
  const [isDataLoading, setIsDataLoading] = useState(true);

  const statusDisplayMap: Record<RideStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }> = {
    pending_student_confirmation: { label: tc("status.waitingStudent"), variant: "outline", className: "border-yellow-500 text-yellow-700" },
    confirmed: { label: tc("status.confirmed"), variant: "default", className: "bg-green-600 hover:bg-green-700 text-white" },
    cancelled_by_student: { label: tc("status.youCancelled"), variant: "destructive" },
    cancelled_by_admin: { label: tc("status.adminCancelled"), variant: "destructive", className: "bg-red-700 text-white" },
    in_progress: { label: tc("status.enRoute"), variant: "default", className: "bg-blue-500 hover:bg-blue-600 text-white" },
    completed: { label: tc("status.completedTrip"), variant: "secondary", className: "bg-gray-500 text-white" },
    pending_admin_approval: { label: tc("status.waitingAdmin"), variant: "outline", className: "border-orange-500 text-orange-700" },
  };

  useEffect(() => {
    if (user && !isLoading) {
      const loadRequests = async () => {
        try {
          const allRequests = await dbGetRideRequests({ userId: user.id });
          setUserRequests(allRequests);
        } catch (error) {
          console.error("Error loading ride requests:", error);
          setUserRequests([]);
        } finally {
          setIsDataLoading(false);
        }
      };
      loadRequests();
    } else if (!user && !isLoading) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sync initial loading state once auth resolves (not a data fetch)
      setIsDataLoading(false);
    }
  }, [user, isLoading]);

  if (isLoading || isDataLoading) {
    return <Card><CardHeader><CardTitle>{tc("loading")}</CardTitle></CardHeader><CardContent><p>{t("loading")}</p></CardContent></Card>;
  }

  if (!user || user.role !== "student") {
     return (
      <Card className="shadow-lg border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2"><AlertCircle /> {t("accessDenied")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p>{t("accessDeniedDesc")}</p>
        </CardContent>
      </Card>
     );
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><ListChecks className="text-primary"/>{t("title")}</CardTitle>
          <CardDescription>
            {t("description")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {userRequests.length === 0 ? (
            <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
              <ListChecks className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">{t("empty")}</p>
               <p className="text-sm text-muted-foreground mt-2">{t("emptyHint")}</p>
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("dateCol")}</TableHead>
                    <TableHead>{t("pickupTimeCol")}</TableHead>
                    <TableHead>{t("pickupLocCol")}</TableHead>
                    <TableHead>{t("dropoffLocCol")}</TableHead>
                    <TableHead className="text-center">{t("statusCol")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {userRequests.sort((a,b) => new Date(b.requestedPickupTime).getTime() - new Date(a.requestedPickupTime).getTime() ).map((request) => (
                    <TableRow key={request.id}>
                      <TableCell>
                        {format(new Date(request.requestedPickupTime), "dd MMMM yyyy", { locale: tr })}
                      </TableCell>
                      <TableCell>
                        {format(new Date(request.requestedPickupTime), "HH:mm", { locale: tr })}
                      </TableCell>
                      <TableCell>{request.pickupLocation.address}</TableCell>
                      <TableCell>{request.dropoffLocation.address}</TableCell>
                      <TableCell className="text-center">
                        <Badge 
                          variant={statusDisplayMap[request.status].variant}
                          className={cn("font-semibold", statusDisplayMap[request.status].className)}
                        >
                          {statusDisplayMap[request.status].label}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

    