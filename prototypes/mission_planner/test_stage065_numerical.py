"""Independent finite arithmetic fixtures; see docs/NUMERICAL_MODEL_AUDIT.md.

Expected quantities below are hand accounts, never obtained from Consumption.
"""
from dataclasses import replace
import json
import math
import subprocess
import sys
import unittest
from unittest.mock import patch

from demo_stage05 import flat_terrain, make_request
from mars_mission_resources import (Consumption, Usage, Budget, ResourceAllocation,
    ExcludedResource, MotionModel, Mobility, ResourceMissionPlanner, small_example_profile)
from mars_route_planner import Terrain, PlannerConfig, RiskAwareAStar
from mission_api import (MissionRequest, TerrainReference, LocalFrame, plan_mission,
                         _breakdown, USAGE_FIELDS)
from mission_decisions import (plan_future, RateScenario, MissionState,
    effective_future_profile, nominal_scenario)
from numeric_domain import NumericDomainError


def audit_profile(agent='astronaut'):
    p = small_example_profile(agent)
    # Deliberately distinct reserves and movement/activity rates.
    resources = dict(time=ResourceAllocation(1000, 10, 1, 1),
                     battery=ResourceAllocation(1000, 7, 2, 5))
    if agent == 'astronaut':
        resources.update(oxygen=ResourceAllocation(1000, 3, 1, 3),
                         water=ResourceAllocation(1000, .2, .1, .4),
                         nutrition=ResourceAllocation(1000, 11, 4, 6))
    return replace(p, resources=resources)


