"""Property-based tests for all distance functions in uniride_core.algorithms.distance."""

import math

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis.strategies import floats, lists, tuples

from uniride_core.algorithms.distance import (
    create_np_distance_matrix,
    estimate_travel_time,
    euclidean_distance_2d,
    haversine_distance,
    tsplib_att_distance,
    tsplib_ceil_2d_distance,
    tsplib_distance_by_type,
    tsplib_euc_2d_distance,
    tsplib_geo_distance,
)

TOL = 1e-9
GEO_TOL = 1e-6

_GEO_LAT = floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
_GEO_LON = floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)
GEO_POINT = tuples(_GEO_LAT, _GEO_LON)

_2D_VAL = floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
COORD_2D = tuples(_2D_VAL, _2D_VAL)


def _approx_triangle(a, b, c, dist_fn):
    """Check triangle inequality: dist(a,c) <= dist(a,b) + dist(b,c) + eps"""
    return dist_fn(a, c) <= dist_fn(a, b) + dist_fn(b, c) + TOL


class TestHaversine:
    @given(GEO_POINT, GEO_POINT)
    def test_non_negative(self, p1, p2):
        assert haversine_distance(*p1, *p2) >= 0

    @given(GEO_POINT, GEO_POINT)
    def test_symmetric(self, p1, p2):
        assert abs(haversine_distance(*p1, *p2) - haversine_distance(*p2, *p1)) < GEO_TOL

    @given(GEO_POINT)
    def test_same_point_zero(self, p):
        assert haversine_distance(*p, *p) == 0

    @given(GEO_POINT, GEO_POINT, GEO_POINT)
    def test_triangle_inequality(self, p1, p2, p3):
        d12 = haversine_distance(*p1, *p2)
        d23 = haversine_distance(*p2, *p3)
        d13 = haversine_distance(*p1, *p3)
        assert d13 <= d12 + d23 + GEO_TOL

    @given(GEO_POINT, GEO_POINT)
    def test_reasonable_range(self, p1, p2):
        EARTH_HALF_CIRC = 20_014_000
        assert haversine_distance(*p1, *p2) <= EARTH_HALF_CIRC + GEO_TOL


class TestEuclidean:
    @given(COORD_2D, COORD_2D)
    def test_non_negative(self, p1, p2):
        assert euclidean_distance_2d(p1, p2) >= 0

    @given(COORD_2D, COORD_2D)
    def test_symmetric(self, p1, p2):
        d1 = euclidean_distance_2d(p1, p2)
        d2 = euclidean_distance_2d(p2, p1)
        assert abs(d1 - d2) < TOL

    @given(COORD_2D)
    def test_same_point_zero(self, p):
        assert euclidean_distance_2d(p, p) == 0

    @given(COORD_2D, COORD_2D, COORD_2D)
    def test_triangle_inequality(self, p1, p2, p3):
        d12 = euclidean_distance_2d(p1, p2)
        d23 = euclidean_distance_2d(p2, p3)
        d13 = euclidean_distance_2d(p1, p3)
        assert d13 <= d12 + d23 + TOL

    @given(COORD_2D, COORD_2D)
    def test_linear_scaling(self, p1, p2):
        d = euclidean_distance_2d(p1, p2)
        assume(0.1 <= d <= 1e7)
        scale = 2.5
        scaled = euclidean_distance_2d(
            (p1[0] * scale, p1[1] * scale),
            (p2[0] * scale, p2[1] * scale),
        )
        assert abs(scaled - d * scale) < TOL * scale * 10


class TestTSPLIB_EUC_2D:
    @given(COORD_2D, COORD_2D)
    def test_non_negative(self, p1, p2):
        assert tsplib_euc_2d_distance(p1, p2) >= 0

    @given(COORD_2D, COORD_2D)
    def test_symmetric(self, p1, p2):
        assert tsplib_euc_2d_distance(p1, p2) == tsplib_euc_2d_distance(p2, p1)

    @given(COORD_2D)
    def test_same_point_zero(self, p):
        assert tsplib_euc_2d_distance(p, p) == 0

    @given(COORD_2D, COORD_2D)
    def test_returns_int(self, p1, p2):
        assert isinstance(tsplib_euc_2d_distance(p1, p2), int)

    @given(COORD_2D, COORD_2D)
    def test_rounds_to_nearest_int(self, p1, p2):
        raw = euclidean_distance_2d(p1, p2)
        rounded = tsplib_euc_2d_distance(p1, p2)
        assert abs(rounded - raw) <= 0.5 + TOL


class TestTSPLIB_CEIL_2D:
    @given(COORD_2D, COORD_2D)
    def test_non_negative(self, p1, p2):
        assert tsplib_ceil_2d_distance(p1, p2) >= 0

    @given(COORD_2D, COORD_2D)
    def test_symmetric(self, p1, p2):
        assert tsplib_ceil_2d_distance(p1, p2) == tsplib_ceil_2d_distance(p2, p1)

    @given(COORD_2D)
    def test_same_point_zero(self, p):
        assert tsplib_ceil_2d_distance(p, p) == 0

    @given(COORD_2D, COORD_2D)
    def test_returns_int(self, p1, p2):
        assert isinstance(tsplib_ceil_2d_distance(p1, p2), int)

    @given(COORD_2D, COORD_2D)
    def test_is_ceiling(self, p1, p2):
        raw = euclidean_distance_2d(p1, p2)
        ceil_val = tsplib_ceil_2d_distance(p1, p2)
        assert ceil_val >= raw - 1e-9
        assert ceil_val < raw + 1.0


