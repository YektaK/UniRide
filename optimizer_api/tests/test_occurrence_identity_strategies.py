"""Strategy-level occurrence-identity integration tests.

Verifies that production strategies treat multiple customers at the same
physical ``location_code`` as distinct solver nodes end-to-end, while
preserving backward compatibility for single-customer locations.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from models.schemas import OptimizationRequest, StudentNode, LocationNode


class FakeDataLoader:
    """Minimal DataLoader stand-in returning a coordinate-based submatrix."""

    def get_submatrix(self, locations, coordinates=None, geo_coords=False, asymmetric_haversine=False):
        n = len(locations)
        if not coordinates:
            return [[0.0] * n for _ in range(n)]
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            c1 = coordinates.get(locations[i], {}) or {"lat": 0.0, "lng": 0.0}
            for j in range(n):
                c2 = coordinates.get(locations[j], {}) or {"lat": 0.0, "lng": 0.0}
                d = ((c1.get("lat", 0.0) - c2.get("lat", 0.0)) ** 2
                     + (c1.get("lng", 0.0) - c2.get("lng", 0.0)) ** 2) ** 0.5
                matrix[i][j] = round(d, 2)
        return matrix


def _request(students, depot_id="D.Kampus", lat=0.0, lng=0.0):
    depot = LocationNode(id=depot_id, lat=lat, lng=lng, type="Depot")
    return OptimizationRequest(
        algorithm="ga_split",
        students=students,
        depot=depot,
        max_travel_time=240,
        sw_capacity=10,
        so_capacity=10,
    )


def _student(sid, loc, sw=False, lat=0.0, lng=0.0):
    return StudentNode(
        id=sid,
        name=sid,
        location_code=loc,
        coordinates={"lat": lat, "lng": lng},
        disability_type="Sw" if sw else "So",
    )


def _patch_loader(monkeypatch):
    from strategies.sota_response_builder import DataLoader
    from utils import data_loader as data_loader_module

    fake = FakeDataLoader()
    monkeypatch.setattr(data_loader_module, "DataLoader", type("DL", (), {"get_instance": staticmethod(lambda: fake)}))
    monkeypatch.setattr(DataLoader, "get_instance", staticmethod(lambda: fake))
    return fake


# ── Greedy ────────────────────────────────────────────────────────────────────

class TestGreedyOccurrenceIdentity:
    def test_greedy_keeps_same_location_students_distinct(self, monkeypatch):
        _patch_loader(monkeypatch)
        from strategies.greedy_heuristic import GreedyHeuristicStrategy

        students = [
            _student("S1", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S2", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S3", "L2", sw=False, lat=2.0, lng=0.0),
        ]
        request = _request(students, lat=0.0, lng=0.0)
        result = GreedyHeuristicStrategy().optimize(request)

        assert result.success
        visited = [sid for route in result.routes for sid in route.student_ids]
        assert "S1" in visited
        assert "S2" in visited
        assert "S3" in visited
        assert len(visited) == 3, f"expected all 3 students, got {visited}"
        # Route steps must use distinct occurrence keys for same-location students
        route = result.routes[0]
        step_locs = [step.location2 for step in route.route_details if step.location2 != "D.Kampus"]
        assert "L1#S1" in step_locs
        assert "L1#S2" in step_locs

    def test_greedy_backward_compat_single_customer_locations(self, monkeypatch):
        _patch_loader(monkeypatch)
        from strategies.greedy_heuristic import GreedyHeuristicStrategy

        students = [
            _student("S1", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S2", "L2", sw=False, lat=2.0, lng=0.0),
        ]
        request = _request(students)
        result = GreedyHeuristicStrategy().optimize(request)

        assert result.success
        route = result.routes[0]
        step_locs = [step.location2 for step in route.route_details if step.location2 != "D.Kampus"]
        assert step_locs == ["L1", "L2"]
        assert sorted(route.student_ids) == ["S1", "S2"]


# ── GA-Split ─────────────────────────────────────────────────────────────────

class TestGASplitOccurrenceIdentity:
    def _run(self, monkeypatch, students):
        _patch_loader(monkeypatch)

        import strategies.ga_split_strategy as ga_module

        captured = {}

        class FakeSolution:
            final_result = {"routes": [], "time_window_violations": 0}

        def fake_solve_ga_split(**kwargs):
            captured.update(kwargs)
            FakeSolution.final_result = {"routes": [list(kwargs["waypoints"])], "time_window_violations": 0}
            return FakeSolution()

        monkeypatch.setattr(ga_module, "solve_ga_split", fake_solve_ga_split)

        request = _request(students)
        result = ga_module.GASplitStrategy(config={"population_size": 2, "max_iterations": 1}).optimize(request)
        return result, captured

    def test_ga_split_keeps_same_location_students_distinct(self, monkeypatch):
        students = [
            _student("S1", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S2", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S3", "L2", sw=False, lat=2.0, lng=0.0),
        ]
        result, captured = self._run(monkeypatch, students)

        # Solver input must use distinct occurrence keys
        assert captured["waypoints"] == ["L1#S1", "L1#S2", "L2"]
        assert set(captured["demands"]) == {"L1#S1", "L1#S2", "L2"}
        for node in ("L1#S1", "L1#S2", "L2", "D.Kampus"):
            assert node in captured["distance_matrix"]

        # Response must preserve both same-location students
        visited = [sid for route in result.routes for sid in route.student_ids]
        assert "S1" in visited
        assert "S2" in visited
        assert "S3" in visited
        assert len(visited) == 3

    def test_ga_split_backward_compat_single_customer_locations(self, monkeypatch):
        students = [
            _student("S1", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S2", "L2", sw=False, lat=2.0, lng=0.0),
        ]
        result, captured = self._run(monkeypatch, students)

        assert captured["waypoints"] == ["L1", "L2"]
        assert set(captured["demands"]) == {"L1", "L2"}
        visited = [sid for route in result.routes for sid in route.student_ids]
        assert sorted(visited) == ["S1", "S2"]


# ── SOTA context (shared by greedy / SOTA / holistic strategies) ─────────────

class TestSOTAContextOccurrenceIdentity:
    def test_context_uses_occurrence_keys_for_same_location(self, monkeypatch):
        fake = _patch_loader(monkeypatch)
        from strategies.sota_response_builder import build_sota_request_context

        students = [
            _student("S1", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S2", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S3", "L2", sw=False, lat=2.0, lng=0.0),
        ]
        depot = LocationNode(id="D", lat=0.0, lng=0.0)
        context = build_sota_request_context(students, depot)

        assert context["student_ids"] == ["L1#S1", "L1#S2", "L2"]
        assert set(context["time_matrix"]) == {"D", "L1#S1", "L1#S2", "L2"}
        assert "L1#S1" in context["coordinates"]
        assert "L1#S2" in context["coordinates"]
        # Same-location occurrences have zero travel time between them
        assert context["time_matrix"]["L1#S1"]["L1#S2"] == 0.0

    def test_context_backward_compat_unique_locations(self, monkeypatch):
        _patch_loader(monkeypatch)
        from strategies.sota_response_builder import build_sota_request_context

        students = [
            _student("S1", "L1", sw=True, lat=1.0, lng=0.0),
            _student("S2", "L2", sw=False, lat=2.0, lng=0.0),
        ]
        depot = LocationNode(id="D", lat=0.0, lng=0.0)
        context = build_sota_request_context(students, depot)

        assert context["student_ids"] == ["L1", "L2"]
        assert set(context["time_matrix"]) == {"D", "L1", "L2"}


# ── get_time_windows (occurrence-aware) ──────────────────────────────────────

class TestTimeWindowsOccurrenceIdentity:
    def test_get_time_windows_disambiguates_same_location(self):
        students = [
            StudentNode(id="S1", location_code="L1", pickup_time="08:00", disability_type="Sw"),
            StudentNode(id="S2", location_code="L1", pickup_time="09:00", disability_type="So"),
        ]
        request = _request(students)
        request.use_time_windows = True
        windows = request.get_time_windows()
        assert set(windows) == {"L1#S1", "L1#S2"}
        assert windows["L1#S1"].earliest == 450  # 07:30
        assert windows["L1#S2"].earliest == 510  # 08:30

    def test_get_time_windows_backward_compat_unique_locations(self):
        students = [
            StudentNode(id="S1", location_code="L1", pickup_time="08:00", disability_type="Sw"),
            StudentNode(id="S2", location_code="L2", pickup_time="09:00", disability_type="So"),
        ]
        request = _request(students)
        request.use_time_windows = True
        windows = request.get_time_windows()
        assert set(windows) == {"L1", "L2"}
