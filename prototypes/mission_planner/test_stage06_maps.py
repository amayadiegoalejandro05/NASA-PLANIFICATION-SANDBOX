"""Regional acceptance tests: spatial contracts and real CTX engine integration."""
from copy import deepcopy
import http.client
import json
import math
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from regional_ui import RegionalBridge
from jezero_map import en_to_planet, planet_to_en, RADIUS, raster
from mission_ui import make_server, UIInputError
from jezero_adapter import CropWindow,load_ctx_crop


class RegionalMaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=RegionalBridge()

    def test_independent_control_points_axes_and_pixel_centers(self):
        # Controls from the parent affine: full parent NW=(-256,256), crop starts
        # at source edge (4,4) -> (-240,240); coarse NW centre=(-230,230).
        self.assertEqual(self.b.mapping.cell_jezero((0,0)),(-230.,230.))
        self.assertEqual(self.b.mapping.cell_jezero((23,23)),(230.,-230.))
        self.assertEqual(en_to_planet(0,0),[18.45,77.45])
        # Independent arc-length controls on the declared 3396190 m sphere.
        self.assertAlmostEqual(planet_to_en(19.45,77.45)[1],59274.69752330622,places=6)
        self.assertAlmostEqual(planet_to_en(18.45,78.45)[0],56228.020953,delta=2.)
        for cell in ((0,0),(12,12),(23,23)):
            en=self.b.mapping.cell_jezero(cell)
            ll=en_to_planet(*en)
            self.assertEqual(self.b.mapping.jezero_to_cell(planet_to_en(*ll)),cell)
        for en in ((240,0),(0,-240),(-241,0),(0,241)):
            with self.assertRaises(ValueError):self.b.mapping.jezero_to_cell(en)

    def test_aggregation_matches_original_prior_only(self):
        from mission_ui import ROOT
        raw=load_ctx_crop(ROOT/'data/jezero',CropWindow(4,4,120,120))
        expected=sum(raw.terrain.snapshot.heights_m[r][c] for r in range(5) for c in range(5))/25
        self.assertEqual(self.b.region.snapshot.heights_m[0][0],expected)
        self.assertEqual(self.b.region.snapshot.resolution_m,20.)
        self.assertEqual((self.b.region.snapshot.rows,self.b.region.snapshot.cols),(24,24))
        self.assertEqual(self.b.region_provenance['source']['input_layer'],'prior')
        self.assertFalse(self.b.region_provenance['source']['inventory']['reference']['decoded'])

    def test_geographic_selection_no_relocation_and_outside_explanation(self):
        q=self.b.defaults('regional','astronaut')
        point=en_to_planet(-29.,-11.)
        v=self.b.select(q,point)
        self.assertEqual(v['cell'],[12,10])
        self.assertAlmostEqual(v['adjustment_m'],math.sqrt(2),places=6)
        self.assertNotEqual(v['chosen_latlon'],v['used_latlon'])
        q['obstacles']=[[12,10]]
        self.assertFalse(self.b.select(q,point)['traversable'])
        self.assertEqual(self.b.select(q,point)['cell'],[12,10])
        with self.assertRaisesRegex(UIInputError,'fuera de la cobertura'):
            self.b.select(q,[18.6,77.45])

    def test_new_mission_mode_is_authoritative(self):
        q=self.b.defaults('regional','rover')
        self.assertEqual(q['current'],q['base'])
        q['current']=[12,11]
        with self.assertRaisesRegex(UIInputError,'deben coincidir'):
            self.b.calculate(q,'compare')
        q['mission_mode']='ongoing'
        v=self.b.calculate(q,'evaluate')
        self.assertEqual(v['result']['decision'],'CONTINUE')
        self.assertIsNone(v['result']['returning']['plan']['goal_cell'])

    def test_finite_regional_missions_and_export_alignment(self):
        for agent in ('astronaut','rover'):
            q=self.b.defaults('regional',agent)
            v=self.b.calculate(q,'compare')
            self.assertTrue(all(x['status']=='SUCCESS' for x in v['result']['alternatives']))
            self.assertEqual(v['result']['alternatives'][0]['plan']['total']['distance_m'],80.)
            for w in v['waypoints']:
                self.assertEqual(w['east_north_m'],list(self.b.mapping.cell_jezero(tuple(w['cell']))))
                self.assertEqual(w['latlon'],en_to_planet(*w['east_north_m']))
            q['activity_min']=3.
            changed=self.b.calculate(q,'compare')
            self.assertNotEqual(v['input_sha256'],changed['input_sha256'])
            self.assertAlmostEqual(changed['result']['alternatives'][0]['plan']['total']['duration_min']-
                                   v['result']['alternatives'][0]['plan']['total']['duration_min'],1.)
        q=self.b.defaults('regional','astronaut');q['remaining']['battery']=9.
        self.assertEqual(self.b.calculate(q,'compare')['result']['alternatives'][0]['status'],'INFEASIBLE')
        q=self.b.defaults('regional','astronaut');q['max_labels']=1
        v=self.b.calculate(q,'evaluate')['result']
        self.assertEqual(v['continuation']['status'],'SEARCH_LIMIT_REACHED')
        self.assertEqual(v['decision'],'REVIEW_CONTINUATION_UNKNOWN')

    def test_visual_products_do_not_change_planning_snapshot(self):
        before=self.b.region.revision_sha256
        for kind in ('relief','elevation'):
            data,legend=raster(self.b.region,kind)
            self.assertTrue(data.startswith(b'\x89PNG'))
            self.assertEqual(legend['resolution_m'],20.)
        self.assertEqual(before,self.b.region.revision_sha256)
        q=self.b.defaults('regional','rover');q['obstacles']=[[11,11]]
        self.assertNotEqual(before,self.b.terrain(q)[0].revision_sha256)
        q['obstacles']=[]
        self.assertEqual(before,self.b.terrain(q)[0].revision_sha256)

    def test_regional_http_catalog_selection_and_png(self):
        server=make_server(self.b,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            c.request('GET','/api/catalog');r=c.getresponse();catalog=json.loads(r.read())
            self.assertEqual(r.status,200)
            self.assertEqual(catalog['maps']['regional']['rows'],24)
            for path in ('/regional-relief.png','/regional-elevation.png','/vendor/leaflet.js','/map-app.js'):
                c.request('GET',path);r=c.getresponse();self.assertEqual(r.status,200);self.assertTrue(r.read())
            q=self.b.defaults('regional','rover');c.request('POST','/api/select',json.dumps({'configuration':q,'point':en_to_planet(-30,-10)}))
            r=c.getresponse();v=json.loads(r.read());self.assertEqual(r.status,200);self.assertEqual(v['cell'],[12,10]);c.close()
        finally:server.shutdown();server.server_close();thread.join()

    def test_real_script_entrypoint_preserves_validation_error_identity(self):
        # Import-only tests miss duplicate __main__/mission_ui class identities.
        process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('mission_ui.py')),'--port','0'],
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
        try:
            line=process.stdout.readline()
            self.assertIn('http://127.0.0.1:',line)
            port=int(line.split('http://127.0.0.1:')[1].split()[0])
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
            q=self.b.defaults('regional','astronaut');q['activity_min']=-1.
            c.request('POST','/api/calculate',json.dumps({'configuration':q,'action':'compare'}))
            r=c.getresponse();v=json.loads(r.read());c.close()
            self.assertEqual(r.status,400)
            self.assertEqual(v['status'],'INVALID_INPUT')
        finally:
            process.terminate();process.communicate(timeout=10)


if __name__=='__main__':unittest.main()
