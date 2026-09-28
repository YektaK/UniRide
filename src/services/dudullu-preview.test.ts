import { describe, expect, it } from "vitest";

import { buildDudulluPreview } from "./dudullu-preview";
import type {
  MatrixSnapshot,
  PreviewDemand,
  PreviewJobInput,
  PreviewOptimizationResult,
  PreviewRoute,
} from "./dudullu-preview";

const SERVICE_DATE = "2026-08-26";
const DEPOT = "D.Kampus";

const arc = (origin_code: string, destination_code: string, duration_minutes: number) => ({
  origin_code,
  destination_code,
  duration_minutes,
});

const baseMatrix: MatrixSnapshot = {
  id: "time-matrix-2026-08-26",
  version: "v1",
  sha256: "a".repeat(64),
  source: "supabase",
  arcs: [
    arc(DEPOT, "H1", 5),
    arc("H1", DEPOT, 6),
    arc(DEPOT, "H2", 4),
    arc("H2", DEPOT, 7),
  ],
};

function demand(
  occurrenceId: string,
  locationCode = "H1",
  direction: PreviewDemand["direction"] = "pickup",
  anchorMinutes = 600,
  disabilityType: PreviewDemand["disabilityType"] = "So",
): PreviewDemand {
  return {
    occurrenceId,
    studentId: occurrenceId,
    locationCode,
    campusCode: DEPOT,
    serviceDate: SERVICE_DATE,
    direction,
    source: "schedule",
    admission: "confirmed",
    classBoundaryMinutes: 570,
    waveKey: `${SERVICE_DATE}|${direction}|09:00|9-10`,
    anchorGroupKey: `${SERVICE_DATE}|${direction}|${anchorMinutes}`,
    anchorMinutes,
    hardDeadlineMinutes: direction === "pickup" ? anchorMinutes : undefined,
    hardReadyMinutes: direction === "dropoff" ? anchorMinutes : undefined,
    flexibilityMinutes: 0,
    emergencyException: false,
    disabilityType,
  };
}

function route(
  routeDetails: PreviewRoute["route_details"],
  studentIds: readonly string[],
  totalDuration = routeDetails.reduce((sum, step) => sum + step.duration, 0),
): PreviewRoute {
  return {
    vehicle_id: "V1",
    route_details: routeDetails,
    total_duration_minutes: totalDuration,
    total_distance_km: 1,
    sw_count: 0,
    so_count: studentIds.length,
    student_ids: studentIds,
  };
}

function result(
  routes: readonly PreviewRoute[],
  options: Partial<PreviewOptimizationResult> = {},
): PreviewOptimizationResult {
  return {
    success: true,
    routes,
    total_duration_minutes: routes.reduce((sum, item) => sum + item.total_duration_minutes, 0),
    feasibility_certificate: { is_feasible: true },
    ...options,
  };
}

function job(
  demands: readonly PreviewDemand[],
  routeDetails: PreviewRoute["route_details"],
  options: {
    direction?: PreviewDemand["direction"];
    anchorMinutes?: number;
    routeStudentIds?: readonly string[];
    result?: PreviewOptimizationResult;
    nodeNames?: readonly string[];
  } = {},
): PreviewJobInput {
  const direction = options.direction ?? demands[0]?.direction ?? "pickup";
  const anchorMinutes = options.anchorMinutes ?? demands[0]?.anchorMinutes ?? 600;
  const nodeNames = options.nodeNames ?? demands.map((item) => item.occurrenceId);
  const nodeToLocation = new Map<string, string>([[DEPOT, DEPOT]]);
  const nodeToOccurrence = new Map<string, string>();

  demands.forEach((item, index) => {
    const node = nodeNames[index] ?? item.occurrenceId;
    nodeToLocation.set(node, item.locationCode);
    nodeToOccurrence.set(node, item.occurrenceId);
  });

  const routeStudentIds = options.routeStudentIds ?? demands.map((item) => item.occurrenceId);
  return {
    id: `${direction}-${anchorMinutes}`,
    serviceDate: SERVICE_DATE,
    direction,
    anchorMinutes,
    demands,
    nodeToLocation,
    nodeToOccurrence,
    result: options.result ?? result([route(routeDetails, routeStudentIds)]),
  };
}

