"""Pruebas para el prototipo MARS GOD'S EYE."""
from dataclasses import replace
import unittest
from mars_route_planner import (
    Terrain, PlannerConfig, RiskAwareAStar, NoSafeRouteError, synthetic_terrain
)


def flat(rows=10, cols=10, res=0.25):
    return Terrain(
        [[0.0] * cols for _ in range(rows)],
        [[False] * cols for _ in range(rows)],
        [[0.0] * cols for _ in range(rows)],
        [[0.0] * cols for _ in range(rows)], res,
    )


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.cfg = PlannerConfig(rover_radius_m=0.0, safety_margin_m=0.0,
                                 near_obstacle_m=0.0, proximity_weight=0.0)

    def test_route_flat(self):
        t = flat()
        result = RiskAwareAStar(t, self.cfg).plan((1, 1), (8, 8))
        self.assertEqual(result.cells[0], (1, 1))
        self.assertEqual(result.cells[-1], (8, 8))
        self.assertAlmostEqual(result.distance_m, 7 * 2**0.5 * t.resolution_m)

    def test_no_route_wall(self):
        t = flat()
        for r in range(t.rows):
            t.obstacles[r][5] = True
        with self.assertRaises(NoSafeRouteError):
            RiskAwareAStar(t, self.cfg).plan((4, 2), (4, 7))

    def test_slope_limit(self):
        t = flat()
        for r in range(t.rows):
            for c in range(5, t.cols):
                t.heights_m[r][c] = 2.0
        with self.assertRaises(NoSafeRouteError):
            RiskAwareAStar(t, self.cfg).plan((4, 2), (4, 7))

    def test_prefers_low_risk_detour(self):
        t = flat(7, 11)
        for c in range(2, 9):
            t.risk[3][c] = 1.0
        cfg = replace(self.cfg, risk_weight=20.0)
        result = RiskAwareAStar(t, cfg).plan((3, 1), (3, 9))
        self.assertTrue(any(r != 3 for r, c in result.cells))

    def test_replanning(self):
        t = flat()
        original = RiskAwareAStar(t, self.cfg).plan((1, 1), (8, 8))
        midpoint = original.cells[len(original.cells)//2]
        t.obstacles[midpoint[0]][midpoint[1]] = True
        updated = RiskAwareAStar(t, self.cfg).plan((1, 1), (8, 8))
        self.assertNotIn(midpoint, updated.cells)

    def test_unknown_is_blocked(self):
        t = flat()
        t.heights_m[3][3] = None
        planner = RiskAwareAStar(t, self.cfg)
        self.assertFalse(planner.traversable((3, 3)))

    def test_default_demo(self):
        planner = RiskAwareAStar(synthetic_terrain())
        route = planner.plan((8, 2), (8, 27))
        self.assertTrue(route.distance_m > 0)
        self.assertTrue(all(planner.traversable(cell) for cell in route.cells))


if __name__ == '__main__':
    unittest.main()
