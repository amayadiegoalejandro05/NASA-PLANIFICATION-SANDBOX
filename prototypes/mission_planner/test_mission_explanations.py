"""Explanations must be evidence-based and never change planning semantics."""
import unittest
from regional_ui import RegionalBridge


class MissionExplanations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.bridge=RegionalBridge()

    def test_three_obstacles_does_not_invent_a_single_failure_cause(self):
        q=self.bridge.defaults('regional','astronaut')
        q['obstacles']=[[11,11],[12,11],[13,11]]
        v=self.bridge.calculate(q,'compare')
        a=v['result']['alternatives'][0]
        self.assertEqual(a['status'],'INFEASIBLE')
        self.assertEqual(a['ui_diagnostic']['kind'],'NO_ADMISSIBLE_PLAN')
        self.assertIn('3 obstáculos',a['ui_diagnostic']['next_step'])
        self.assertNotIn('resources',a['ui_diagnostic'])
        self.assertEqual(q['remaining']['battery'],100.)
        q['obstacles']=[]
        a=self.bridge.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['status'],'SUCCESS')
        self.assertIsNone(a['ui_diagnostic'])

    def test_resource_shortfall_is_a_bound_from_engine_not_a_route(self):
        q=self.bridge.defaults('regional','astronaut');q['goal']=[12,16]
        a=self.bridge.calculate(q,'compare')['result']['alternatives'][0]
        d=a['ui_diagnostic'];self.assertEqual(a['status'],'INFEASIBLE')
        self.assertEqual(d['kind'],'RESOURCE_LOWER_BOUND_EXCEEDED')
        self.assertEqual(d['minimum_future_distance_m'],240.)
        battery=next(v for v in d['resources'] if v['resource']=='battery')
        self.assertEqual(battery['minimum_consumption'],128.)
        self.assertEqual(battery['available_above_reserve'],90.)
        self.assertEqual(battery['minimum_shortfall'],38.)
        self.assertIn('No es una ruta',d['scope'])
        q['scenario']='conservative'
        a=self.bridge.calculate(q,'compare')['result']['alternatives'][0]
        battery=next(v for v in a['ui_diagnostic']['resources'] if v['resource']=='battery')
        self.assertAlmostEqual(battery['minimum_consumption'],128.*1.2)

    def test_endpoint_obstacle_and_below_reserve_have_specific_messages(self):
        q=self.bridge.defaults('regional','astronaut');q['obstacles']=[q['goal'][:]]
        a=self.bridge.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['ui_diagnostic']['kind'],'POINT_ON_SIMULATED_OBSTACLE')
        self.assertIn('El destino',a['ui_diagnostic']['summary'])
        q['obstacles']=[];q['remaining']['battery']=9.
        a=self.bridge.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['ui_diagnostic']['kind'],'BALANCE_BELOW_RESERVE')
        self.assertIn('batería',a['ui_diagnostic']['summary'])

    def test_interruption_remains_unknown_not_resource_rejection(self):
        q=self.bridge.defaults('regional','astronaut');q['max_labels']=1
        a=self.bridge.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['status'],'SEARCH_LIMIT_REACHED')
        self.assertEqual(a['ui_diagnostic']['kind'],'INTERRUPTED')
        self.assertNotIn('resources',a['ui_diagnostic'])


if __name__=='__main__':unittest.main()
