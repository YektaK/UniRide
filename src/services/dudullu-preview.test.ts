import { describe, expect, it } from "vitest";

import { buildDudulluPreview } from "./dudullu-preview";
import type {
  MatrixSnapshot,
  PreviewDemand,
  PreviewJobInput,
  PreviewOptimizationResult,
  PreviewRoute,
  PreviewVehicle,
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

function vehicle(
  vehicleId: string,
  swCapacity = 2,
  soCapacity = 2,
  cooldownMinutes = 0,
): PreviewVehicle {
  return { vehicleId, swCapacity, soCapacity, cooldownMinutes };
}

function job(
  demands: readonly PreviewDemand[],
  routeDetails: PreviewRoute["route_details"],
  options: {
    id?: string;
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
    id: options.id ?? `${direction}-${anchorMinutes}`,
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
  options: {
    vehicles?: readonly PreviewVehicle[];
  } = {},
) {
  return buildDudulluPreview({
    serviceDate: SERVICE_DATE,
    demands,
    vehicles: options.vehicles ?? [vehicle("BUS-1")],
    matrix,
    jobs,
  });
}

const normalRoute = (node = "H1", outbound = 5, inbound = 6) => [
  { location1: DEPOT, location2: node, duration: outbound, distance: 1 },
  { location1: node, location2: DEPOT, duration: inbound, distance: 1 },
];

function countedRoute(
  details: PreviewRoute["route_details"],
  studentIds: readonly string[],
  swCount: number,
  soCount: number,
  totalDuration = details.reduce((sum, step) => sum + step.duration, 0),
): PreviewRoute {
  return {
    ...route(details, studentIds, totalDuration),
    sw_count: swCount,
    so_count: soCount,
  };
}

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

  it("assigns a route only when both Sw and So capacities fit", () => {
    const sw = demand("sw-1", "H1", "pickup", 600, "Sw");
    const so = demand("so-1", "H1", "pickup", 600, "So");
    const details = [
      { location1: DEPOT, location2: "H1#sw", duration: 5, distance: 1 },
      { location1: "H1#sw", location2: "H1#so", duration: 0, distance: 0 },
      { location1: "H1#so", location2: DEPOT, duration: 6, distance: 1 },
    ];
    const preview = build(
      [sw, so],
      [job([sw, so], details, {
        nodeNames: ["H1#sw", "H1#so"],
        result: result([countedRoute(details, [sw.occurrenceId, so.occurrenceId], 1, 1)]),
      })],
      baseMatrix,
      { vehicles: [vehicle("BUS-1", 1, 1)] },
    );

    expect(preview.status).toBe("preview_ready");
    expect(preview.assignments).toEqual([
      expect.objectContaining({ physicalVehicleId: "BUS-1", swCount: 1, soCount: 1 }),
    ]);
  });

  it("rejects optimizer load counts that disagree with admitted Sw/So occurrences", () => {
    const sw = demand("sw-1", "H1", "pickup", 600, "Sw");
    const details = normalRoute("sw-1");
    const preview = build(
      [sw],
      [job([sw], details, {
        result: result([countedRoute(details, [sw.occurrenceId], 0, 1)]),
      })],
    );

    expect(preview.status).toBe("blocked_data");
    expect(preview.reasonCodes).toContain("ROUTE_LOAD_MISMATCH");
  });

  it("uses heterogeneous vehicles for incompatible Sw and So routes", () => {
    const sw = demand("sw-1", "H1", "pickup", 600, "Sw");
    const so = demand("so-1", "H2", "pickup", 600, "So");
    const preview = build(
      [sw, so],
      [
        job([sw], normalRoute("sw-1"), {
          id: "sw-job",
          result: result([countedRoute(normalRoute("sw-1"), [sw.occurrenceId], 1, 0)]),
        }),
        job([so], normalRoute("so-1", 4, 7), {
          id: "so-job",
          result: result([countedRoute(normalRoute("so-1", 4, 7), [so.occurrenceId], 0, 1)]),
        }),
      ],
      baseMatrix,
      { vehicles: [vehicle("SW-BUS", 1, 0), vehicle("SO-BUS", 0, 1)] },
    );

    expect(preview.status).toBe("preview_ready");
    expect(new Set(preview.assignments.map((item) => item.physicalVehicleId))).toEqual(
      new Set(["SW-BUS", "SO-BUS"]),
    );
  });

  it("allows exact endpoint reuse but honors a positive cooldown", () => {
    const first = demand("occ-1", "H1", "pickup", 600);
    const second = demand("occ-2", "H2", "pickup", 611);
    const jobs = [
      job([first], normalRoute("occ-1"), { id: "first", anchorMinutes: 600 }),
      job([second], normalRoute("occ-2", 4, 7), { id: "second", anchorMinutes: 611 }),
    ];
    const endpoint = build([first, second], jobs, baseMatrix, {
      vehicles: [vehicle("BUS-1", 2, 2, 0)],
    });
    const cooldown = build([first, second], jobs, baseMatrix, {
      vehicles: [vehicle("BUS-1", 2, 2, 1)],
    });

    expect(endpoint.status).toBe("preview_ready");
    expect(new Set(endpoint.assignments.map((item) => item.physicalVehicleId))).toEqual(new Set(["BUS-1"]));
    expect(cooldown.status).toBe("shortage");
    expect(cooldown.unassignedOccurrenceIds).toEqual([first.occurrenceId, second.occurrenceId]);
  });

  it("reuses one physical vehicle across pickup and dropoff when full intervals do not conflict", () => {
    const pickup = demand("pickup-1", "H1", "pickup", 600);
    const dropoff = demand("dropoff-1", "H1", "dropoff", 900);
    const preview = build(
      [pickup, dropoff],
      [
        job([pickup], normalRoute("pickup-1"), { id: "pickup-job", anchorMinutes: 600 }),
        job([dropoff], normalRoute("dropoff-1"), {
          id: "dropoff-job",
          direction: "dropoff",
          anchorMinutes: 900,
        }),
      ],
      baseMatrix,
      { vehicles: [vehicle("BUS-1", 2, 2, 5)] },
    );

    expect(preview.status).toBe("preview_ready");
    expect(preview.assignments).toHaveLength(2);
    expect(new Set(preview.assignments.map((item) => item.physicalVehicleId))).toEqual(new Set(["BUS-1"]));
    expect(preview.hourlyOccupiedVehicles["09:00"]).toBe(1);
  });

  it("returns shortage rather than claiming fleet feasibility when routes cannot fit", () => {
    const first = demand("occ-1", "H1", "pickup", 600);
    const second = demand("occ-2", "H2", "pickup", 600);
    const preview = build(
      [first, second],
      [
        job([first], normalRoute("occ-1"), { id: "first", anchorMinutes: 600 }),
        job([second], normalRoute("occ-2", 4, 7), { id: "second", anchorMinutes: 600 }),
      ],
      baseMatrix,
      { vehicles: [vehicle("BUS-1", 2, 2, 0)] },
    );

    expect(preview.status).toBe("shortage");
    expect(preview.publishable).toBe(false);
    expect(preview.unassignedOccurrenceIds).toEqual([first.occurrenceId, second.occurrenceId]);
  });

  it("chooses the minimum distinct physical fleet instead of keeping the first fit", () => {
    const first = demand("occ-1", "H1", "pickup", 600);
    const second = demand("occ-2", "H2", "pickup", 700);
    const third = demand("occ-3", "H2", "pickup", 700);
    const secondDetails = [
      { location1: DEPOT, location2: "H2#occ-2", duration: 4, distance: 1 },
      { location1: "H2#occ-2", location2: "H2#occ-3", duration: 0, distance: 0 },
      { location1: "H2#occ-3", location2: DEPOT, duration: 7, distance: 1 },
    ];
    const preview = build(
      [first, second, third],
      [
        job([first], normalRoute("occ-1"), { id: "first", anchorMinutes: 600 }),
        job([second, third], secondDetails, {
          id: "second",
          anchorMinutes: 700,
          nodeNames: ["H2#occ-2", "H2#occ-3"],
          result: result([countedRoute(secondDetails, [second.occurrenceId, third.occurrenceId], 0, 2)]),
        }),
      ],
      baseMatrix,
      { vehicles: [vehicle("A", 2, 1), vehicle("B", 2, 2)] },
    );

    expect(preview.status).toBe("preview_ready");
    expect(new Set(preview.assignments.map((item) => item.physicalVehicleId))).toEqual(new Set(["B"]));
  });

  it("returns indeterminate when the bounded assignment search is exhausted", () => {
    const demands = Array.from({ length: 9 }, (_, index) =>
      demand(`occ-${index + 1}`, `H${index + 1}`, "pickup", 600),
    );
    const matrix: MatrixSnapshot = {
      ...baseMatrix,
      arcs: demands.flatMap((item) => [
        arc(DEPOT, item.locationCode, 5),
        arc(item.locationCode, DEPOT, 6),
      ]),
    };
    const jobs = demands.map((item) =>
      job([item], normalRoute(item.occurrenceId), {
        id: item.occurrenceId,
        anchorMinutes: 600,
      }),
    );
    const preview = build(
      demands,
      jobs,
      matrix,
      { vehicles: Array.from({ length: 8 }, (_, index) => vehicle(`V${index + 1}`, 2, 1)) },
    );

    expect(preview.status).toBe("indeterminate");
    expect(preview.reasonCodes).toContain("ASSIGNMENT_SEARCH_INDETERMINATE");
    expect(preview.unassignedOccurrenceIds).toEqual(demands.map((item) => item.occurrenceId));
  });
});
