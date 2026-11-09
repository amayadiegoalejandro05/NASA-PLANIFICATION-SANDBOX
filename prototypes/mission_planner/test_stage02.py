import unittest
from dataclasses import replace
from mars_mission_resources import (AgentProfile, ResourceAllocation as A, ExcludedResource,
    Mobility, MotionModel, ResourceMissionPlanner, NoFeasibleMissionError,
    SearchLimitReachedError, small_example_profile, small_demo)
from mars_route_planner import Terrain


def terrain():
    return Terrain([[0., 0., 0.]], [[False]*3], [[0.]*3], [[0.]*3], 1.)


class StageTwo(unittest.TestCase):
    def test_small_astronaut(self):
        p = small_demo('astronaut')
        self.assertEqual(p.path, ((0,0),(0,1),(0,2),(0,1),(0,0)))
        self.assertEqual(p.total.values(), (6, 10, 1.2000000000000002, 18, 28, 4))
        self.assertEqual(p.outbound[-1], p.inbound[0])

    def test_small_rover(self):
        p = small_demo('rover')
        self.assertEqual(p.total.values(), (6, 0, 0, 18, 0, 4))

    def test_rover_rejects_human_inputs(self):
        p = small_example_profile('rover')
        for name in ('oxygen', 'water', 'nutrition'):
            for entry in (A(0,0,0,0), A(10,1,0,0), A(10,0,1,2), ExcludedResource('experimento')):
                with self.subTest(name=name, entry=entry), self.assertRaises(ValueError):
                    replace(p, resources=dict(p.resources, **{name: entry}))

    def test_status_and_exclusion(self):
        p = small_example_profile('astronaut')
        p = replace(p, resources=dict(p.resources, oxygen=ExcludedResource('Sin modelo en este experimento'), water=A(0,0,0,0)))
        self.assertEqual(p.resource_status('oxygen'), 'excluded')
        self.assertEqual(p.resource_status('water'), 'modeled')
        self.assertEqual(small_example_profile('rover').resource_status('oxygen'), 'not_applicable')
        result = ResourceMissionPlanner.from_profile(terrain(), p).plan((0,0),(0,2),2)
        self.assertEqual(result.total.oxygen_u, 0)
        with self.assertRaises(TypeError): ExcludedResource('omitido', reserve=1)
        with self.assertRaises(ValueError): ExcludedResource('')
        with self.assertRaises(TypeError): p.resources['water'] = A(1,0,0,0)
        for name in ('oxygen','water','nutrition','time','battery'):
            resources = dict(p.resources); del resources[name]
            with self.assertRaises(ValueError): replace(p, resources=resources)
        for name in ('time','battery'):
            with self.assertRaises(ValueError): replace(p, resources=dict(p.resources, **{name:ExcludedResource('omitido')}))

    def test_numeric_validation(self):
        for value in (-1, float('nan'), float('inf'), -float('inf')):
            for field in ('capacity','reserve','movement_rate','activity_rate'):
                args = dict(capacity=10, reserve=0, movement_rate=0, activity_rate=0); args[field]=value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): A(**args)
            for field in ('speed_m_per_min','uphill_speed_penalty','roughness_speed_penalty',
                          'uphill_effort_penalty','climb_battery_wh_per_m','hazard_cost_weight','battery_cost_weight'):
                args=dict(speed_m_per_min=1); args[field]=value
                with self.assertRaises(ValueError): MotionModel(**args)
            for field in ('agent_radius_m','safety_margin_m','max_slope_deg','near_obstacle_m',
                          'slope_weight','risk_weight','roughness_weight','proximity_weight'):
                with self.assertRaises(ValueError): Mobility(**{field:value})
        with self.assertRaises(ValueError): MotionModel(0)
        with self.assertRaises(ValueError): A(1,2,0,0)
        self.assertEqual(A(1,1,0,0).reserve, 1)

    def test_exact_reserves_and_short_budget(self):
        p = small_example_profile('astronaut')
        expected = dict(time=6, oxygen=10, water=1.2, battery=18, nutrition=28)
        resources = {k:replace(v, capacity=expected[k]+v.reserve) for k,v in p.resources.items()}
        p = replace(p, resources=resources)
        planner=ResourceMissionPlanner.from_profile(terrain(),p)
        result=planner.plan((0,0),(0,2),2)
        for name, used in zip(('time','oxygen','water','battery','nutrition'), result.total.values()):
            self.assertAlmostEqual(p.resources[name].capacity-used,p.resources[name].reserve)
        for name in resources:
            lower=dict(resources); lower[name]=replace(lower[name],capacity=lower[name].capacity-1e-6)
            with self.assertRaises(NoFeasibleMissionError):
                ResourceMissionPlanner.from_profile(terrain(),replace(p,resources=lower)).plan((0,0),(0,2),2)
        with self.assertRaises(SearchLimitReachedError): planner.plan((0,0),(0,2),2,max_labels=1)

    def test_activity_once_and_zero(self):
        planner=ResourceMissionPlanner.from_profile(terrain(),small_example_profile('astronaut'))
        zero=planner.plan((0,0),(0,2),0)
        self.assertEqual(zero.total.values(), (4,4,.4,8,16,4))
        work=planner.plan((0,0),(0,2),2)
        self.assertEqual(work.total.minutes-zero.total.minutes,2)
        self.assertEqual(work.total.battery_wh-zero.total.battery_wh,10)
        self.assertEqual(work.total.oxygen_u-zero.total.oxygen_u,6)

    def test_mobility(self):
        p=small_example_profile('rover')
        self.assertTrue(ResourceMissionPlanner.from_profile(terrain(),p).nav.traversable((0,0)))
        q=replace(p,mobility=replace(p.mobility,agent_radius_m=.6))
        with self.assertRaises(NoFeasibleMissionError): ResourceMissionPlanner.from_profile(terrain(),q).plan((0,0),(0,2))
        t=terrain(); t.heights_m[0]=[0.,.3,.6]
        for slope, allowed in ((10,False),(30,True)):
            q=replace(p,mobility=replace(p.mobility,max_slope_deg=slope))
            self.assertEqual(ResourceMissionPlanner.from_profile(t,q).nav.traversable((0,1)),allowed)

    def test_metadata(self):
        for kind in ('astronaut','rover'):
            p=small_example_profile(kind)
            self.assertEqual(p.agent_type,kind)
            self.assertEqual(p.parameter_nature,'simulated')
            planner=ResourceMissionPlanner.from_profile(terrain(),p)
            self.assertIs(planner.profile,p)
            for field in ('profile_id','version','parameter_nature','provenance','limitations'):
                with self.assertRaises(ValueError): replace(p,**{field:''})
        with self.assertRaises(ValueError): replace(p,agent_type='drone')
        with self.assertRaises(ValueError): replace(p,resources=dict(p.resources,time=A(10,0,0,1)))

if __name__ == '__main__': unittest.main()
