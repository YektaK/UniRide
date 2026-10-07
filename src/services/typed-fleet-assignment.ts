import type { PreviewRouteInterval } from "./dudullu-preview";

/**
 * Day-level typed assignment of FIXED routes to typed vehicles
 * (docs/designs/HETEROGENEOUS_FLEET_DESIGN.md section 4).
 *
 * Interval convention (same as `assignPhysicalVehicles`): a route occupies its vehicle
 * during [start, end + cooldown(type)); two routes share a vehicle iff
 * `a.end + cooldown <= b.start` or `b.end + cooldown <= a.start`.
 *
 * Objective: the fixed types keep their given counts; the number of vehicles of the
 * (single) `minimise` type is minimised first, then its vehicle-minutes (route
 * duration summed over routes labelled with that type).
 */

export const TYPED_ASSIGNMENT_NODE_BUDGET = 200_000;

export interface TypedFleetType {
  readonly typeId: string;
  readonly swCapacity: number;
  readonly soCapacity: number;
  readonly cooldownMinutes: number;
  readonly role: "fixed" | "minimise";
  /** Required for `fixed`: the number of vehicles of this type. */
  readonly count?: number;
  /** Optional for `minimise`: upper cap on vehicles of this type (unlimited when absent). */
  readonly maxCount?: number;
  /** Physical id prefix; defaults to the upper-cased first letter of typeId. */
  readonly idPrefix?: string;
}

export interface TypedAssignmentInput {
  readonly intervals: readonly PreviewRouteInterval[];
  readonly types: readonly TypedFleetType[];
  /** Node budget per feasibility test (and for the car-minutes refinement). */
  readonly nodeBudget?: number;
  /** Refine the minimum-count witness to minimum minimise-type vehicle-minutes (default true). */
  readonly minimiseMinutes?: boolean;
}

export type TypedAssignmentStatus =
  | "proven"
  | "witness"
  | "indeterminate"
  | "infeasible_for_L"
  | "blocked_data";

export type TypedReasonCode =
  | "FLEET_INVALID"
  | "TYPE_CAPACITY_UNCOVERED"
  | "FIXED_TYPE_TOO_SMALL"
  | "MINIMISE_CAP_EXCEEDED"
  | "FIXED_TYPES_INSUFFICIENT"
  | "ASSIGNMENT_SEARCH_INDETERMINATE"
  | "WITNESS_INVALID";

export interface TypedAssignment extends PreviewRouteInterval {
  readonly physicalVehicleId: string;
  readonly vehicleType: string;
}

export interface MinimiseTypeUsageWindow {
  readonly vehicleId: string;
  readonly firstStartMinutes: number;
  readonly lastEndMinutes: number;
  readonly busyMinutes: number;
  readonly routeCount: number;
  readonly jobIds: readonly string[];
}

export interface TypedAssignmentResult {
  readonly status: TypedAssignmentStatus;
  readonly reasonCodes: readonly TypedReasonCode[];
  /** Vehicles actually used per type. */
  readonly countsByType: Readonly<Record<string, number>>;
  readonly lowerBoundsByType: Readonly<Record<string, number>>;
  readonly minimiseTypeId: string | null;
  /** Minimum number of minimise-type vehicles (exact only when status is "proven"). */
  readonly minimumCount: number | null;
  /** Route minutes on minimise-type vehicles; null when no witness. */
  readonly minimiseMinutes: number | null;
  /** True when the minute total is the proven minimum for `minimumCount`. */
  readonly minimiseMinutesProven: boolean;
  readonly assignments: readonly TypedAssignment[];
  readonly usageWindows: readonly MinimiseTypeUsageWindow[];
  readonly hourlyOccupiedVehiclesByType: Readonly<Record<string, Readonly<Record<string, number>>>>;
  readonly nodes: number;
}

class BudgetExceeded extends Error {}

function fits(type: TypedFleetType, interval: PreviewRouteInterval): boolean {
  return interval.swCount <= type.swCapacity && interval.soCount <= type.soCapacity;
}

function conflicts(cooldown: number, a: PreviewRouteInterval, b: PreviewRouteInterval): boolean {
  return !(a.endMinutes + cooldown <= b.startMinutes || b.endMinutes + cooldown <= a.startMinutes);
}

