"""Transport/adapter regressions, without a browser or duplicate planner oracle."""
from copy import deepcopy
import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from mission_ui import MissionBridge, UIInputError, make_server, strict
from mission_decisions import compare_alternatives


class StageSix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = MissionBridge()
        cls.server = make_server(cls.bridge, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def http(self, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        try:
            conn.request('GET' if body is None else 'POST', path, body=body, headers=headers or {})
            result = conn.getresponse()
            return result.status, dict(result.getheaders()), result.read()
        finally:
            conn.close()

    def config(self):
        return self.bridge.defaults('ctx', 'astronaut')

    def test_http_real_ctx_and_current_inputs(self):
        q = self.config()
        code, headers, body = self.http('/api/calculate', strict({'configuration':q,'action':'compare'}))
        self.assertEqual(code, 200)
        result = json.loads(body)
        direct = compare_alternatives(self.bridge.build(q)).to_dict()
        for a, b in zip(result['result']['alternatives'], direct['alternatives']):
            self.assertEqual(a['status'], 'SUCCESS')
            self.assertEqual(a['plan'], b['plan'])
        q['activity_min'] = 3.
        changed = self.bridge.calculate(q, 'compare')
        self.assertNotEqual(result['input_sha256'], changed['input_sha256'])
        self.assertAlmostEqual(changed['result']['alternatives'][0]['plan']['total']['duration_min']-
                               result['result']['alternatives'][0]['plan']['total']['duration_min'], 1.)
        self.assertIn('no-store', headers['Cache-Control'])

    def test_exports_frames_identity_and_strict_json(self):
        v = self.bridge.calculate(self.config(), 'compare')
        self.assertEqual(json.loads(strict(v)), v)
        self.assertEqual(v['request']['schema_version'], '5.0')
        self.assertEqual(v['terrain']['revision_sha256'], v['request']['state']['terrain_revision_sha256'])
        for w in v['waypoints']:
            x,y = w['planner_xy_m']
            self.assertEqual(w['east_north_m'], [-16+x,16-y])
            self.assertEqual(w['height_m'], self.bridge.ctx.terrain.snapshot.heights_m[w['cell'][0]][w['cell'][1]])
        self.assertEqual(v['provenance']['input_layer'], 'prior')
        self.assertEqual(v['result']['distinct_successful_routes'], 1)

    def test_selection_checks_and_new_snapshot_restore(self):
        q = self.config()
        original = self.bridge.terrain(q)[0].revision_sha256
        self.assertTrue(self.bridge.inspect(q, [3,3])['traversable'])
        q['obstacles'] = [[3,3]]
        self.assertFalse(self.bridge.inspect(q, [3,3])['traversable'])
        self.assertNotEqual(self.bridge.terrain(q)[0].revision_sha256, original)
        self.assertEqual(self.bridge.ctx.terrain.revision_sha256, original)
        self.assertEqual(q['current'], [3,3])
        q['obstacles'] = []
        self.assertEqual(self.bridge.terrain(q)[0].revision_sha256, original)
        for cell in ([7,0],[-1,0],[1.2,3],[True,0]):
            with self.assertRaises(UIInputError):
                self.bridge.inspect(q,cell)

    def test_continue_return_completed_and_balances(self):
        q=self.config()
        q.update(activity_status='completed', activity_min=0.)
        q['remaining']['battery']=80.
        v=self.bridge.calculate(q,'evaluate')['result']
        self.assertEqual(v['decision'],'CONTINUE')
        self.assertIn(q['goal'],v['continuation']['plan']['path'])
        for key in ('continuation','returning'):
            a=v[key]
            self.assertFalse(any(e['kind']=='science' for e in a['plan']['events']))
            b=a['plan']['total']['resources']['battery']
            self.assertEqual(b['capacity'],80.)
            self.assertEqual(b['reserve'],10.)
            self.assertAlmostEqual(b['remaining'],80.-b['consumed'])
            self.assertEqual(a['request']['profile']['resources']['battery']['capacity'],100.)
        self.assertIsNone(v['returning']['plan']['goal_cell'])

    def test_all_statuses_and_construction_errors(self):
        q=self.config()
        q['remaining']['battery']=9.
        v=self.bridge.calculate(q,'evaluate')['result']
        self.assertEqual(v['continuation']['status'],'INFEASIBLE')
        self.assertEqual(v['continuation']['reason_code'],'BALANCE_BELOW_RESERVE')
        q=self.config();q['max_labels']=1
        v=self.bridge.calculate(q,'evaluate')['result']
        self.assertEqual(v['continuation']['status'],'SEARCH_LIMIT_REACHED')
        self.assertEqual(v['decision'],'REVIEW_RETURN_UNCONFIRMED')
        q=self.config();q['goal']=q['base'][:]
        v=self.bridge.calculate(q,'evaluate')
        self.assertEqual(v['result']['decision'],'REVIEW_INVALID_INPUT')
        self.assertIsNone(v['request'])
        for key,value in [('max_labels',5001),('max_labels',1.2),('max_labels',True),('activity_min',-1.)]:
            q=self.config();q[key]=value
            code,_,body=self.http('/api/calculate',strict({'configuration':q,'action':'compare'}))
            self.assertEqual(code,400)
            self.assertEqual(json.loads(body)['status'],'INVALID_INPUT')

    def test_rover_and_explicit_exclusion(self):
        q=self.bridge.defaults('ctx','rover')
        v=self.bridge.calculate(q,'compare')
        for k in ('oxygen','water','nutrition'):
            self.assertEqual(v['result']['alternatives'][0]['plan']['total']['resources'][k]['status'],'not_applicable')
        q=self.config();q['profile']['resources']['water']={'status':'excluded','reason':'Ensayo de interfaz; no modelado'}
        del q['remaining']['water']
        v=self.bridge.calculate(q,'compare')
        self.assertEqual(v['result']['alternatives'][0]['plan']['total']['resources']['water']['reason'],'Ensayo de interfaz; no modelado')
        q['profile']['resources']['water']['reason']=''
        with self.assertRaises(UIInputError):self.bridge.calculate(q,'compare')

    def test_synthetic_detour_policies_and_conservative(self):
        q=self.bridge.defaults('synthetic','rover')
        v=self.bridge.calculate(q,'compare')
        self.assertTrue(all(a['status']=='SUCCESS' for a in v['result']['alternatives']))
        self.assertGreater(v['result']['distinct_successful_routes'],1)
        q['obstacles']=[[3,3]]
        updated=self.bridge.calculate(q,'compare')
        for a in updated['result']['alternatives']:
            if a['plan']:self.assertNotIn([3,3],a['plan']['path'])
        q=self.config();q['scenario']='conservative';q['factor']=1.2
        v=self.bridge.calculate(q,'compare')
        self.assertEqual(v['request']['scenario']['factors']['time'],1.)
        self.assertEqual(v['result']['alternatives'][0]['effective_profile']['resources']['battery']['movement_rate'],2.4)

    def test_http_scope_invalid_json_and_static(self):
        self.assertEqual(self.server.server_address[0],'127.0.0.1')
        for path in ('/','/app.js','/style.css','/api/catalog'):
            self.assertEqual(self.http(path)[0],200)
        self.assertEqual(self.http('/../mission_decisions.py')[0],404)
        self.assertEqual(self.http('/api/catalog',headers={'Host':'other.example'})[0],403)
        self.assertEqual(self.http('/api/calculate','{}',{'Origin':'https://other.example'})[0],403)
        self.assertEqual(self.http('/api/calculate','{"configuration":NaN}')[0],400)
        self.assertEqual(self.http('/api/calculate','{')[0],400)
        self.assertEqual(self.http('/api/calculate','x'*65537)[0],400)

    def test_http_rejects_duplicate_work_and_internal_error_is_not_invalid_input(self):
        started=threading.Event();release=threading.Event();responses=[]
        original=self.bridge.calculate
        def blocked(*args):
            started.set();release.wait(4);return original(*args)
        body=strict({'configuration':self.config(),'action':'compare'})
        with patch.object(self.bridge,'calculate',side_effect=blocked):
            first=threading.Thread(target=lambda:responses.append(self.http('/api/calculate',body)[0]))
            first.start()
            self.assertTrue(started.wait(2))
            try:self.assertEqual(self.http('/api/calculate',body)[0],409)
            finally:release.set();first.join()
        self.assertEqual(responses,[200])
        with patch('mission_ui.compare_alternatives',side_effect=ValueError('fixture unexpected internal failure')):
            with patch('traceback.print_exc'):
                code,_,body=self.http('/api/calculate',body)
            self.assertEqual(code,500)
            self.assertEqual(json.loads(body)['status'],'INTERNAL_ERROR')

    def test_core_has_no_server_dependency(self):
        script = '''
import builtins, sys
real = builtins.__import__
def guarded(name,*args,**kwargs):
    if name in ('mission_ui','http.server','socket','webbrowser'):
        raise AssertionError('CORE attempted UI/server import: '+name)
    return real(name,*args,**kwargs)
builtins.__import__=guarded
from demo_stage05 import make_request
from mission_decisions import evaluate_options
assert evaluate_options(make_request()).to_dict()['decision']=='CONTINUE'
assert 'mission_ui' not in sys.modules
'''
        result=subprocess.run([sys.executable,'-S','-c',script],cwd=Path(__file__).parent,
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
