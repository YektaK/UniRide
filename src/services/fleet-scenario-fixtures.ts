import type { DailyPlanReader } from "@/services/daily-plan-run";
import type { FleetScenarioParams } from "@/services/fleet-scenario-run";
import type { FleetTypeSpec } from "@/services/fleet-scenario-args";

// Shared fakes of the fleet scenario tests: an in-memory read-only Supabase reader (writes are recorded) and a scripted optimizer transport.


export const DATE = "2026-09-30"; // a Wednesday
export const hash = "a".repeat(64);
export const nodes = ["D.Kampus", "Sw1", "So1", "So2"];
export const matrixOf = (duration: number) => ({
  id: `time_matrix:sha256:${hash}`, version: hash, sha256: hash, source: "supabase",
  arcs: nodes.flatMap((a) => nodes.filter((b) => b !== a).map((b) => ({ origin_code: a, destination_code: b, duration_minutes: duration }))),
});
export const matrix = matrixOf(5);

export const large: FleetTypeSpec = { typeId: "large", swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 };
export const sedan: FleetTypeSpec = { typeId: "sedan", swCapacity: 0, soCapacity: 4, cooldownMinutes: 10 };

export function rows() {
  const student = (id: string, code: string, type: "Sw" | "So") => ({
    id, role: "student", location_code: code, disability_type: type, weekly_schedule_id: `sch-${id}`,
  });
  const schedule = (id: string) => ({
    id: `sch-${id}`, user_id: id,
    entries: [{ id: "c1", dayOfWeek: "wednesday", startTime: "09:00", endTime: "10:00", location: "Dudullu" }],
  });
  return {
    users: [student("s-sw", "Sw1", "Sw"), student("s-so1", "So1", "So"), student("s-so2", "So2", "So")],
    weekly_schedules: [schedule("s-sw"), schedule("s-so1"), schedule("s-so2")],
    student_leg_decisions: [], ride_requests: [], vehicles: [{ id: "db-1", wheelchair_capacity: 4, seating_capacity: 10, cooldown_minutes: 10, status: "active" }],
  } as Record<string, unknown[]>;
}

export function reader(data: Record<string, unknown[]>) {
  const tables: string[] = [];
  const writes: string[] = [];
  const from = (table: string) => {
    tables.push(table);
    const query: Record<string, unknown> = {};
    for (const method of ["select", "eq", "in", "or"]) query[method] = () => query;
    for (const method of ["insert", "update", "upsert", "delete"]) query[method] = () => { writes.push(`${table}.${method}`); return query; };
    query.then = (ok: (value: unknown) => unknown, bad: (reason: unknown) => unknown) =>
      Promise.resolve({ data: data[table] ?? [], error: null }).then(ok, bad);
    return query;
  };
  return { client: { from } as unknown as DailyPlanReader, tables, writes };
}

export interface OptimizeBody {
  algorithm: string; direction: "pickup" | "dropoff"; students: Array<{ id: string; disability_type: "Sw" | "So"; location_code: string }>;
  vehicle_types?: Array<{ type_id: string; max_routes?: number; total_capacity?: number }>;
}
export const steps = (locations: string[], d = 5) => {
  const path = ["D.Kampus", ...locations, "D.Kampus"];
  return path.slice(1).map((to, i) => ({ location1: path[i], location2: to, duration: d, distance: 0 }));
};
export const round2 = (x: number) => Math.round(x * 100) / 100;
export const route = (students: OptimizeBody["students"], vehicleId: string, type?: string, d = 5) => ({
  vehicle_id: vehicleId, route_details: steps(students.map((s) => s.location_code), d),
  total_duration_minutes: round2(d * (students.length + 1)), sw_count: students.filter((s) => s.disability_type === "Sw").length,
  so_count: students.filter((s) => s.disability_type === "So").length, student_ids: students.map((s) => s.id),
  ...(type ? { vehicle_type: type } : {}),
});

export type SelectionRequest = {
  waves: Array<{ wave_id: string; options: Array<{ option_id: string; baseline: boolean; routes: Array<{ start: number; end: number; minutes: number; large_ok: boolean; car_ok: boolean }> }> }>;
  max_large: number;
  time_scale?: number; cooldown_large: number; cooldown_car: number;
};

export function transport(options: { selection?: (request: SelectionRequest) => { status: number; body: unknown }; duration?: number } = {}) {
  const d = options.duration ?? 5;
  const calls: Array<{ path: string; body: unknown }> = [];
  const fetch = async (path: string, init?: RequestInit): Promise<Response> => {
    const body = init?.body ? JSON.parse(String(init.body)) : null;
    calls.push({ path, body });
    if (path === "/api/v1/internal/matrix-snapshot") return Response.json(matrixOf(d));
    if (path.endsWith("/v1/optimize")) {
      const request = body as OptimizeBody;
      const all = request.students;
      if (request.algorithm === "ga_split") {
        return Response.json({ success: true, routes: [route(all, "V1", undefined, d)], total_duration_minutes: round2(d * (all.length + 1)), feasibility_certificate: { is_feasible: true } });
      }
      const quota = request.vehicle_types!.find((t) => t.type_id === "large")!.max_routes!;
      const sw = all.filter((s) => s.disability_type === "Sw");
      const so = all.filter((s) => s.disability_type === "So");
      if (quota === 0 && sw.length > 0) {
        return Response.json({ success: false, routes: [], feasibility_certificate: { is_feasible: false } });
      }
      const routes = [...(sw.length ? [route(sw, "H1", "large", d)] : []), ...(so.length ? [route(so, "H2", "sedan", d)] : [])];
      return Response.json({ success: true, routes, total_duration_minutes: round2(routes.reduce((s, r) => s + r.total_duration_minutes, 0)), feasibility_certificate: { is_feasible: true } });
    }
    if (path === "/api/v1/internal/fleet-selection") {
      const scripted = options.selection?.(body as SelectionRequest);
      if (!scripted) return new Response("{}", { status: 503 });
      return Response.json(scripted.body, { status: scripted.status });
    }
    throw new Error("unexpected path");
  };
  return { fetch, calls };
}

export const pickSelection = (optionId: string, labelsFor: (routes: number) => string[]) => (request: SelectionRequest) => ({
  status: 200,
  body: {
    status: "optimal", cars: 1, large_peak: 1, car_minutes: 15, total_minutes: 25,
    selection: Object.fromEntries(request.waves.map((wave) => {
      const option = wave.options.find((o) => o.option_id === optionId)!;
      return [wave.wave_id, { option_id: optionId, option_index: wave.options.indexOf(option), labels: labelsFor(option.routes.length) }];
    })),
    diagnostics: { claim: "minimum cars over the given menus only" }, stats: { random_seed: 20261008, num_workers: 1 },
  },
});

export const params = (overrides: Partial<FleetScenarioParams> = {}): FleetScenarioParams => ({
  serviceDate: DATE, maxRideTimeMinutes: 60, maxTourMinutes: 150, fixedType: large, minimiseType: sedan,
  scenarios: ["A", 1, 2], ...overrides,
});
