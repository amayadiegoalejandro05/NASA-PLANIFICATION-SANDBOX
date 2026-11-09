"""Unit tests of the resource-limited mission planner (synthetic maps only)."""
import unittest
from mars_route_planner import Terrain, PlannerConfig
from mars_mission_resources import (
    Budget, Consumption, NoFeasibleMissionError, ResourceMissionPlanner
)


def flat(rows=5, cols=7, res=10.0):
    return Terrain(
        heights_m=[[0.0] * cols for _ in range(rows)],
        obstacles=[[False] * cols for _ in range(rows)],
        risk=[[0.0] * cols for _ in range(rows)],
        roughness=[[0.0] * cols for _ in range(rows)],
        resolution_m=res,
    )


def make(t, c=None, b=None):
    cfg = PlannerConfig(rover_radius_m=0, safety_margin_m=0,
                        near_obstacle_m=0, proximity_weight=0)
    c = c or Consumption(speed_m_per_min=10, oxygen_u_per_min=1,
                         water_l_per_min=.1, battery_wh_per_min=2,
                         nutrition_kcal_per_min=3)
    b = b or Budget(time_min=12, time_reserve_min=3, oxygen_u=12,
                    oxygen_reserve_u=3, water_l=1, water_reserve_l=.1,
                    battery_wh=20, battery_reserve_wh=2,
                    nutrition_kcal=30, nutrition_reserve_kcal=3)
    return ResourceMissionPlanner(t, cfg, c, b)


class TestResourceMission(unittest.TestCase):
    def test_roundtrip_activities_and_reserves(self):
        plan = make(flat()).plan((2, 1), (2, 3), activity_min=4)
        self.assertEqual(plan.path[0], (2, 1))
        self.assertEqual(plan.path[-1], (2, 1))
        self.assertEqual(plan.path[plan.goal_index], (2, 3))
        self.assertAlmostEqual(plan.total.distance_m, 40)
        self.assertAlmostEqual(plan.total.minutes, 8)
        self.assertAlmostEqual(plan.total.oxygen_u, 8)
        self.assertAlmostEqual(plan.total.water_l, .8)
        self.assertAlmostEqual(plan.total.battery_wh, 16)
        self.assertAlmostEqual(plan.total.nutrition_kcal, 24)

    def test_reject_even_if_outbound_is_feasible(self):
        budget = Budget(time_min=20, time_reserve_min=0,
                        oxygen_u=7, oxygen_reserve_u=1)
        with self.assertRaises(NoFeasibleMissionError):
            make(flat(1, 5), b=budget).plan((0, 0), (0, 4))

    def test_reject_if_water_reserve_would_be_spent(self):
        budget = Budget(time_min=12, time_reserve_min=0,
                        water_l=.9, water_reserve_l=.2)
        with self.assertRaises(NoFeasibleMissionError):
            make(flat(), b=budget).plan((2, 1), (2, 3), activity_min=4)

    def test_respects_blocked_cells_and_returns(self):
        t = flat()
        t.obstacles[2][3] = True
        p = make(t, c=Consumption(speed_m_per_min=10),
                 b=Budget(time_min=100, time_reserve_min=5)).plan((2, 1), (2, 5))
        self.assertNotIn((2, 3), p.path)
        self.assertEqual(p.path[-1], (2, 1))
        self.assertTrue(len(p.path) > 2)

    def test_rover_has_no_human_consumables(self):
        c = Consumption(speed_m_per_min=10, battery_wh_per_min=2)
        b = Budget(time_min=30, time_reserve_min=3,
                   battery_wh=30, battery_reserve_wh=5)
        p = make(flat(), c=c, b=b).plan((2, 1), (2, 3), activity_min=3)
        self.assertEqual(p.total.oxygen_u, 0)
        self.assertEqual(p.total.water_l, 0)
        self.assertEqual(p.total.nutrition_kcal, 0)
        self.assertGreater(p.total.battery_wh, 0)
        self.assertLessEqual(p.total.battery_wh, 25)

    def test_activity_cost_is_not_free(self):
        t = flat()
        c = Consumption(speed_m_per_min=10, oxygen_u_per_min=1)
        b = Budget(time_min=20, time_reserve_min=0,
                   oxygen_u=20, oxygen_reserve_u=0)
        fast = make(t, c, b).plan((2, 1), (2, 3), activity_min=0)
        work = make(t, c, b).plan((2, 1), (2, 3), activity_min=6)
        self.assertAlmostEqual(work.total.minutes - fast.total.minutes, 6)
        self.assertAlmostEqual(work.total.oxygen_u - fast.total.oxygen_u, 6)

    def test_uphill_is_not_free(self):
        c = Consumption(speed_m_per_min=10, oxygen_u_per_min=1,
                        battery_wh_per_min=1, climb_battery_wh_per_m=3)
        uphill = c.traveling(10, 2, 0)
        downhill = c.traveling(10, -2, 0)
        self.assertGreater(uphill.minutes, downhill.minutes)
        self.assertGreater(uphill.oxygen_u, downhill.oxygen_u)
        self.assertGreater(uphill.battery_wh, downhill.battery_wh)

    def test_budget_validation(self):
        with self.assertRaises(ValueError):
            Budget(time_min=10, time_reserve_min=11)


if __name__ == '__main__':
    unittest.main(verbosity=2)
