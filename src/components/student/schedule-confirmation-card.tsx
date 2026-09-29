"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { BellRing, CalendarClock, CheckCircle, Edit3, Loader2, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { getSupabaseClient } from "@/lib/supabase";

type Direction = "pickup" | "dropoff";
type LegDecision = "pending" | "confirmed" | "cancelled";
interface LegView {
  decision: LegDecision;
  admission: string;
}
interface LegStateResponse {
  legs: Record<Direction, LegView>;
  legacyBlocker: boolean;
}
type BusyTarget = Direction | "change" | null;

interface ScheduleConfirmationCardProps {
  studentName: string;
  pickupTime: string;
  dropoffTime: string;
  notificationMessage: string;
  relevantDate: string;
  rideDate: string;
  hasRide?: boolean;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = getSupabaseClient();
  const { data: { session } } = await supabase.auth.getSession();
  return {
    "Content-Type": "application/json",
    ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
  };
}

export default function ScheduleConfirmationCard({
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
  const [legs, setLegs] = useState<Record<Direction, LegView> | null>(null);
  const [legacyBlocker, setLegacyBlocker] = useState(false);
  const [busyTarget, setBusyTarget] = useState<BusyTarget>(null);
  const [loadError, setLoadError] = useState(false);

  const loadState = useCallback(async () => {
    if (!user?.id) return;
    try {
      const response = await fetch(`/api/ride-confirmation?date=${rideDate}`, {
        headers: await getAuthHeaders(),
      });
      if (!response.ok) throw new Error("Request failed");
      const data = await response.json() as LegStateResponse;
      setLoadError(false);
      setLegs(data.legs);
      setLegacyBlocker(data.legacyBlocker);
    } catch {
      setLoadError(true);
    }
  }, [rideDate, user?.id]);

  useEffect(() => {
    // The state updates in loadState happen only after the authenticated GET resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadState();
  }, [loadState]);

  const handleLegAction = async (direction: Direction, action: "confirm" | "cancel") => {
    if (!user?.id || busyTarget) return;
    setBusyTarget(direction);
    try {
      const response = await fetch("/api/ride-confirmation", {
        method: "POST",
        headers: await getAuthHeaders(),
        body: JSON.stringify({ action, rideDate, direction }),
      });
      if (!response.ok) throw new Error(t("operationFailed"));
      await loadState();
      toast({
        title: action === "confirm" ? t("legConfirmed") : t("legCancelled"),
        variant: action === "cancel" ? "destructive" : "default",
      });
    } catch (error) {
      toast({
        title: tc("error"),
        description: error instanceof Error ? error.message : t("operationFailed"),
        variant: "destructive",
      });
    } finally {
      setBusyTarget(null);
    }
  };

  const handleChangeRequest = async () => {
    if (!user?.id || busyTarget) return;
    setBusyTarget("change");
    try {
      const response = await fetch("/api/ride-confirmation", {
        method: "POST",
        headers: await getAuthHeaders(),
        body: JSON.stringify({ action: "change", rideDate, pickupTime, dropoffTime }),
      });
      if (!response.ok) throw new Error(t("operationFailed"));
      await loadState();
      toast({ title: t("changeRequested") });
    } catch (error) {
      toast({
        title: tc("error"),
        description: error instanceof Error ? error.message : t("operationFailed"),
        variant: "destructive",
      });
    } finally {
      setBusyTarget(null);
    }
  };

  const renderLeg = (direction: Direction, time: string) => {
    const leg = legs?.[direction];
    const label = !legs || loadError
      ? "—"
      : leg?.admission === "pending_admin_approval"
        ? t("pendingAdminReview")
        : leg ? t(leg.decision) : t("pending");
    const disabled = !legs || loadError || busyTarget !== null;

    return (
      <div role="group" aria-label={t(direction)} className="space-y-2 rounded-md border p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="font-medium">{t(direction)}</p>
          <Badge variant={leg?.decision === "cancelled" ? "destructive" : "outline"} aria-live="polite">
            {label}
          </Badge>
        </div>
        <p className="text-primary flex items-center gap-1 text-lg">
          <CalendarClock aria-hidden="true" className="h-5 w-5" />
          <span className="sr-only">{t(direction === "pickup" ? "pickupLabel" : "dropoffLabel")}</span>
          {time}
        </p>
        <div className="flex flex-wrap gap-2">
          {leg?.decision !== "confirmed" && (
            <Button
              onClick={() => void handleLegAction(direction, "confirm")}
              disabled={disabled}
              className="flex-1"
            >
              {busyTarget === direction ? <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle aria-hidden="true" className="mr-2 h-4 w-4" />}
              {t("confirmLeg", { direction: t(direction) })}
            </Button>
          )}
          {leg?.decision !== "cancelled" && (
            <Button
              variant="outline"
              onClick={() => void handleLegAction(direction, "cancel")}
              disabled={disabled}
              className="flex-1"
            >
              {busyTarget === direction ? <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" /> : <XCircle aria-hidden="true" className="mr-2 h-4 w-4" />}
              {t("cancelLeg", { direction: t(direction) })}
            </Button>
          )}
        </div>
      </div>
    );
  };

  return (
    <Card className="bg-accent/10 border-accent shadow-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <BellRing aria-hidden="true" className="h-6 w-6 text-accent" />
          {t("cardTitle", { relevantDate })}
        </CardTitle>
        <CardDescription>{t("defaultDescription", { relevantDate })}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm">{notificationMessage}</p>
        {legacyBlocker && <p role="status" className="text-sm text-yellow-700">{t("legacyBlocker")}</p>}
        {loadError && <p role="alert" className="text-sm text-destructive">{t("stateUnavailable")}</p>}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" aria-busy={!legs && !loadError}>
          {renderLeg("pickup", pickupTime)}
          {renderLeg("dropoff", dropoffTime)}
        </div>
      </CardContent>
      <CardFooter className="flex justify-end">
        <Button
          variant="outline"
          onClick={() => void handleChangeRequest()}
          disabled={!legs || loadError || busyTarget !== null}
          className="w-full sm:w-auto"
        >
          {busyTarget === "change" ? <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" /> : <Edit3 aria-hidden="true" className="mr-2 h-4 w-4" />}
          {t("changeButton")}
        </Button>
      </CardFooter>
    </Card>
  );
}
