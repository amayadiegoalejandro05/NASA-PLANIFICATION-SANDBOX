import hashlib
import json
from pathlib import Path
import unittest
from expanded_ui import ExpandedBridge
from jezero_map import en_to_planet
from mission_ui import UIInputError


class ExpandedWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.b=ExpandedBridge()

    def test_real_source_integrity_and_independent_projection_controls(self):
        folder=Path(__file__).resolve().parents[2]/'data/mission_planner_ctx_2km'
        meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((folder/'terrain.json').read_bytes()).hexdigest(),meta['output_sha256'])
        self.assertEqual(hashlib.sha256((folder/'source-window.npy').read_bytes()).hexdigest(),meta['source_window_sha256'])
        for en,lat,lon in zip(meta['control_points']['local_en_m'],meta['control_points']['latitude_planetocentric'],meta['control_points']['longitude_east']):
            actual=en_to_planet(*en)
            self.assertAlmostEqual(actual[0],lat,places=9)
            self.assertAlmostEqual(actual[1],lon,places=9)
        self.assertEqual(self.b.region.snapshot.rows,100)
        self.assertEqual(self.b.mapping.cell_jezero((0,0)),(-990.,990.))

    def test_selection_beyond_old_window_and_rejection(self):
        q=self.b.defaults('regional','astronaut')
        v=self.b.select(q,en_to_planet(510,-10))
        self.assertEqual(v['cell'],[50,75])
        with self.assertRaises(UIInputError):self.b.select(q,en_to_planet(1010,-10))

    def test_detour_is_real_and_conditions_include_reserves(self):
        q=self.b.defaults('regional','astronaut');q.update(goal=[49,51],obstacles=[[50,50]])
        a=self.b.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['status'],'SUCCESS')
        p=a['plan'];self.assertNotIn([50,50],p['path'])
        self.assertIn([49,49],p['path'])
        directions={(b[0]-a[0],b[1]-a[1]) for a,b in zip(p['path'],p['path'][1:])}
        self.assertGreater(len(directions),2)
        battery=next(v for v in a['mission_conditions']['resources'] if v['resource']=='battery')
        self.assertAlmostEqual(battery['required_initial'],p['total']['resources']['battery']['consumed']+10.)
        self.assertTrue(battery['satisfied'])

    def test_insufficient_and_interrupted_not_automatically_rebudgeted(self):
        q=self.b.defaults('regional','astronaut');q['goal']=[50,60]
        a=self.b.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['status'],'INFEASIBLE')
        self.assertEqual(a['mission_conditions']['kind'],'OPTIMISTIC_MINIMUM')
        self.assertEqual(q['remaining']['battery'],100.)
        q=self.b.defaults('regional','astronaut');q['max_labels']=1
        a=self.b.calculate(q,'compare')['result']['alternatives'][0]
        self.assertEqual(a['status'],'SEARCH_LIMIT_REACHED')
        self.assertNotIn('mission_conditions',a)