function validTypes(types: readonly TypedFleetType[]): boolean {
  if (types.length === 0) return false;
  const ids = new Set<string>();
  let minimise = 0;
  for (const type of types) {
    if (type.typeId === "" || ids.has(type.typeId)) return false;
    ids.add(type.typeId);
    const numbers = [type.swCapacity, type.soCapacity, type.cooldownMinutes];
    if (numbers.some((value) => !Number.isFinite(value) || value < 0)) return false;
    if (type.role === "minimise") {
      minimise += 1;
      if (type.maxCount !== undefined && !(Number.isInteger(type.maxCount) && type.maxCount >= 0)) return false;
    } else if (type.role === "fixed") {
      if (type.count === undefined || !Number.isInteger(type.count) || type.count < 0) return false;
    } else return false;
  }
  return minimise <= 1;
}

function validIntervals(intervals: readonly PreviewRouteInterval[]): boolean {
  return intervals.every((item) =>
    [item.startMinutes, item.endMinutes, item.swCount, item.soCount].every(Number.isFinite) &&
    item.endMinutes >= item.startMinutes && item.swCount >= 0 && item.soCount >= 0
  );
}

/** Peak number of simultaneously busy vehicles for a subset (intervals extended by cooldown). */
function peakBusy(items: readonly PreviewRouteInterval[], cooldown: number): number {
  let peak = 0;
  for (const probe of items) {
    let count = 0;
    for (const item of items) {
      if (item.startMinutes <= probe.startMinutes && probe.startMinutes < item.endMinutes + cooldown) count += 1;
    }
    if (count > peak) peak = count;
  }
  return peak;
}

function hourKey(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}

function defaultPrefix(type: TypedFleetType, all: readonly TypedFleetType[]): string {
  if (type.idPrefix !== undefined) return type.idPrefix;
  const short = type.typeId.charAt(0).toUpperCase();
  const clash = all.some((other) => other !== type && other.idPrefix === undefined &&
    other.typeId.charAt(0).toUpperCase() === short);
  return clash ? `${type.typeId}-` : short;
}

/**
 * Independent re-check of a typed witness: capacity per vehicle, cooldown-separated
 * non-overlap per vehicle, and a single type per physical vehicle. Returns violations.
 */
export function verifyTypedAssignment(
  assignments: readonly TypedAssignment[],
  types: readonly TypedFleetType[],
): string[] {
  const problems: string[] = [];
  const typeById = new Map(types.map((type) => [type.typeId, type]));
  const byVehicle = new Map<string, TypedAssignment[]>();
  for (const item of assignments) {
    const type = typeById.get(item.vehicleType);
    if (type === undefined) {
      problems.push(`unknown type ${item.vehicleType}`);
      continue;
    }
    if (!fits(type, item)) problems.push(`route ${item.jobId}#${item.routeIndex} exceeds ${type.typeId} capacity`);
    const list = byVehicle.get(item.physicalVehicleId) ?? [];
    list.push(item);
    byVehicle.set(item.physicalVehicleId, list);
  }
  for (const [vehicleId, list] of byVehicle) {
    if (new Set(list.map((item) => item.vehicleType)).size > 1) problems.push(`${vehicleId} mixes types`);
    const type = typeById.get(list[0].vehicleType);
    if (type === undefined) continue;
    for (let i = 0; i < list.length; i += 1) {
      for (let j = i + 1; j < list.length; j += 1) {
        if (conflicts(type.cooldownMinutes, list[i], list[j])) problems.push(`${vehicleId} overlaps`);
      }
    }
  }
  return problems;
}