class IndependentAccounts(unittest.TestCase):
    def assertUsage(self, actual, expected):
        # Order: min, simulated_u, L, Wh, kcal, m.
        for value, wanted in zip(actual.values(), expected):
            self.assertAlmostEqual(value, wanted, places=10)

    def test_flat_ascent_descent_rough_diagonal(self):
        c = Consumption(10, 1, .1, 2, 4, climb_battery_wh_per_m=3)
        # d=10, v=10 => 1 min. +2m => g=.2, t=1.4, effort=1.4.
        cases = [(10, 0, 0, (1, 1, .1, 2, 4, 10)),
                 (10, 2, 0, (1.4, 1.96, .196, 8.8, 7.84, 10)),
                 (10, -2, 0, (1, 1, .1, 2, 4, 10)),
                 (10, 0, .4, (1.2, 1.2, .12, 2.4, 4.8, 10)),
                 (10*math.sqrt(2), 0, 0, (math.sqrt(2), math.sqrt(2),
                    .1*math.sqrt(2), 2*math.sqrt(2), 4*math.sqrt(2), 10*math.sqrt(2)))]
        for d, z, rough, expected in cases:
            with self.subTest(d=d, z=z, rough=rough):
                self.assertUsage(c.traveling(d, z, rough), expected)

    def test_stationary_and_distinct_activity_rates(self):
        self.assertUsage(Consumption(1, 3, .4, 5, 6).stationary(2),
                         (2, 6, .8, 10, 12, 0))
        planner = ResourceMissionPlanner.from_profile(flat_terrain(1, 3), audit_profile())
        self.assertUsage(planner.consumption.traveling(2, 0, 0), (2, 2, .2, 4, 8, 2))
        self.assertUsage(planner.activity_consumption.stationary(2), (2, 6, .8, 10, 12, 0))

    def test_roundtrip_completed_initial_goal_and_direct_returns(self):
        p = audit_profile()
        # (current, complete, return_only, hand total).
        cases = [((0, 0), False, False, (6, 10, 1.2, 18, 28, 4)),
                 ((0, 0), True, False, (4, 4, .4, 8, 16, 4)),
                 ((0, 2), False, False, (4, 8, 1, 14, 20, 2)),
                 ((0, 1), False, True, (1, 1, .1, 2, 4, 1)),
                 ((0, 0), False, True, (0, 0, 0, 0, 0, 0))]
        for current, completed, returning, expected in cases:
            q = make_request(profile=p, current=current, activity=0 if completed else 2)
            if completed:
                q = replace(q, state=replace(q.state, activity_status='completed'))
            r = plan_future(q, 'return' if returning else 'continue')
            with self.subTest(current=current, completed=completed, returning=returning):
                self.assertEqual(r.status.value, 'SUCCESS')
                plan = r.plan
                total = plan['total']
                self.assertAlmostEqual(total['duration_min'], expected[0])
                self.assertAlmostEqual(total['distance_m'], expected[5])
                for k, wanted in zip(('time','oxygen','water','battery','nutrition'), expected[:5]):
                    self.assertAlmostEqual(total['resources'][k]['consumed'], wanted)
                self.check_breakdown(plan)
                self.assertEqual(sum(e['kind']=='science' for e in plan['events']),
                                 int(not completed and not returning))
                if current == (0, 2) and not returning:
                    self.assertEqual(plan['events'][0]['kind'], 'science')
                if returning:
                    self.assertIsNone(plan['goal_index'])
                json.loads(r.to_json(), parse_constant=lambda x: self.fail(x))

    def check_breakdown(self, plan):
        for resource in USAGE_FIELDS:
            if plan['total']['resources'][resource]['status'] != 'modeled':
                continue
            cumulative = 0
            for event in plan['events']:
                cumulative += event['incremental'][resource]
                self.assertAlmostEqual(event['cumulative'][resource], cumulative)
                self.assertAlmostEqual(event['resources'][resource]['remaining'],
                    event['resources'][resource]['capacity']-cumulative)
            self.assertAlmostEqual(cumulative, plan['total']['resources'][resource]['consumed'])
            self.assertAlmostEqual(sum(p['consumed'][resource] for p in plan['phases'].values()), cumulative)
            for phase, values in plan['phases'].items():
                self.assertAlmostEqual(values['consumed'][resource], sum(
                    e['incremental'][resource] for e in plan['events'] if e['phase']==phase))

    def test_geometry_units_and_weighted_cost(self):
        # Uniform risk .5, rough .4, slope/proximity weights 0 => 1+2*.5+1.5*.4=2.6.
        t = Terrain([[0.]*2 for _ in range(2)], [[False]*2 for _ in range(2)],
                    [[.5]*2 for _ in range(2)], [[.4]*2 for _ in range(2)], 10)
        nav = RiskAwareAStar(t, PlannerConfig(rover_radius_m=0, safety_margin_m=0,
                                             slope_weight=0, proximity_weight=0))
        route = nav.plan((0,0),(1,1))
        self.assertAlmostEqual(route.distance_m, 10*math.sqrt(2))
        self.assertAlmostEqual(route.total_cost, 26*math.sqrt(2))
        self.assertEqual(route.waypoints_xy_m, [(5,5),(15,15)])
        # Rise 2/10 gives 11.3099 degrees, not 20 degrees or 20m distance.
        t = Terrain([[0.,2.,4.]], [[False]*3], [[0.]*3], [[0.]*3], 10)
        nav = RiskAwareAStar(t, PlannerConfig(rover_radius_m=0, safety_margin_m=0))
        self.assertAlmostEqual(nav._edge((0,0),(0,1))[2], math.degrees(math.atan(.2)))

    def test_shared_accounting_same_sloped_path_v3_v5(self):
        t = TerrainReference.capture(Terrain([[0.,2.,4.]], [[False]*3],
                    [[0.]*3], [[.4]*3], 10), 'audit-slope')
        p = replace(audit_profile(), motion=MotionModel(10, climb_battery_wh_per_m=3))
        q = make_request(terrain=t, profile=p, current=(0,0))
        v5 = plan_future(q)
        v3 = plan_mission(MissionRequest('3.0','audit',t,q.frame,(0,0),(0,0),(0,2),2,p,5000))
        self.assertEqual(v3.status.value, 'SUCCESS')
        self.assertEqual(v3.plan['path'], v5.plan['path'])
        # Uphill two edges (1.6min, effort1.4), downhill two (1.2min), activity2.
        expected = dict(time=7.6, oxygen=12.88, water=1.488, battery=33.2, nutrition=39.52)
        for k, wanted in expected.items():
            self.assertAlmostEqual(v3.plan['total']['resources'][k]['consumed'], wanted)
            self.assertAlmostEqual(v5.plan['total']['resources'][k]['consumed'], wanted)
        self.check_breakdown(v3.plan)

    def test_scenario_scales_rates_only(self):
        p = replace(audit_profile(), motion=MotionModel(10, climb_battery_wh_per_m=3))
        q = make_request(profile=p)
        factors = {k: (1 if k=='time' else 2) for k in q.scenario.factors}
        nominal = effective_future_profile(q)
        conservative = effective_future_profile(replace(q,scenario=RateScenario('conservative',factors,'audit')))
        self.assertEqual(nominal.motion, conservative.motion)
        for k, item in nominal.resources.items():
            other = conservative.resources[k]
            self.assertEqual((item.capacity,item.reserve),(other.capacity,other.reserve))
            self.assertEqual(other.movement_rate,item.movement_rate*factors[k])
            self.assertEqual(other.activity_rate,item.activity_rate*factors[k])
        _, movement, _, activity = conservative._engine_inputs()
        # Double 2 Wh/min, but climb remains 2m*3 Wh/m => 11.6 Wh (not 17.6).
        self.assertAlmostEqual(movement.traveling(10,2,0).battery_wh,11.6)
        self.assertAlmostEqual(activity.stationary(2).battery_wh,20)