class TestTSPLIB_ATT:
    @given(COORD_2D, COORD_2D)
    def test_non_negative(self, p1, p2):
        assert tsplib_att_distance(p1, p2) >= 0

    @given(COORD_2D, COORD_2D)
    def test_symmetric(self, p1, p2):
        assert tsplib_att_distance(p1, p2) == tsplib_att_distance(p2, p1)

    @given(COORD_2D)
    def test_same_point_zero(self, p):
        assert tsplib_att_distance(p, p) == 0

    @given(COORD_2D, COORD_2D)
    def test_returns_int(self, p1, p2):
        assert isinstance(tsplib_att_distance(p1, p2), int)

    @given(COORD_2D, COORD_2D)
    def test_pseudo_euclidean_range(self, p1, p2):
        raw_sq = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
        rij = math.sqrt(raw_sq / 10.0)
        att_val = tsplib_att_distance(p1, p2)
        assert att_val >= int(round(rij))
        assert att_val <= int(round(rij)) + 1


class TestTSPLIB_GEO:
    @given(COORD_2D, COORD_2D)
    def test_non_negative(self, p1, p2):
        assert tsplib_geo_distance(p1, p2) >= 0

    @given(COORD_2D, COORD_2D)
    def test_symmetric(self, p1, p2):
        assert tsplib_geo_distance(p1, p2) == tsplib_geo_distance(p2, p1)

    @given(COORD_2D)
    def test_same_point_zero(self, p):
        assert tsplib_geo_distance(p, p) == 0

    @given(COORD_2D, COORD_2D)
    def test_returns_int(self, p1, p2):
        assert isinstance(tsplib_geo_distance(p1, p2), int)

    @given(
        floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
        floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False),
        floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
        floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False),
    )
    def test_max_range(self, lat1, lon1, lat2, lon2):
        TSPLIB_GEO_MAX = 20000
        assert tsplib_geo_distance((lat1, lon1), (lat2, lon2)) <= TSPLIB_GEO_MAX


class TestDistanceByType:
    @given(COORD_2D, COORD_2D)
    def test_euc_2d_dispatch(self, p1, p2):
        assert tsplib_distance_by_type("EUC_2D", p1, p2) == tsplib_euc_2d_distance(p1, p2)

    @given(COORD_2D, COORD_2D)
    def test_ceil_2d_dispatch(self, p1, p2):
        assert tsplib_distance_by_type("CEIL_2D", p1, p2) == tsplib_ceil_2d_distance(p1, p2)

    @given(COORD_2D, COORD_2D)
    def test_att_dispatch(self, p1, p2):
        assert tsplib_distance_by_type("ATT", p1, p2) == tsplib_att_distance(p1, p2)

    @given(COORD_2D, COORD_2D)
    def test_geo_dispatch(self, p1, p2):
        assert tsplib_distance_by_type("GEO", p1, p2) == tsplib_geo_distance(p1, p2)

    @given(COORD_2D, COORD_2D)
    def test_unknown_type_raises(self, p1, p2):
        with pytest.raises(ValueError, match="Unsupported EDGE_WEIGHT_TYPE"):
            tsplib_distance_by_type("UNKNOWN_TYPE", p1, p2)

    @given(COORD_2D, COORD_2D)
    def test_case_insensitive(self, p1, p2):
        assert tsplib_distance_by_type("euc_2d", p1, p2) == tsplib_euc_2d_distance(p1, p2)


class TestEstimateTravelTime:
    @given(
        floats(min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False),
        floats(min_value=1, max_value=200, allow_nan=False, allow_infinity=False),
    )
    def test_non_negative(self, dist, speed):
        assert estimate_travel_time(dist, speed) >= 0

    @given(
        floats(min_value=0, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    def test_zero_distance_zero_time(self, speed):
        assume(speed > 0)
        assert estimate_travel_time(0, speed) == 0

    def test_proportional_to_distance(self):
        t1 = estimate_travel_time(1000, 40)
        t2 = estimate_travel_time(2000, 40)
        assert abs(t2 / t1 - 2.0) < TOL

    def test_inversely_proportional_to_speed(self):
        t1 = estimate_travel_time(10000, 40)
        t2 = estimate_travel_time(10000, 80)
        assert abs(t2 / t1 - 0.5) < TOL


class TestNpDistanceMatrix:
    @given(lists(COORD_2D, min_size=1, max_size=20))
    def test_symmetric(self, coords):
        dm = create_np_distance_matrix(coords)
        n = len(coords)
        for i in range(n):
            for j in range(n):
                assert dm[i, j] == dm[j, i]

    @given(lists(COORD_2D, min_size=1, max_size=20))
    def test_zero_diagonal(self, coords):
        dm = create_np_distance_matrix(coords)
        n = len(coords)
        for i in range(n):
            assert dm[i, i] == 0

    @given(lists(COORD_2D, min_size=1, max_size=20))
    def test_non_negative(self, coords):
        dm = create_np_distance_matrix(coords)
        assert np.all(dm >= 0)

    @given(lists(COORD_2D, min_size=1, max_size=20))
    def test_integer_values(self, coords):
        dm = create_np_distance_matrix(coords)
        assert np.all(dm == np.round(dm))

    @given(lists(COORD_2D, min_size=1, max_size=20))
    def test_matches_euc_2d(self, coords):
        dm = create_np_distance_matrix(coords)
        n = len(coords)
        for i in range(n):
            for j in range(n):
                expected = float(tsplib_euc_2d_distance(coords[i], coords[j]))
                assert dm[i, j] == expected, f"Mismatch at ({i},{j})"