export function assignTypedVehicles(input: TypedAssignmentInput): TypedAssignmentResult {
  const { intervals } = input;
  const nodeBudget = input.nodeBudget ?? TYPED_ASSIGNMENT_NODE_BUDGET;
  const empty = (
    status: TypedAssignmentStatus,
    reasonCodes: TypedReasonCode[],
    extra: Partial<TypedAssignmentResult> = {},
  ): TypedAssignmentResult => ({
    status,
    reasonCodes,
    countsByType: {},
    lowerBoundsByType: {},
    minimiseTypeId: input.types.find((type) => type.role === "minimise")?.typeId ?? null,
    minimumCount: null,
    minimiseMinutes: null,
    minimiseMinutesProven: false,
    assignments: [],
    usageWindows: [],
    hourlyOccupiedVehiclesByType: {},
    nodes: 0,
    ...extra,
  });

  if (!validTypes(input.types) || !validIntervals(intervals) || !(nodeBudget >= 1)) {
    return empty("blocked_data", ["FLEET_INVALID"]);
  }
  const minimiseType = input.types.find((type) => type.role === "minimise") ?? null;
  const fixedTypes = input.types.filter((type) => type.role === "fixed");
  const types: readonly TypedFleetType[] = minimiseType === null ? fixedTypes : [minimiseType, ...fixedTypes];
  const eligible = types.map((type) => intervals.map((item) => fits(type, item)));
  if (intervals.some((_, index) => !eligible.some((row) => row[index]))) {
    return empty("blocked_data", ["TYPE_CAPACITY_UNCOVERED"]);
  }
  const order = intervals
    .map((_, index) => index)
    .sort((a, b) =>
      intervals[a].startMinutes - intervals[b].startMinutes ||
      intervals[a].endMinutes - intervals[b].endMinutes ||
      a - b
    );

  // ---- lower bounds -------------------------------------------------------------------
  const fixedTotal = fixedTypes.reduce((sum, type) => sum + (type.count ?? 0), 0);
  const minCooldown = Math.min(...types.map((type) => type.cooldownMinutes));
  const lowerBoundsByType: Record<string, number> = {};
  let infeasibleReason: TypedReasonCode | null = null;
  if (fixedTypes.length === 1) {
    const fixed = fixedTypes[0];
    const fixedIndex = types.indexOf(fixed);
    const onlyFixed = intervals.filter((_, i) => eligible[fixedIndex][i] && (minimiseType === null || !eligible[0][i]));
    const bound = peakBusy(onlyFixed, fixed.cooldownMinutes);
    lowerBoundsByType[fixed.typeId] = bound;
    if (bound > (fixed.count ?? 0)) infeasibleReason = "FIXED_TYPE_TOO_SMALL";
  }
  let lowerBoundMinimise = 0;
  if (minimiseType !== null) {
    const onlyMinimise = intervals.filter((_, i) => eligible[0][i] && fixedTypes.every((_t, t) => !eligible[t + 1][i]));
    const allActive = peakBusy(intervals, minCooldown);
    lowerBoundMinimise = Math.max(0, allActive - fixedTotal, peakBusy(onlyMinimise, minimiseType.cooldownMinutes));
    lowerBoundsByType[minimiseType.typeId] = lowerBoundMinimise;
  } else if (intervals.length > 0 && peakBusy(intervals, minCooldown) > fixedTotal) {
    infeasibleReason ??= "FIXED_TYPES_INSUFFICIENT";
  }
  const maxMinimise = minimiseType === null
    ? 0
    : Math.min(minimiseType.maxCount ?? Number.POSITIVE_INFINITY, eligible[0].filter(Boolean).length);
  if (minimiseType !== null && lowerBoundMinimise > maxMinimise) {
    infeasibleReason ??= minimiseType.maxCount !== undefined && lowerBoundMinimise > minimiseType.maxCount
      ? "MINIMISE_CAP_EXCEEDED"
      : "FIXED_TYPES_INSUFFICIENT";
  }
  if (infeasibleReason !== null) {
    return empty("infeasible_for_L", [infeasibleReason], { lowerBoundsByType });
  }

  // ---- decision search ----------------------------------------------------------------
  let totalNodes = 0;
  const countsFor = (cars: number): number[] =>
    types.map((type, t) => (minimiseType !== null && t === 0 ? cars : type.count ?? 0));

  function busyKey(busy: readonly (readonly number[])[]): string {
    return busy.map((list) => list.join(",")).join("|");
  }

  /** Returns labels indexed by position in `order`, or null when infeasible. Throws on budget. */
  function feasible(counts: readonly number[]): number[] | null {
    let nodes = 0;
    const dead = new Set<string>();
    const labels = new Array<number>(order.length).fill(-1);
    const rec = (k: number, busy: readonly (readonly number[])[]): boolean => {
      if (k === order.length) return true;
      nodes += 1;
      totalNodes += 1;
      if (nodes > nodeBudget) throw new BudgetExceeded();
      const item = intervals[order[k]];
      const t0 = item.startMinutes;
      const live = busy.map((list) => list.filter((until) => until > t0));
      const key = `${k}#${busyKey(live)}`;
      if (dead.has(key)) return false;
      for (let t = 0; t < types.length; t += 1) {
        if (!eligible[t][order[k]] || live[t].length >= counts[t]) continue;
        const until = item.endMinutes + types[t].cooldownMinutes;
        const next = live.map((list, i) => (i === t ? [...list, until].sort((a, b) => a - b) : list));
        labels[k] = t;
        if (rec(k + 1, next)) return true;
      }
      labels[k] = -1;
      dead.add(key);
      return false;
    };
    return rec(0, types.map(() => [])) ? labels : null;
  }

  /** Exact minimum minimise-type minutes for fixed counts; labels of an optimal labelling. */
  function refineMinutes(counts: readonly number[]): number[] | null {
    let nodes = 0;
    const memo = new Map<string, number>();
    const cost = (k: number, t: number): number =>
      minimiseType !== null && t === 0 ? intervals[order[k]].endMinutes - intervals[order[k]].startMinutes : 0;
    const solve = (k: number, busy: readonly (readonly number[])[]): number => {
      if (k === order.length) return 0;
      const item = intervals[order[k]];
      const live = busy.map((list) => list.filter((until) => until > item.startMinutes));
      const key = `${k}#${busyKey(live)}`;
      const cached = memo.get(key);
      if (cached !== undefined) return cached;
      nodes += 1;
      totalNodes += 1;
      if (nodes > nodeBudget) throw new BudgetExceeded();
      let best = Number.POSITIVE_INFINITY;
      for (let t = 0; t < types.length; t += 1) {
        if (!eligible[t][order[k]] || live[t].length >= counts[t]) continue;
        const until = item.endMinutes + types[t].cooldownMinutes;
        const next = live.map((list, i) => (i === t ? [...list, until].sort((a, b) => a - b) : list));
        best = Math.min(best, cost(k, t) + solve(k + 1, next));
      }
      memo.set(key, best);
      return best;
    };
    const total = solve(0, types.map(() => []));
    if (!Number.isFinite(total)) return null;
    const labels: number[] = [];
    let busy: readonly (readonly number[])[] = types.map(() => []);
    for (let k = 0; k < order.length; k += 1) {
      const item = intervals[order[k]];
      const live = busy.map((list) => list.filter((until) => until > item.startMinutes));
      const target = solve(k, busy);
      let chosen = -1;
      for (let t = 0; t < types.length && chosen < 0; t += 1) {
        if (!eligible[t][order[k]] || live[t].length >= counts[t]) continue;
        const until = item.endMinutes + types[t].cooldownMinutes;
        const next = live.map((list, i) => (i === t ? [...list, until].sort((a, b) => a - b) : list));
        if (cost(k, t) + solve(k + 1, next) === target) {
          chosen = t;
          busy = next;
        }
      }
      labels.push(chosen);
    }
    return labels;
  }

  const capacityLimit = minimiseType === null ? 0 : maxMinimise;
  let budgetHit = false;
  let foundCount: number | null = null;
  let foundLabels: number[] | null = null;
  for (let cars = lowerBoundMinimise; cars <= capacityLimit; cars += 1) {
    try {
      const labels = feasible(countsFor(cars));
      if (labels !== null) {
        foundCount = cars;
        foundLabels = labels;
        break;
      }
    } catch (error) {
      if (!(error instanceof BudgetExceeded)) throw error;
      budgetHit = true;
    }
  }
  if (foundLabels === null || foundCount === null) {
    if (budgetHit) {
      return empty("indeterminate", ["ASSIGNMENT_SEARCH_INDETERMINATE"], { lowerBoundsByType, nodes: totalNodes });
    }
    return empty(
      "infeasible_for_L",
      [minimiseType?.maxCount !== undefined ? "MINIMISE_CAP_EXCEEDED" : "FIXED_TYPES_INSUFFICIENT"],
      { lowerBoundsByType, nodes: totalNodes },
    );
  }

  let labels = foundLabels;
  let minutesProven = false;
  if (minimiseType !== null && (input.minimiseMinutes ?? true)) {
    try {
      const refined = refineMinutes(countsFor(foundCount));
      if (refined !== null) {
        labels = refined;
        minutesProven = true;
      }
    } catch (error) {
      if (!(error instanceof BudgetExceeded)) throw error;
    }
  }

  // ---- physical witness: first-fit per type in start order -----------------------------
  const labelOf = new Array<number>(intervals.length).fill(-1);
  order.forEach((intervalIndex, k) => {
    labelOf[intervalIndex] = labels[k];
  });
  const prefixes = types.map((type) => defaultPrefix(type, types));
  const vehicleOf = new Array<string>(intervals.length).fill("");
  const countsByType: Record<string, number> = {};
  types.forEach((type, t) => {
    const freeAt: number[] = [];
    for (const intervalIndex of order) {
      if (labelOf[intervalIndex] !== t) continue;
      const item = intervals[intervalIndex];
      let slot = freeAt.findIndex((until) => until <= item.startMinutes);
      if (slot < 0) {
        slot = freeAt.length;
        freeAt.push(0);
      }
      freeAt[slot] = item.endMinutes + type.cooldownMinutes;
      vehicleOf[intervalIndex] = `${prefixes[t]}${slot + 1}`;
    }
    countsByType[type.typeId] = freeAt.length;
  });
  const assignments: TypedAssignment[] = intervals.map((item, index) => ({
    ...item,
    physicalVehicleId: vehicleOf[index],
    vehicleType: types[labelOf[index]].typeId,
  }));
  const fixedExceeded = fixedTypes.some((type) => (countsByType[type.typeId] ?? 0) > (type.count ?? 0));
  if (fixedExceeded || verifyTypedAssignment(assignments, types).length > 0) {
    return empty("blocked_data", ["WITNESS_INVALID"], { lowerBoundsByType, nodes: totalNodes });
  }

  const minimiseId = minimiseType?.typeId ?? null;
  const onMinimise = assignments.filter((item) => item.vehicleType === minimiseId);
  const windows = new Map<string, TypedAssignment[]>();
  for (const item of onMinimise) windows.set(item.physicalVehicleId, [...(windows.get(item.physicalVehicleId) ?? []), item]);
  const usageWindows: MinimiseTypeUsageWindow[] = [...windows.entries()]
    .sort(([a], [b]) => (a.length - b.length) || (a < b ? -1 : a > b ? 1 : 0))
    .map(([vehicleId, list]) => ({
      vehicleId,
      firstStartMinutes: Math.min(...list.map((item) => item.startMinutes)),
      lastEndMinutes: Math.max(...list.map((item) => item.endMinutes)),
      busyMinutes: list.reduce((sum, item) => sum + (item.endMinutes - item.startMinutes), 0),
      routeCount: list.length,
      jobIds: [...new Set(list.map((item) => item.jobId))].sort(),
    }));

  const hourly: Record<string, Record<string, Set<string>>> = {};
  for (const item of assignments) {
    const first = Math.floor(item.startMinutes / 60);
    const last = Math.floor(Math.max(item.startMinutes, item.endMinutes - 0.000000001) / 60);
    for (let hour = first; hour <= last; hour += 1) {
      const perType = (hourly[item.vehicleType] ??= {});
      (perType[hourKey(hour)] ??= new Set()).add(item.physicalVehicleId);
    }
  }
  const hourlyOccupiedVehiclesByType: Record<string, Record<string, number>> = {};
  for (const [typeId, perHour] of Object.entries(hourly)) {
    hourlyOccupiedVehiclesByType[typeId] = Object.fromEntries(
      Object.entries(perHour).sort(([a], [b]) => (a < b ? -1 : 1)).map(([key, set]) => [key, set.size]),
    );
  }

  return {
    status: budgetHit ? "witness" : "proven",
    reasonCodes: [],
    countsByType,
    lowerBoundsByType,
    minimiseTypeId: minimiseId,
    minimumCount: minimiseType === null ? null : foundCount,
    minimiseMinutes: minimiseType === null
      ? null
      : onMinimise.reduce((sum, item) => sum + (item.endMinutes - item.startMinutes), 0),
    minimiseMinutesProven: minutesProven,
    assignments,
    usageWindows,
    hourlyOccupiedVehiclesByType,
    nodes: totalNodes,
  };
}
