"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { adminApi, DudulluReadinessRequestError } from "@/lib/admin-api";
import type { DudulluReadinessReport } from "@/services/dudullu-readiness";

type ViewState =
  | { kind: "loading" }
  | { kind: "report"; report: DudulluReadinessReport }
  | { kind: "error"; error: "authorization" | "configuration" };

function ReadinessRows({ report }: { report: DudulluReadinessReport }) {
  const t = useTranslations("page.admin.readiness");
  const boolean = (value: boolean) => (value ? t("boolean.yes") : t("boolean.no"));

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>{t("sections.students")}</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          <p>{t("labels.allAccounts")}: {report.students.allAccounts}</p>
          <p>{t("labels.dudulluTarget")}: {report.students.dudulluTarget}</p>
          <p>{t("labels.completeTargetProfiles")}: {report.students.completeTargetProfiles}</p>
          <p>{t("labels.unclassifiedSchedule")}: {report.students.unclassifiedSchedule}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>{t("sections.schedules")}</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          <p>{t("labels.scheduleTotal")}: {report.schedules.total}</p>
          <p>{t("labels.scheduleEmpty")}: {report.schedules.empty}</p>
          <p>{t("labels.scheduleMalformed")}: {report.schedules.malformed}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>{t("sections.fleet")}</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          <p>{t("labels.configuredDrivers")}: {report.fleet.configuredDrivers}</p>
          <p>{t("labels.activeVehicles")}: {report.fleet.activeVehicles}</p>
          <p>{t("labels.usableActiveVehicles")}: {report.fleet.usableActiveVehicles}</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>{t("sections.matrix")}</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          <p>{t("labels.matrixSource")}: {t(`matrixSources.${report.matrix.source}`)}</p>
          <p>{t("labels.matrixLocationCount")}: {report.matrix.matrixLocationCount}</p>
          <p>{t("labels.requiredLocationCount")}: {report.matrix.requiredLocationCount}</p>
          <p>{t("labels.validArcCount")}: {report.matrix.validRequiredDirectedArcCount}</p>
          <p>{t("labels.expectedArcCount")}: {report.matrix.expectedRequiredDirectedArcCount}</p>
        </CardContent>
      </Card>
      <Card className="md:col-span-2">
        <CardHeader><CardTitle>{t("sections.historical")}</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          <p>{t("labels.expectedStudents")}: {report.historicalExpectation.studentCount}</p>
          <p>{t("labels.expectedMatrixNodes")}: {report.historicalExpectation.matrixNodeCount}</p>
          <p>{t("labels.matchesStudents")}: {boolean(report.historicalExpectation.matchesStudentCount)}</p>
          <p>{t("labels.matchesMatrix")}: {boolean(report.historicalExpectation.matchesMatrixNodeCount)}</p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ReadinessPage() {
  const t = useTranslations("page.admin.readiness");
  const [view, setView] = useState<ViewState>({ kind: "loading" });
  const requestInFlight = useRef(false);
  const mounted = useRef(false);

  const load = () => {
    if (requestInFlight.current) return;

    requestInFlight.current = true;
    void Promise.resolve()
      .then(() => adminApi.readiness.getDudullu())
      .then((report) => {
        if (mounted.current) setView({ kind: "report", report });
      })
      .catch((error: unknown) => {
        const kind = error instanceof DudulluReadinessRequestError ? error.kind : "configuration";
        if (mounted.current) setView({ kind: "error", error: kind });
      })
      .finally(() => {
        requestInFlight.current = false;
      });
  };

  useEffect(() => {
    mounted.current = true;
    load();
    return () => { mounted.current = false; };
  }, []);

  const loading = view.kind === "loading";
  const refresh = () => {
    setView({ kind: "loading" });
    load();
  };

  return (
    <div className="space-y-6" aria-live="polite">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <Button onClick={refresh} disabled={loading}>{t("refresh")}</Button>
      </div>

      {loading && <Card><CardContent className="p-6">{t("loading")}</CardContent></Card>}
      {view.kind === "error" && <Card><CardContent className="p-6">{t(`errors.${view.error}`)}</CardContent></Card>}
      {view.kind === "report" && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>{view.report.ready ? t("status.passTitle") : t("status.blockedDataTitle")}</CardTitle>
            </CardHeader>
            {!view.report.ready && (
              <CardContent>
                <ul className="list-disc pl-5">
                  {view.report.reasonCodes.map((code) => <li key={code}>{t(`reasons.${code}`)}</li>)}
                </ul>
              </CardContent>
            )}
          </Card>
          <ReadinessRows report={view.report} />
        </>
      )}
    </div>
  );
}