function build(
  demands: readonly PreviewDemand[],
  jobs: readonly PreviewJobInput[],
  matrix: MatrixSnapshot = baseMatrix,
) {
  return buildDudulluPreview({
    serviceDate: SERVICE_DATE,
    demands,
    vehicles: [],
    matrix,
    jobs,
  });
}

const normalRoute = (node = "H1", outbound = 5, inbound = 6) => [
  { location1: DEPOT, location2: node, duration: outbound, distance: 1 },
  { location1: node, location2: DEPOT, duration: inbound, distance: 1 },
];

describe("buildDudulluPreview", () => {
  it("keeps distinct exact anchors as separate jobs even within one wave", () => {
    const first = demand("occ-1", "H1", "pickup", 540);
    const second = demand("occ-2", "H2", "pickup", 570);

    const preview = build(
      [first, second],
      [
        job([first], normalRoute("occ-1"), { anchorMinutes: 540 }),
        job([second], normalRoute("occ-2", 4, 7), { anchorMinutes: 570 }),
      ],
    );

    expect(preview.status).toBe("preview_ready");
    expect(preview.jobs.map((item) => item.anchorMinutes)).toEqual([540, 570]);
    expect(preview.routeIntervals).toHaveLength(2);
  });

  it("covers duplicate physical homes with distinct occurrence nodes and a zero-minute self arc", () => {
    const first = demand("occ-1", "H1");
    const second = demand("occ-2", "H1");
    const details = [
      { location1: DEPOT, location2: "H1#occ-1", duration: 5, distance: 1 },
      { location1: "H1#occ-1", location2: "H1#occ-2", duration: 0, distance: 0 },
      { location1: "H1#occ-2", location2: DEPOT, duration: 6, distance: 1 },
    ];

    const preview = build(
      [first, second],
      [
        job([first, second], details, {
          nodeNames: ["H1#occ-1", "H1#occ-2"],
        }),
      ],
    );

    expect(preview.status).toBe("preview_ready");
    expect(preview.routeIntervals[0]?.occurrenceIds).toEqual(["occ-1", "occ-2"]);
  });

  it("blocks a missing or mutated directed matrix arc", () => {
    const item = demand("occ-1");
    const mutated = {
      ...baseMatrix,
      arcs: [arc(DEPOT, "H1", 5), arc("H1", DEPOT, 6.5)],
    };

    const preview = build(
      [item],
      [job([item], normalRoute("occ-1"))],
      mutated,
    );

    expect(preview.status).toBe("blocked_data");
    expect(preview.reasonCodes).toContain("MATRIX_ARC_MISMATCH");
  });

  it.each([
    undefined,
    { is_feasible: false },
  ])("requires a positive feasibility certificate (%s)", (certificate) => {
    const item = demand("occ-1");
    const preview = build(
      [item],
      [
        job([item], normalRoute("occ-1"), {
          result: result([route(normalRoute("occ-1"), [item.occurrenceId])], {
            feasibility_certificate: certificate,
          }),
        }),
      ],
    );

    expect(preview.status).toBe("blocked_data");
    expect(preview.reasonCodes).toContain("CERTIFICATE_INVALID");
  });

  it("rejects duplicate and missing occurrence coverage", () => {
    const first = demand("occ-1", "H1");
    const second = demand("occ-2", "H2");
    const duplicate = build(
      [first],
      [
        job([first], normalRoute("occ-1")),
        job([first], normalRoute("occ-1")),
      ],
    );
    const missing = build(
      [first, second],
      [job([first], normalRoute("occ-1"))],
    );

    expect(duplicate.reasonCodes).toContain("DUPLICATE_OCCURRENCE_COVERAGE");
    expect(missing.reasonCodes).toContain("MISSING_OCCURRENCE_COVERAGE");
  });

  it("rejects a wrong route total and an omitted closing depot arc", () => {
    const item = demand("occ-1");
    const wrongTotal = build(
      [item],
      [
        job([item], normalRoute("occ-1"), {
          result: result([route(normalRoute("occ-1"), [item.occurrenceId], 99)]),
        }),
      ],
    );
    const omittedClosingArc = build(
      [item],
      [job([item], [{ location1: DEPOT, location2: "occ-1", duration: 5, distance: 1 }])],
    );

    expect(wrongTotal.reasonCodes).toContain("ROUTE_TOTAL_MISMATCH");
    expect(omittedClosingArc.reasonCodes).toContain("CLOSING_DEPOT_ARC_MISSING");
  });

  it("calculates pickup backward from the hard deadline and dropoff forward from hard ready", () => {
    const pickup = demand("pickup-1", "H1", "pickup", 600);
    const dropoff = demand("dropoff-1", "H1", "dropoff", 900);
    const preview = build(
      [pickup, dropoff],
      [
        job([pickup], normalRoute("pickup-1"), { anchorMinutes: 600 }),
        job([dropoff], normalRoute("dropoff-1"), {
          direction: "dropoff",
          anchorMinutes: 900,
        }),
      ],
    );

    expect(preview.status).toBe("preview_ready");
    expect(preview.routeIntervals.map(({ startMinutes, endMinutes }) => [startMinutes, endMinutes])).toEqual([
      [589, 600],
      [900, 911],
    ]);
    expect(preview.hourlyDemand["09:00"]).toEqual({
      pickup: { Sw: 0, So: 1 },
      dropoff: { Sw: 0, So: 1 },
    });
  });

  it("checks the closing home-to-depot arc for dropoff as well as pickup", () => {
    const item = demand("dropoff-1", "H1", "dropoff", 900);
    const matrix: MatrixSnapshot = {
      ...baseMatrix,
      arcs: [arc(DEPOT, "H1", 5), arc("H1", DEPOT, 6.5)],
    };
    const preview = build(
      [item],
      [job([item], normalRoute("dropoff-1"), {
        direction: "dropoff",
        anchorMinutes: 900,
      })],
      matrix,
    );

    expect(preview.reasonCodes).toContain("MATRIX_ARC_MISMATCH");
  });

  it("uses unrounded source durations for timing while comparing responses at two decimals", () => {
    const item = demand("occ-1", "H1", "pickup", 600);
    const matrix: MatrixSnapshot = {
      ...baseMatrix,
      arcs: [arc(DEPOT, "H1", 5.234), arc("H1", DEPOT, 6.753)],
    };
    const responseDetails = [
      { location1: DEPOT, location2: "occ-1", duration: 5.23, distance: 1 },
      { location1: "occ-1", location2: DEPOT, duration: 6.75, distance: 1 },
    ];
    const preview = build([item], [job([item], responseDetails, {
      result: result([route(responseDetails, [item.occurrenceId], 11.99)]),
    })], matrix);

    expect(preview.status).toBe("preview_ready");
    expect(preview.routeIntervals[0]?.startMinutes).toBeCloseTo(588.013, 6);
  });

  it.each([
    ["pickup", demand("pickup-1", "H1", "pickup", 5), normalRoute("pickup-1"), "ROUTE_OUTSIDE_SERVICE_DAY"],
    ["dropoff", demand("dropoff-1", "H1", "dropoff", 1_435), normalRoute("dropoff-1"), "ROUTE_OUTSIDE_SERVICE_DAY"],
  ] as const)("rejects %s intervals outside the service day without clamping", (_label, item, details, code) => {
    const preview = build([item], [job([item], details, {
      direction: item.direction,
      anchorMinutes: item.anchorMinutes,
    })]);

    expect(preview.status).toBe("blocked_data");
    expect(preview.reasonCodes).toContain(code);
  });
});
