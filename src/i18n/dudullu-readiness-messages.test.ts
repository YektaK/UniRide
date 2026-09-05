import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

type MessageValue = string | { [key: string]: MessageValue };
type Messages = { page: { admin: { readiness?: MessageValue } } };

const expectedKeys = [
  "boolean.no", "boolean.yes", "description",
  "errors.authorization", "errors.configuration",
  "labels.activeVehicles", "labels.allAccounts", "labels.completeTargetProfiles",
  "labels.configuredDrivers", "labels.dudulluTarget", "labels.expectedArcCount",
  "labels.expectedMatrixNodes", "labels.expectedStudents", "labels.matrixLocationCount",
  "labels.matrixSource", "labels.matchesMatrix", "labels.matchesStudents",
  "labels.requiredLocationCount", "labels.scheduleEmpty", "labels.scheduleMalformed",
  "labels.scheduleTotal", "labels.unclassifiedSchedule",
  "labels.usableActiveVehicles", "labels.validArcCount", "loading",
  "matrixSources.coordinates", "matrixSources.empty", "matrixSources.supabase",
  "reasons.matrix_incomplete", "reasons.matrix_location_mismatch",
  "reasons.matrix_stale", "reasons.matrix_unavailable",
  "reasons.no_configured_driver", "reasons.no_dudullu_students",
  "reasons.no_usable_active_vehicle", "reasons.schedule_classification_incomplete",
  "reasons.schedule_data_invalid", "reasons.target_profile_incomplete",
  "refresh", "sections.fleet", "sections.historical", "sections.matrix",
  "sections.schedules", "sections.students", "status.blockedConfigTitle",
  "status.blockedDataTitle", "status.passTitle", "title",
].sort();

const enMessages = JSON.parse(
  readFileSync(new URL("../../messages/en.json", import.meta.url), "utf8")
) as Messages;
const trMessages = JSON.parse(
  readFileSync(new URL("../../messages/tr.json", import.meta.url), "utf8")
) as Messages;

const flattenKeys = (value: MessageValue, prefix = ""): string[] =>
  typeof value === "string"
    ? [prefix]
    : Object.entries(value).flatMap(([key, child]) =>
        flattenKeys(child, prefix ? `${prefix}.${key}` : key)
      );

const resolveMessage = (value: MessageValue, key: string): string | undefined =>
  key.split(".").reduce<MessageValue | undefined>(
    (current, segment) =>
      current && typeof current !== "string" ? current[segment] : undefined,
    value
  ) as string | undefined;

describe("Dudullu readiness message catalog contract", () => {
  it.each([
    ["en", enMessages],
    ["tr", trMessages],
  ] as const)("has the exact non-empty readiness keys in %s", (_locale, messages) => {
    const readiness = messages.page.admin.readiness;

    expect(readiness).toBeDefined();
    if (!readiness) return;
    expect(flattenKeys(readiness).sort()).toEqual(expectedKeys);
    for (const key of expectedKeys) {
      expect(resolveMessage(readiness, key)?.trim()).toBeTruthy();
    }
  });
});
