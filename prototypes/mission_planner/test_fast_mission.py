import unittest
from expanded_ui import ExpandedBridge
from mars_route_planner import RiskAwareAStar,Terrain,RouteSearchLimitReachedError


class FastMission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.b=ExpandedBridge()

    def test_actual_route_rebudgeting_succeeds_without_changing_reserves(self):
        q=self.b.defaults('regional','astronaut')
        q.update(planning_method='fast',goal=[50,80],obstacles=[[49,60],[50,60],[51,60]])
        v=self.b.calculate(q,'compare');a=v['result']['alternatives'][0]
        self.assertEqual(a['reason_code'],'FAST_ROUTE_NEEDS_RESOURCES')
        self.assertIsNone(a['plan']);self.assertIsNotNone(v['candidate_plan'])
        self.assertEqual(v['waypoints'],[])
        reserves={k:r['reserve'] for k,r in q['profile']['resources'].items() if r['status']=='modeled'}
        candidate=v['candidate_plan']['path']
        for r in a['mission_conditions']['resources']:
            k=r['resource'];q['remaining'][k]=max(q['remaining'][k],r['required_initial'])
            q['profile']['resources'][k]['capacity']=max(q['profile']['resources'][k]['capacity'],q['remaining'][k])
        after=self.b.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(after['status'],'SUCCESS')
        self.assertEqual(candidate,after['plan']['path'])
        for k,r in after['plan']['total']['resources'].items():
            if r['status']=='modeled':self.assertEqual(r['reserve'],reserves[k]);self.assertGreaterEqual(r['margin_above_reserve'],-1e-9)

    def test_blocked_goal_cannot_be_fixed_by_resources(self):
        q=self.b.defaults('regional','rover');q.update(planning_method='fast',obstacles=[q['goal'][:]])
        a=self.b.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['reason_code'],'NO_GEOMETRIC_ROUTE')
        self.assertNotIn('mission_conditions',a)

    def test_completed_activity_not_recharged_and_rover_humans_not_applicable(self):
        q=self.b.defaults('regional','rover');q.update(planning_method='fast',activity_status='completed',activity_min=0.)
        a=self.b.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['status'],'SUCCESS')
        self.assertFalse(any(e['kind']=='science' for e in a['plan']['events']))
        self.assertIn(q['goal'],a['plan']['path'])
        self.assertEqual(a['plan']['total']['resources']['water']['status'],'not_applicable')

    def test_bounded_astar_separates_interruption_from_no_route(self):
        t=Terrain([[0.]*8 for _ in range(8)],[[False]*8 for _ in range(8)],[[0.]*8 for _ in range(8)],[[0.]*8 for _ in range(8)],20.)
        from mars_route_planner import PlannerConfig
        nav=RiskAwareAStar(t,PlannerConfig())
        with self.assertRaises(RouteSearchLimitReachedError):nav.plan((1,1),(6,6),max_expansions=1)
        self.assertEqual(nav.plan((1,1),(6,6)).cells[-1],(6,6))
