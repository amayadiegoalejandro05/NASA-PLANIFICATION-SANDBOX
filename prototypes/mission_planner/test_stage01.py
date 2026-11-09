import unittest
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
from mars_route_planner import Terrain, PlannerConfig, RiskAwareAStar, NoSafeRouteError
from mars_mission_resources import (ResourceMissionPlanner, Consumption, Budget,
    SearchLimitReachedError, NoFeasibleMissionError, main)


def flat(n=5, res=1):
    return Terrain([[0.] * n for _ in range(n)], [[False] * n for _ in range(n)],
                   [[0.] * n for _ in range(n)], [[0.] * n for _ in range(n)], res)

CFG = PlannerConfig(rover_radius_m=0, safety_margin_m=0, near_obstacle_m=0,
                    proximity_weight=0)


class StageOne(unittest.TestCase):
    def mission(self, terrain=None, budget=None):
        return ResourceMissionPlanner(terrain or flat(2), CFG,
            Consumption(speed_m_per_min=1), budget or Budget(time_min=100, time_reserve_min=0))

    def test_limit_exact_and_classification(self):
        t = Terrain([[0., 0.]], [[False, False]], [[0., 0.]], [[0., 0.]], 1)
        p = self.mission(t)
        self.assertEqual(p.plan((0, 0), (0, 1), max_labels=3).explored_labels, 3)
        for limit in (1, 2):
            with self.assertRaises(SearchLimitReachedError) as cm:
                p.plan((0, 0), (0, 1), max_labels=limit)
            e = cm.exception
            self.assertEqual((e.limit, e.generated_labels), (limit, limit))
            self.assertNotIsInstance(e, (NoFeasibleMissionError, NoSafeRouteError))
            self.assertIn('factibilidad no determinada', str(e))
        for invalid in (0, -1, 1.5, 3., True, None, '3', float('inf')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                p.plan((0, 0), (0, 1), max_labels=invalid)

    def test_exhaustion_is_infeasible_even_at_limit(self):
        with self.assertRaises(NoFeasibleMissionError):
            self.mission(budget=Budget(time_min=.1, time_reserve_min=0)).plan((0, 0), (0, 1), max_labels=1)

    def test_cli_interrupted(self):
        output = StringIO()
        with patch('mars_mission_resources.astronaut_demo', side_effect=SearchLimitReachedError(1, 1)), \
             patch('mars_mission_resources.rover_demo', side_effect=NoFeasibleMissionError('agotada')), \
             redirect_stdout(output):
            main()
        self.assertIn('ASTRONAUTA: BUSQUEDA INTERRUMPIDA; FACTIBILIDAD NO DETERMINADA', output.getvalue())
        self.assertIn('ROVER: MISION RECHAZADA', output.getvalue())

    def test_snapshot_and_updated_requests(self):
        for change in ('obstacles', 'heights', 'unknown', 'resolution'):
            with self.subTest(change=change):
                t = flat()
                p = self.mission(t)
                before = p.plan((2, 1), (2, 3))
                if change == 'obstacles': t.obstacles[2][2] = True
                elif change == 'heights': t.heights_m[2][2] = 10
                elif change == 'unknown': t.heights_m[2][2] = None
                else: t.resolution_m = 2
                self.assertEqual(p.plan((2, 1), (2, 3)), before)
                q = self.mission(t)
                if change == 'resolution':
                    self.assertEqual(q.plan((2, 1), (2, 3)).total.distance_m,
                                     before.total.distance_m * 2)
                elif change == 'heights':
                    self.assertFalse(q.nav.traversable((2, 1)))
                    with self.assertRaises(NoFeasibleMissionError):
                        q.plan((2, 1), (2, 3))
                else:
                    self.assertNotIn((2, 2), q.plan((2, 1), (2, 3)).path)
                with self.assertRaises(TypeError): p.nav.t.obstacles[0][0] = True
                with self.assertRaises(FrozenInstanceError): p.nav.t.resolution_m = 0
                with self.assertRaises(AttributeError): p.nav.t = t
        t = flat(); p = self.mission(t); t.resolution_m = 0
        with self.assertRaises(ValueError): self.mission(t)
        self.assertEqual(p.nav.t.resolution_m, 1)

    def test_area_footprint_and_boundary(self):
        t = flat(); t.obstacles[2][2] = True
        p = RiskAwareAStar(t, replace(CFG, rover_radius_m=.75))
        self.assertFalse(p.traversable((2, 1)))  # center distance 1, square distance .5
        self.assertFalse(p.traversable((0, 0)))
        self.assertIsNone(p._edge((1, 0), (1, 1)))
        q = RiskAwareAStar(flat(), replace(CFG, rover_radius_m=.49))
        self.assertIsNotNone(q._edge((0, 0), (0, 1)))
        q = RiskAwareAStar(flat(), replace(CFG, rover_radius_m=.51))
        self.assertIsNone(q._edge((0, 0), (0, 1)))

    def test_swept_diagonal_and_corners(self):
        t = flat(); t.obstacles[1][2] = True
        p = RiskAwareAStar(t, replace(CFG, rover_radius_m=.4))
        self.assertTrue(p.traversable((1, 1)))
        self.assertTrue(p.traversable((2, 2)))
        self.assertFalse(p._swept_clear((1, 1), (2, 2)))
        self.assertIsNone(p._edge((1, 1), (2, 2)))
        # Zero radius must still obey no corner cutting with only ONE blocked side.
        p = RiskAwareAStar(t, CFG)
        self.assertIsNone(p._edge((1, 1), (2, 2)))
        self.assertIsNotNone(RiskAwareAStar(flat(), CFG)._edge((1, 1), (2, 2)))
        # Endpoints clear, swept interior intersects expanded area.
        t = flat(9); t.obstacles[2][4] = True
        p = RiskAwareAStar(t, replace(CFG, rover_radius_m=1.51))
        self.assertTrue(p.traversable((3, 2)))
        self.assertTrue(p.traversable((4, 3)))
        self.assertFalse(p._swept_clear((3, 2), (4, 3)))

if __name__ == '__main__': unittest.main()