class BudgetAndDomain(unittest.TestCase):
    def test_exact_insufficient_and_tolerance(self):
        q = make_request(profile=audit_profile(), current=(0,0))
        used = dict(time=6,battery=18,oxygen=10,water=1.2,nutrition=28)
        balances = {k: used[k]+a.reserve for k,a in q.profile.resources.items()}
        q = replace(q,state=replace(q.state,remaining=balances,historical_consumption={'battery':123}))
        r = plan_future(q)
        self.assertEqual(r.status.value,'SUCCESS')
        for k,v in r.plan['total']['resources'].items():
            self.assertAlmostEqual(v['remaining'], q.state.reserves[k])
            self.assertAlmostEqual(v['margin_above_reserve'],0)
        for k in balances:
            with self.subTest(resource=k):
                low = replace(q,state=replace(q.state,remaining=dict(balances,**{k:balances[k]-1e-7})))
                self.assertEqual(plan_future(low).status.value,'INFEASIBLE')
        b = Budget(10,3,battery_wh=8,battery_reserve_wh=2)
        self.assertTrue(b.fits(Usage(7,battery_wh=6)))
        self.assertTrue(b.fits(Usage(7+5e-10,battery_wh=6)))
        self.assertFalse(b.fits(Usage(7+2e-9,battery_wh=6)))

    def test_zero_capacity_equal_reserve_and_below(self):
        p = replace(audit_profile('rover'),resources=dict(time=ResourceAllocation(10,10,1,1),
                                                       battery=ResourceAllocation(7,7,0,0)))
        q = make_request(profile=p,current=(0,0),activity=0)
        self.assertEqual(plan_future(q,'return').status.value,'SUCCESS')
        self.assertEqual(plan_future(q).status.value,'INFEASIBLE')
        q = replace(q,state=replace(q.state,remaining={'time':9,'battery':7}))
        self.assertEqual(plan_future(q,'return').to_dict()['reason_code'],'BALANCE_BELOW_RESERVE')

    def test_applicability_at_events_phases_totals_json(self):
        p = audit_profile()
        p = replace(p,resources=dict(p.resources,water=ExcludedResource('audit exclusion'),
                                     oxygen=ResourceAllocation(10,2,0,0)))
        for profile in (p,audit_profile('rover')):
            q = make_request(profile=profile,current=(0,0))
            data = plan_future(q).to_dict()
            for k in ('water','oxygen','nutrition'):
                status = profile.resource_status(k)
                total = data['plan']['total']['resources'][k]
                self.assertEqual(total['status'],status)
                for e in data['plan']['events']:
                    self.assertEqual(e['resources'][k]['status'],status)
                    if status!='modeled':
                        self.assertIsNone(e['incremental'][k]);self.assertIsNone(e['resources'][k]['remaining'])
                for phase in data['plan']['phases'].values():
                    if status!='modeled':self.assertIsNone(phase['consumed'][k])
                if status!='modeled':
                    for name in ('capacity','consumed','reserve','remaining','margin_above_reserve'):
                        self.assertIsNone(total[name])
                elif k=='oxygen':self.assertEqual(total['consumed'],0)
        with self.assertRaises(ValueError):
            replace(audit_profile('rover'),resources=dict(audit_profile('rover').resources,
                    oxygen=ResourceAllocation(1,0,0,0)))

    def test_invalid_public_numbers(self):
        invalid = [True,False,float('nan'),float('inf'),-float('inf'),'1',None,10**400]
        for x in invalid:
            factories = [lambda:Consumption(x), lambda:ResourceAllocation(x,0,0,0),
                         lambda:Budget(x,0), lambda:MotionModel(x), lambda:PlannerConfig(risk_weight=x),
                         lambda:Mobility(agent_radius_m=x),
                         lambda:Terrain([[0.]],[[False]],[[0.]],[[0.]],x),
                         lambda:Consumption(1).stationary(x),
                         lambda:Consumption(1).traveling(1,x,0)]
            for fn in factories:
                with self.subTest(value=repr(x)),self.assertRaises(ValueError):fn()
        for args in ((0,0,0),(-1,0,0),(1,0,-.1),(1,0,1.1),(True,0,0),(1,0,True)):
            with self.subTest(args=args),self.assertRaises(ValueError):Consumption(1).traveling(*args)
        with self.assertRaises(ValueError):Consumption(1).stationary(-1)
        for name in ('risk','roughness','heights_m'):
            for x in (True,'1',float('nan')):
                params=dict(heights_m=[[0.]],obstacles=[[False]],risk=[[0.]],roughness=[[0.]],resolution_m=1)
                params[name]=[[x]]
                with self.assertRaises(ValueError):Terrain(**params)

    def test_overflow_usage_addition_and_geometry_are_not_infeasibility(self):
        with self.assertRaises(NumericDomainError):Consumption(1e308).traveling(1e-308,0,0)
        with self.assertRaises(NumericDomainError):Consumption(1,battery_wh_per_min=1e308).traveling(2,0,0)
        with self.assertRaises(NumericDomainError):Usage(1e308)+Usage(1e308)
        with self.assertRaises(ValueError):Usage(oxygen_u=float('inf'))
        t = Terrain([[0.,0.]],[[False]*2],[[1.]*2],[[0.]*2],2)
        with self.assertRaises(NumericDomainError):
            RiskAwareAStar(t,PlannerConfig(rover_radius_m=0,safety_margin_m=0,risk_weight=1e308)).plan((0,0),(0,1))
        with self.assertRaises(NumericDomainError):
            RiskAwareAStar(Terrain([[-1e308,1e308]],[[False]*2],[[0.]*2],[[0.]*2],1))

    def test_overflow_facades_strict_json_and_unexpected_error(self):
        p = replace(audit_profile('rover'),motion=MotionModel(1e-308))
        q = make_request(profile=p,current=(0,0))
        for r in (plan_future(q),plan_mission(MissionRequest('3.0','overflow',q.terrain,q.frame,
                    (0,0),(0,0),(0,2),2,p,5000))):
            self.assertEqual(r.status.value,'INVALID_INPUT')
            self.assertEqual(r.to_dict()['reason_code'],'NUMERIC_DOMAIN_EXCEEDED')
            self.assertIsNone(r.plan)
            json.loads(r.to_json(),parse_constant=lambda x:self.fail(x))
        q = make_request()
        q = replace(q,scenario=RateScenario('conservative',dict(q.scenario.factors,battery=1e308),'audit'))
        self.assertEqual(plan_future(q).to_dict()['reason_code'],'NUMERIC_DOMAIN_EXCEEDED')
        q = make_request(profile=replace(audit_profile('rover'),motion=MotionModel(1,hazard_cost_weight=1e308)))
        # Roughness penalty gives a finite edge, but the detailed weighted cost overflows.
        t = TerrainReference.capture(Terrain([[0.]*3],[[False]*3],[[1.]*3],[[0.]*3],1),'cost')
        q = make_request(terrain=t,profile=q.profile,current=(0,0))
        self.assertEqual(plan_future(q).to_dict()['reason_code'],'NUMERIC_DOMAIN_EXCEEDED')
        with patch.object(ResourceMissionPlanner,'movement_usage',side_effect=RuntimeError('internal defect')):
            with self.assertRaisesRegex(RuntimeError,'internal defect'):plan_future(make_request())

    def test_core_importable_without_site_packages(self):
        code = 'import mars_route_planner,mars_mission_resources,mission_api,mission_decisions;import sys;assert not any(k in sys.modules for k in ("numpy","mission_ui","fast_mission","http.server","rclpy"))'
        result = subprocess.run([sys.executable,'-S','-c',code],cwd=__import__('pathlib').Path(__file__).parent,
                                capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


class FastAccounting(unittest.TestCase):
    def bridge(self, q):
        from types import SimpleNamespace
        return SimpleNamespace(build=lambda config:q,
            mapping=SimpleNamespace(cell_jezero=lambda cell:((cell[1]+.5)*q.frame.resolution_m,
                                                           -(cell[0]+.5)*q.frame.resolution_m)),
            region_provenance={'nature':'synthetic audit fixture'})

    def test_large_finite_activity_same_chronological_sum(self):
        from fast_mission import fast_calculate
        p = audit_profile('rover')
        p = replace(p,motion=MotionModel(10),resources={k:replace(a,capacity=1e10) for k,a in p.resources.items()})
        q = make_request(profile=p,current=(0,0),activity=1e8)
        result = fast_calculate(self.bridge(q),{'obstacles':[]})
        self.assertEqual(result['result']['alternatives'][0]['status'],'SUCCESS')
        detailed = plan_future(q)
        self.assertEqual(result['candidate_plan']['total'],detailed.plan['total'])

    def test_preparation_complete_candidate_preserves_rates_and_scenario(self):
        from fast_mission import fast_calculate
        # All rising edges, roughness and activity must be counted before sizing.
        p = replace(audit_profile(),motion=MotionModel(10,climb_battery_wh_per_m=3))
        t = TerrainReference.capture(Terrain([[0.,2.,4.]],[[False]*3],[[0.]*3],[[.4]*3],10),'prep')
        q = make_request(terrain=t,profile=p,current=(0,0))
        factors = {k:1 if k=='time' else 1.25 for k in q.scenario.factors}
        q = replace(q,scenario=RateScenario('conservative',factors,'audit'),
            state=replace(q.state,remaining=dict(q.state.remaining,battery=8)))
        before = fast_calculate(self.bridge(q),{'obstacles':[]})
        self.assertEqual(before['result']['alternatives'][0]['reason_code'],'FAST_ROUTE_NEEDS_RESOURCES')
        candidate = before['candidate_plan']
        # Two uphill 1.6min*2.5Wh/min+6Wh, two downhill 1.2min*2.5Wh/min,
        # science 2min*6.25Wh/min => 38.5Wh +7Wh absolute reserve=45.5Wh.
        resources = before['result']['alternatives'][0]['mission_conditions']['resources']
        self.assertAlmostEqual(next(r['required_initial'] for r in resources if r['resource']=='battery'),45.5)
        balances = dict(q.state.remaining)
        for r in resources:balances[r['resource']] = max(balances[r['resource']],r['required_initial'])
        self.assertEqual({k for k in balances if balances[k]!=q.state.remaining[k]},{'battery'})
        newq = replace(q,state=replace(q.state,remaining=balances))
        after = fast_calculate(self.bridge(newq),{'obstacles':[]})
        self.assertEqual(after['result']['alternatives'][0]['status'],'SUCCESS')
        self.assertEqual(after['candidate_plan']['path'],candidate['path'])
        self.assertEqual(newq.profile,q.profile);self.assertEqual(newq.scenario,q.scenario)
        self.assertEqual(newq.state.reserves,q.state.reserves)
        self.assertAlmostEqual(after['candidate_plan']['total']['resources']['battery']['margin_above_reserve'],0)
        strict = json.dumps(after,allow_nan=False)
        self.assertIn('simulated_u',strict)
        # Same path, same consumption under detailed search, not a promise of same optimum.
        detailed = plan_future(newq)
        self.assertEqual(detailed.status.value,'SUCCESS')
        self.assertEqual(detailed.plan['path'],candidate['path'])
        for k in USAGE_FIELDS:
            self.assertAlmostEqual(detailed.plan['total']['resources'][k]['consumed'],
                                   after['candidate_plan']['total']['resources'][k]['consumed'])

    def test_fast_overflow_is_construction_error_not_infeasibility(self):
        from fast_mission import fast_calculate
        from mission_ui import UIInputError
        p = replace(audit_profile('rover'),motion=MotionModel(1e-308))
        q = make_request(profile=p,current=(0,0))
        with self.assertRaises(UIInputError):fast_calculate(self.bridge(q),{'obstacles':[]})


if __name__=='__main__':unittest.main()
