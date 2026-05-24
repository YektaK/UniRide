"use client";

import { useTranslations } from "next-intl";
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, Edit3, BellRing, CalendarClock, Clock, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { getSupabaseClient } from "@/lib/supabase";
import { format, parseISO } from "date-fns";
import { tr } from "date-fns/locale";

interface ScheduleConfirmationCardProps {
  studentName: string;
  pickupTime: string;
  dropoffTime: string;
  notificationMessage: string;
  relevantDate: string;
  rideDate?: string;
  hasRide?: boolean;
}

export default function ScheduleConfirmationCard({
  studentName,
  pickupTime,
  dropoffTime,
  notificationMessage,
  relevantDate,
  rideDate,
}: ScheduleConfirmationCardProps) {
  const t = useTranslations("component.scheduleConfirmationCard");
  const tc = useTranslations("common");
  const { toast } = useToast();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [isPastDeadline, setIsPastDeadline] = useState(false);
  const [deadlineTime, setDeadlineTime] = useState<string>("");

  const getAuthHeaders = async (): Promise<Record<string, string>> => {
    const supabase = getSupabaseClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) return { "Content-Type": "application/json" };
    return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${session.access_token}`,
    };
  };

  useEffect(() => {
    const checkStatus = async () => {
      if (!user?.id || !rideDate) return;

      try {
        const headers = await getAuthHeaders();
        const response = await fetch(
          `/api/ride-confirmation?date=${rideDate}`,
          { headers }
        );
        if (response.ok) {
          const data = await response.json();
          if (data.hasExistingRide) {
            setStatus(data.ride.status);
          }
          setIsPastDeadline(data.isPastDeadline);
          if (data.deadline) {
            setDeadlineTime(format(parseISO(data.deadline), "HH:mm", { locale: tr }));
          }
        }
      } catch (error) {
        console.error("Error checking ride status:", error);
      }
    };

    checkStatus();
  }, [user?.id, rideDate]);

  const handleAction = async (action: "confirm" | "cancel" | "change") => {
    if (!user?.id) return;

    setLoading(true);
    try {
      const headers = await getAuthHeaders();
      const response = await fetch("/api/ride-confirmation", {
        method: "POST",
        headers,
        body: JSON.stringify({
          action,
          rideDate: rideDate || getNextWeekday(),
          pickupTime,
          dropoffTime,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || t("operationFailed"));
      }

      setStatus(data.status);
      setIsPastDeadline(data.isPastDeadline);

      toast({
        title: action === "confirm" ? t("rideConfirmed") :
          action === "cancel" ? t("rideCancelled") : t("changeRequested"),
        description: data.message,
        variant: action === "cancel" ? "destructive" : "default",
      });
    } catch (error: any) {
      toast({
        title: tc("error"),
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = () => {
    if (!status) return null;

    const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
      confirmed: { label: t("confirmed"), variant: "default" },
      pending_admin_approval: { label: t("statusPending"), variant: "secondary" },
      cancelled_by_student: { label: t("statusCancelled"), variant: "destructive" },
      pending_student_confirmation: { label: t("statusAwaiting"), variant: "outline" },
    };

    const info = statusMap[status] || { label: status, variant: "outline" as const };
    return <Badge variant={info.variant}>{info.label}</Badge>;
  };

  const getNextWeekday = () => {
    const date = new Date();
    date.setDate(date.getDate() + 1);
    return date.toISOString().split("T")[0];
  };

  const isConfirmed = status === "confirmed";
  const isCancelled = status === "cancelled_by_student";

  return (
    <Card className="bg-accent/10 border-accent shadow-lg">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-xl">
            <BellRing className="h-6 w-6 text-accent" />
            {t("cardTitle", { relevantDate })}
          </CardTitle>
          {getStatusBadge()}
        </div>
        <CardDescription>
          {isPastDeadline ? (
            <span className="text-yellow-600 flex items-center gap-1">
              <Clock className="h-4 w-4" />
              {t("pastDeadline")}
            </span>
          ) : deadlineTime ? (
            <span className="text-muted-foreground">
              {t("deadlineInfo", { deadlineTime })}
            </span>
          ) : (
            t("defaultDescription", { relevantDate })
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm">{notificationMessage}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-3 bg-background/50 rounded-md">
          <div className="font-medium">
            <p className="text-muted-foreground text-xs">{t("pickupLabel")}</p>
            <p className="text-lg text-primary flex items-center gap-1">
              <CalendarClock className="h-5 w-5" />{pickupTime}
            </p>
          </div>
          <div className="font-medium">
            <p className="text-muted-foreground text-xs">{t("dropoffLabel")}</p>
            <p className="text-lg text-primary flex items-center gap-1">
              <CalendarClock className="h-5 w-5" />{dropoffTime}
            </p>
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex flex-col sm:flex-row justify-end gap-2">
        {!isCancelled && (
          <Button
            variant="outline"
            onClick={() => handleAction("cancel")}
            disabled={loading}
            className="w-full sm:w-auto"
          >
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <XCircle className="mr-2 h-4 w-4" />}
            {t("cancelButton")}
          </Button>
        )}
        {!isConfirmed && !isCancelled && (
          <>
            <Button
              variant="outline"
              onClick={() => handleAction("change")}
              disabled={loading}
              className="w-full sm:w-auto"
            >
              <Edit3 className="mr-2 h-4 w-4" /> {t("changeButton")}
            </Button>
            <Button
              onClick={() => handleAction("confirm")}
              disabled={loading}
              className="bg-accent hover:bg-accent/90 text-accent-foreground w-full sm:w-auto"
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
              {t("confirmButton")}
            </Button>
          </>
        )}
        {isCancelled && (
          <Button
            onClick={() => handleAction("confirm")}
            disabled={loading}
            className="bg-accent hover:bg-accent/90 text-accent-foreground w-full sm:w-auto"
          >
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
            {t("reconfirmButton")}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
