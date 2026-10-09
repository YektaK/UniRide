#!/usr/bin/env python3
"""Self-test of scripts/plan_fleet_pareto.py against the archived campaign (standard library only).

Run: python scripts/test_plan_fleet_pareto.py
The independent checks use only the CSV columns, not the response routes the script itself reads.
"""
import csv
import os
import sys
import unittest

sys.argv = sys.argv[:1]  # the script reads the results folder from argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_fleet_pareto as P  # noqa: E402


class ParetoTests(unittest.TestCase):
    def test_dominance_semantics(self):
        self.assertTrue(P.dominates((1, 2, 3), (1, 2, 4)))
        self.assertFalse(P.dominates((1, 2, 3), (1, 2, 3)))  # equal vectors do not dominate
        self.assertFalse(P.dominates((1, 3, 3), (2, 2, 3)))  # incomparable
        self.assertFalse(P.dominates((2, 2, 3), (1, 2, 3)))

    def test_no_route_violations(self):
        self.assertEqual(P.VIOL, [])
        self.assertEqual(P.SHAS, {"bfb2dd85087c1d5a4310ad23644f3b2ea53886db5c03dd5bf536912eb2dd31e5"})

    def test_option_counts(self):
        self.assertEqual(len(P.OPTS), 36)
        self.assertEqual(len(P.FEAS), 28)
        self.assertEqual(sum(1 for o in P.OPTS if o["family"] == "hybrid"), 4)

    def test_nondominated_flags_by_brute_force(self):
        for o in P.FEAS:
            dom = any(p is not o and p["R"] == o["R"] and all(a <= b for a, b in zip((p["f1"], p["f2"], p["f3m"]), (o["f1"], o["f2"], o["f3m"])))
                      and (p["f1"], p["f2"], p["f3m"]) != (o["f1"], o["f2"], o["f3m"]) for p in P.FEAS)
            self.assertEqual(o["nd_R"], not dom, o["id"])

    def test_f3_matches_csv_busy_definition(self):
        """f3 = borrowed route minutes + 10-min cooldown per borrowed route, recomputed from scenario_daily.csv."""
        for o in P.FEAS:
            if o["derived"] or o["family"] == "minibus-only":
                continue
            ds = o["days"][0]["ds"]
            s = o["days"][0]["s"]
            mins = sum(int(ds.D[(d, o["R"], s)]["car_vehicle_minutes"]) + 10 * int(ds.D[(d, o["R"], s)]["car_routes"]) for d in P.DATES)
            self.assertEqual(o["f3m"], mins, o["id"])
            self.assertAlmostEqual(o["f3"], mins / 60.0)

    def test_key_values(self):
        by = {o["id"]: o for o in P.FEAS}
        o = by["R60_minibus+sedan_L3"]
        self.assertEqual((o["f1"], o["f2"], o["f4"]), (3, 3, 5))
        self.assertAlmostEqual(o["f3"], 18.18, places=2)
        o = by["R60_minibus+minivan_L2"]
        self.assertEqual((o["f1"], o["f2"], o["f4"]), (2, 4, 5))
        self.assertTrue(by["R60_minibus-only"]["nd_R"] and not by["R60_minibus-only"]["nd_glob"])
        self.assertFalse(by["R60_hybrid_L2"]["nd_R"])

    def test_minivan_total_capacity_three(self):
        """H03: Doblo = 3 passengers in total (at most 1 Sw). Active minivan data must declare it and respect it."""
        mv = [d for d in P.DSS if d.name == "minivan"][0]
        self.assertEqual(mv.types["minivan"].get("totalCapacity"), 3)
        for date in mv.dates:
            for R in P.RS:
                for s in mv.scens:
                    for r in mv.response(date, R, s)["scenario"]["routes"]:
                        if r["vehicleType"] == "minivan":
                            self.assertLessEqual(r["swCount"] + r["soCount"], 3)
                            self.assertLessEqual(r["swCount"], 1)

    def test_check_run_flags_total_capacity(self):
        """A 1 Sw + 3 So route is within the per-kind capacities but exceeds the total of 3: must be a violation."""
        class FakeDS:
            types = {"minivan": {"swCapacity": 1, "soCapacity": 3, "totalCapacity": 3, "cooldownMinutes": 10}}
            bor = "minivan"
        steps = [{"location1": lab, "location2": "C", "duration": 5} for lab in ("Sw1", "So1", "So2", "So3")]
        route = {"vehicleType": "minivan", "physicalVehicleId": "V1", "jobId": "j", "startMinutes": 0, "endMinutes": 20, "minutes": 20,
                 "direction": "pickup", "steps": steps, "swCount": 1, "soCount": 3, "occurrenceIds": ["x:Sw1", "x:So1", "x:So2", "x:So3"]}
        full = {"serviceDate": "d", "limits": {"maxRideTimeMinutes": 50}, "scenario": {"routes": [route]}, "occurrenceLabels": ["x:Sw1", "x:So1", "x:So2", "x:So3"]}
        row = {"legs": "4", "cars": "1", "car_vehicle_minutes": "5", "car_routes": "1", "ride_mean": "5", "ride_max": "5", "date": "d"}
        try:
            v = P.check_run(FakeDS, full, row, 50, "L0")
        except Exception:  # other checks may trip on the minimal fake; the capacity message is produced before them
            self.fail("check_run raised on the fake route")
        self.assertTrue(any(x.startswith("total capacity") for x in v), v)

    def test_hybrid_is_day_level_combination(self):
        for o in P.OPTS:
            if o["family"] != "hybrid":
                continue
            sd, mv = P.DAYS[("main", o["R"], "L%d" % o["L"])], P.DAYS[("minivan", o["R"], "L%d" % o["L"])]
            for h, a, b in zip(o["days"], sd, mv):
                self.assertIs(h, a if a["ok"] else b)

    def test_csv_matches_objects(self):
        with open(os.path.join(P.RES, "pareto_options.csv"), encoding="utf-8", newline="") as f:
            rows = {r["option_id"]: r for r in csv.DictReader(f)}
        self.assertEqual(len(rows), 36)
        for o in P.OPTS:
            r = rows[o["id"]]
            self.assertEqual(r["feasible"], str(o["feasible"]).lower())
            if o["feasible"]:
                self.assertEqual(r["dominated_per_R"], str(not o["nd_R"]).lower())
                self.assertEqual(float(r["f3_borrowed_vehicle_hours_week"]), round(o["f3"], 2))


if __name__ == "__main__":
    unittest.main(argv=sys.argv[:1])
