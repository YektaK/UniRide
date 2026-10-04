"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, CheckCircle2, ChevronDown, Info, Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { adminApi, DailyPlanRequestError, type DailyPlanErrorKind } from "@/lib/admin-api";
import { cn } from "@/lib/utils";
import {
  buildDailyPlanView,
  type DailyPlanView,
  type PlanRoute,
  type PlanTone,
  type PlanWave,
} from "@/services/daily-plan-view";
import { isRealServiceDate } from "@/services/istanbul-service-date";

type ViewState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; error: DailyPlanErrorKind }
  | { kind: "plan"; plan: DailyPlanView };

type Translate = ReturnType<typeof useTranslations>;

const TONE_CLASSES: Record<PlanTone, string> = {
  success: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
  warning: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
  danger: "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100",
  neutral: "border-border bg-muted text-foreground",
};

function todayInIstanbul(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Istanbul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function PreviewBanner({ plan }: { plan: DailyPlanView }) {
  const t = useTranslations("page.admin.dailyPlan.banner");
  const template = plan.virtualTemplate;
  return (
    <Alert
      role="status"
      data-testid="preview-banner"
      className="border-amber-400 bg-amber-50 text-amber-950 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-50"
    >
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>{plan.hypothetical ? t("title") : t("titlePlain")}</AlertTitle>
      <AlertDescription>
        <p>{t("text")}</p>
        {plan.assumedAdmission && <p>{t("assumedAdmission")}</p>}
        {plan.virtualFleet && template && (
          <p>
            {t("virtualFleet", {
              sw: template.swCapacity,
              so: template.soCapacity,
              cooldown: template.cooldownMinutes,
            })}
          </p>
        )}
      </AlertDescription>
    </Alert>
  );
}

function SummaryCards({ plan }: { plan: DailyPlanView }) {
  const t = useTranslations("page.admin.dailyPlan.cards");
  const { summary } = plan;
  const waves = plan.sections.reduce((sum, section) => sum + section.waves.length, 0);
  const fleet = summary.fleet;

  let difference: { text: string; className: string };
  if (fleet.state === "missing") {
    difference = { text: t("missing", { n: fleet.amount }), className: "text-red-700 dark:text-red-300" };
  } else if (fleet.state === "enough") {
    difference = {
      text: fleet.amount === 0 ? t("enough") : `${t("enough")} — ${t("spare", { n: fleet.amount })}`,
      className: "text-emerald-700 dark:text-emerald-300",
    };
  } else {
    difference = { text: t("differenceUnknown"), className: "text-muted-foreground" };
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card data-testid="card-needed-vehicles">
        <CardHeader className="pb-2">
          <CardDescription>{t("neededVehicles")}</CardDescription>
          <CardTitle className="flex items-center gap-2 text-3xl">
            {summary.neededAtMost && <Badge variant="outline" className="text-sm">{t("atMost")}</Badge>}
            <span data-testid="needed-vehicles-value">{summary.neededVehicles ?? "—"}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm text-muted-foreground">
          {summary.neededVehicles === null && <p>{t("unknown")}</p>}
          {summary.neededAtMost && <p>{t("atMostHint")}</p>}
          {summary.lowerBound !== null && (summary.neededVehicles === null || summary.neededAtMost) && (
            <p>{t("lowerBound", { n: summary.lowerBound })}</p>
          )}
          {summary.peakConcurrentRoutes !== null && <p>{t("peak", { n: summary.peakConcurrentRoutes })}</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("students")}</CardDescription>
          <CardTitle className="text-3xl">{summary.students}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm text-muted-foreground">
          <p>{t("studentsHint", { trips: summary.trips })}</p>
          {summary.invalidStudentRecords > 0 && <p>{t("invalidStudents", { n: summary.invalidStudentRecords })}</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardDescription>{t("routes")}</CardDescription>
          <CardTitle className="text-3xl">{summary.routes}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>{t("routesHint", { waves })}</p>
        </CardContent>
      </Card>
      <Card data-testid="card-fleet">
        <CardHeader className="pb-2">
          <CardDescription>{t("liveFleet")}</CardDescription>
          <CardTitle className="text-3xl">{fleet.liveFleet ?? "—"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p className="text-muted-foreground">{t("difference")}</p>
          <p className={cn("font-medium", difference.className)}>
            {fleet.neededAtMost && fleet.state !== "unknown" ? `${t("atMost")} ` : ""}
            {difference.text}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function RouteCard({ route }: { route: PlanRoute }) {
  const t = useTranslations("page.admin.dailyPlan.route");
  return (
    <div className="rounded-md border p-3" data-testid="route-card">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <p className="font-medium">{t("title", { n: route.number })}</p>
        <p className="text-sm text-muted-foreground">
          {t("timeRange", { start: route.startLabel, end: route.endLabel })} · {t("duration", { n: route.totalMinutes })}
        </p>
      </div>
      <p className="text-sm text-muted-foreground">
        {t("counts", { sw: route.swCount, so: route.soCount })} ·{" "}
        {route.vehicleLabel ? t("vehicle", { vehicle: route.vehicleLabel }) : t("noVehicle")}
      </p>
      <p className="mt-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{t("stops")}</p>
      <ol className="mt-1 space-y-1">
        {route.stops.map((stop) => (
          <li key={stop.order} className="flex items-baseline gap-2 text-sm">
            <span className="w-12 shrink-0 font-mono text-muted-foreground">{stop.arrivalLabel}</span>
            <span>
              {stop.kind === "campus"
                ? stop.order === 0 ? t("campusStart") : t("campusEnd")
                : t("student", { code: stop.code })}
            </span>
            {stop.legMinutes > 0 && (
              <span className="text-xs text-muted-foreground">{t("leg", { n: Math.round(stop.legMinutes) })}</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function WaveSection({ wave }: { wave: PlanWave }) {
  const t = useTranslations("page.admin.dailyPlan.wave");
  return (
    <Card data-testid="wave-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">
          {wave.direction === "pickup"
            ? t("pickupTitle", { time: wave.anchorLabel })
            : t("dropoffTitle", { time: wave.anchorLabel })}
        </CardTitle>
        <CardDescription>
          {t("summary", {
            routes: wave.routeCount,
            students: wave.studentCount,
            sw: wave.swCount,
            so: wave.soCount,
          })}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 lg:grid-cols-2">
        {wave.routes.map((route) => <RouteCard key={route.id} route={route} />)}
      </CardContent>
    </Card>
  );
}

function VehicleSchedule({ plan }: { plan: DailyPlanView }) {
  const t = useTranslations("page.admin.dailyPlan.vehicles");
  const timeline = plan.timeline;
  return (
    <Card data-testid="vehicle-schedule">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent>
        {plan.vehicles.length === 0 || timeline === null ? (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">{t("vehicle")}</TableHead>
                <TableHead>{t("routes")}</TableHead>
                <TableHead className="w-28">{t("busy")}</TableHead>
                <TableHead className="min-w-[260px]">
                  <div className="relative h-4" aria-label={t("timeline")}>
                    {timeline.ticks.map((tick) => (
                      <span
                        key={tick.label}
                        className="absolute -translate-x-1/2 text-[10px] font-normal text-muted-foreground"
                        style={{ left: `${tick.leftPercent}%` }}
                      >
                        {tick.label}
                      </span>
                    ))}
                  </div>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {plan.vehicles.map((vehicle) => (
                <TableRow key={vehicle.label} data-testid="vehicle-row">
                  <TableCell className="font-medium">{vehicle.label}</TableCell>
                  <TableCell>
                    <ul className="space-y-0.5 text-sm">
                      {vehicle.routes.map((slot) => (
                        <li key={slot.routeId}>
                          {t("slot", {
                            start: slot.startLabel,
                            end: slot.endLabel,
                            direction: slot.direction === "pickup" ? t("pickupShort") : t("dropoffShort"),
                            n: slot.routeNumber,
                          })}
                        </li>
                      ))}
                    </ul>
                  </TableCell>
                  <TableCell>{t("minutes", { n: vehicle.busyMinutes })}</TableCell>
                  <TableCell>
                    <div className="relative h-5 rounded bg-muted">
                      {vehicle.routes.map((slot) => (
                        <div
                          key={slot.routeId}
                          title={`${slot.startLabel}–${slot.endLabel}`}
                          className={cn(
                            "absolute top-0 h-5 rounded-sm",
                            slot.direction === "pickup" ? "bg-primary" : "bg-amber-500",
                          )}
                          style={{ left: `${slot.leftPercent}%`, width: `${slot.widthPercent}%` }}
                        />
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function StatusNotes({ plan, t }: { plan: DailyPlanView; t: Translate }) {
  if (plan.reasons.length === 0) return null;
  return (
    <Card data-testid="status-notes">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{t("notes.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm">
          {plan.reasons.map((reason) => (
            <li key={reason.code} className="flex items-start gap-2">
              {reason.severity === "info"
                ? <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />}
              <span>
                {t(`reasons.${reason.messageKey}`)}
                {reason.messageKey === "unknown" ? ` (${reason.code})` : ""}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function Limitations({ t }: { t: Translate }) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen} data-testid="limitations">
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2 px-2">
          <Info className="h-4 w-4" />
          {t("limits.title")}
          <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ul className="ml-6 mt-1 list-disc space-y-1 text-sm text-muted-foreground">
          <li>{t("limits.notOptimal")}</li>
          <li>{t("limits.fixedRoutes")}</li>
          <li>{t("limits.timeModel")}</li>
          <li>{t("limits.noNames")}</li>
        </ul>
      </CollapsibleContent>
    </Collapsible>
  );
}

function PlanBody({ plan, t }: { plan: DailyPlanView; t: Translate }) {
  return (
    <div className="space-y-6">
      <PreviewBanner plan={plan} />
      {!plan.isEmptyDay && (
        <div
          data-testid="status-banner"
          className={cn("rounded-md border px-4 py-3 text-sm font-medium", TONE_CLASSES[plan.summary.tone])}
        >
          <span className="inline-flex items-center gap-2">
            {plan.summary.tone === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            {t(`status.${plan.summary.status}`)}
          </span>
        </div>
      )}
      {plan.isEmptyDay ? (
        <Card data-testid="empty-day">
          <CardHeader>
            <CardTitle>{t("emptyDay.title")}</CardTitle>
            <CardDescription>{t("emptyDay.text")}</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          <SummaryCards plan={plan} />
          {plan.sections.map((section) => (
            <section key={section.direction} className="space-y-3" aria-label={t(`sections.${section.direction}`)}>
              <h2 className="text-xl font-semibold">{t(`sections.${section.direction}`)}</h2>
              {section.waves.map((wave) => <WaveSection key={wave.id} wave={wave} />)}
            </section>
          ))}
          {plan.sections.length > 0 && <VehicleSchedule plan={plan} />}
        </>
      )}
      <StatusNotes plan={plan} t={t} />
    </div>
  );
}

export default function DailyPlanPage() {
  const t = useTranslations("page.admin.dailyPlan");
  const [serviceDate, setServiceDate] = useState<string>(todayInIstanbul);
  const [assumeConfirmed, setAssumeConfirmed] = useState(true);
  const [virtualFleet, setVirtualFleet] = useState(true);
  const [view, setView] = useState<ViewState>({ kind: "idle" });
  const latestRequest = useRef(0);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const loading = view.kind === "loading";
  const validDate = isRealServiceDate(serviceDate);

  const run = () => {
    if (loading || !validDate) return;
    const requestId = latestRequest.current + 1;
    latestRequest.current = requestId;
    setView({ kind: "loading" });
    void Promise.resolve()
      .then(() => adminApi.preview.run(serviceDate, {
        admissionMode: assumeConfirmed ? "assume_confirmed" : "recorded",
        fleetMode: virtualFleet ? "virtual" : "live",
      }))
      .then((response) => {
        if (mounted.current && latestRequest.current === requestId) {
          setView({ kind: "plan", plan: buildDailyPlanView(response) });
        }
      })
      .catch((error: unknown) => {
        if (!mounted.current || latestRequest.current !== requestId) return;
        const kind = error instanceof DailyPlanRequestError ? error.kind : "unavailable";
        setView({ kind: "error", error: kind });
      });
  };

  return (
    <div className="space-y-6" aria-live="polite">
      <div>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-5 p-4 md:flex-row md:flex-wrap md:items-end">
          <div className="space-y-2">
            <Label htmlFor="daily-plan-date">{t("controls.date")}</Label>
            <Input
              id="daily-plan-date"
              type="date"
              value={serviceDate}
              onChange={(event) => setServiceDate(event.target.value)}
              className="w-full md:w-48"
            />
          </div>
          <div className="flex items-start gap-3">
            <Switch
              id="daily-plan-assume"
              checked={assumeConfirmed}
              onCheckedChange={setAssumeConfirmed}
              aria-describedby="daily-plan-assume-hint"
            />
            <div className="space-y-1">
              <Label htmlFor="daily-plan-assume">{t("controls.assumeConfirmed")}</Label>
              <p id="daily-plan-assume-hint" className="max-w-xs text-xs text-muted-foreground">
                {t("controls.assumeConfirmedHint")}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Switch
              id="daily-plan-virtual"
              checked={virtualFleet}
              onCheckedChange={setVirtualFleet}
              aria-describedby="daily-plan-virtual-hint"
            />
            <div className="space-y-1">
              <Label htmlFor="daily-plan-virtual">{t("controls.virtualFleet")}</Label>
              <p id="daily-plan-virtual-hint" className="max-w-xs text-xs text-muted-foreground">
                {virtualFleet ? t("controls.virtualFleetOn") : t("controls.virtualFleetOff")}
              </p>
            </div>
          </div>
          <Button onClick={run} disabled={loading || !validDate} className="w-full md:w-auto">
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {loading ? t("controls.running") : t("controls.run")}
          </Button>
        </CardContent>
      </Card>

      {view.kind === "idle" && (
        <Card><CardContent className="p-6 text-muted-foreground">{t("initial")}</CardContent></Card>
      )}
      {view.kind === "loading" && (
        <Card data-testid="plan-loading">
          <CardContent className="flex items-center gap-3 p-6">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>{t("loading")}</span>
          </CardContent>
        </Card>
      )}
      {view.kind === "error" && (
        <Alert variant="destructive" data-testid="plan-error">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>{t("errors.title")}</AlertTitle>
          <AlertDescription>{t(`errors.${view.error}`)}</AlertDescription>
        </Alert>
      )}
      {view.kind === "plan" && <PlanBody plan={view.plan} t={t} />}

      <Limitations t={t} />
    </div>
  );
}
