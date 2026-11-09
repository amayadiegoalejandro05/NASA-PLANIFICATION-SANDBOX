"""Unit coordinates/contracts and explicitly SYNTHETIC nodata/integrity fixtures.

Coordinate and CORE tests require only the standard library. NPZ fixture tests
use optional NumPy; real-product integration is in test_stage04_integration.py.
"""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jezero_adapter import (CTX_URL, RESAMPLING, VERTICAL_REFERENCE, CropWindow,
                             GridMapping, digest, load_ctx_crop, strict_json, validate_metadata)
from mars_route_planner import RiskAwareAStar

HAS_NUMPY = importlib.util.find_spec("numpy") is not None


def synthetic_metadata():
    wkt = ('PROJCS["synthetic unit fixture",GEOGCS["Mars",DATUM["Mars",'
           'SPHEROID["Mars sphere",3396190,0]]],PROJECTION["Equirectangular"],'
           'PARAMETER["standard_parallel_1",18.45],PARAMETER["latitude_of_origin",18.45],'
           'PARAMETER["central_meridian",77.45],PARAMETER["false_easting",0],'
           'PARAMETER["false_northing",0],UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]')
    return dict(schema_version=1, dataset_type="USGS_MRO_REAL_RASTER_CROPS", shape=[8, 8],
                cell_m=4., side_m=32., affine_gdal=[-16., 4., 0., 16., 0., -4.],
                row_order="north_to_south", longitude_direction="east", mars_sphere_radius_m=3396190,
                vertical_reference=VERTICAL_REFERENCE, resampling=RESAMPLING, local_crs_wkt=wkt,
                center_lon_east_deg=77.45, center_lat_planetocentric_deg=18.45,
                terrain_sha256="0"*64, origin_z_m=-99999.,
                sources=dict(prior=dict(url=CTX_URL, instrument="MRO/CTX", doi="10.5066/P906QQT8",
                                        native_post_spacing_m=20, source_pixel_size=[20., 20.],
                                        source_window_sha256="1"*64, source_nodata="-3.4028226550889045e+38",
                                        source_shape=[100, 100], window_col_row_width_height=[1, 1, 5, 5],
                                        source_crs_wkt=wkt, valid_fraction=1.,
                                        citation="SYNTHETIC TEST FIXTURE, not an observed product")))


class CoordinateUnits(unittest.TestCase):
    def setUp(self):
        self.g = GridMapping((128, 128), (-256., 4., 0., 256., 0., -4.), CropWindow(60, 60, 7, 7))

    def test_centers_orientation_and_inverse(self):
        g = self.g
        self.assertEqual(g.product_cell_jezero((0, 0)), (-254., 254.))
        self.assertEqual(g.product_cell_jezero((127, 127)), (254., -254.))
        self.assertEqual(g.cell_jezero((0, 0)), (-14., 14.))
        self.assertEqual(g.cell_jezero((1, 0)), (-14., 10.))
        self.assertEqual(g.cell_jezero((0, 1)), (-10., 14.))
        self.assertEqual(g.cell_planner((0, 0)), (2., 2.))
        self.assertEqual(g.cell_planner((1, 0)), (2., 6.))
        for cell in ((0, 0), (6, 6), (4, 2), (2, 4), (3, 3)):
            self.assertEqual(g.from_product_cell(g.to_product_cell(cell)), cell)
            self.assertEqual(g.jezero_to_cell(g.cell_jezero(cell)), cell)
            self.assertEqual(g.jezero_to_product_cell(g.cell_jezero(cell)), g.to_product_cell(cell))
            self.assertEqual(g.planner_to_cell(g.cell_planner(cell)), cell)
            self.assertEqual(g.planner_to_jezero(g.cell_planner(cell)), g.cell_jezero(cell))
            self.assertEqual(g.jezero_to_planner(g.cell_jezero(cell)), g.cell_planner(cell))

    def test_corners_and_half_open_bounds(self):
        g = self.g
        self.assertEqual(g.corner_jezero(0, 0), (-16., 16.))
        self.assertEqual(g.corner_jezero(7, 7), (12., -12.))
        self.assertEqual(g.planner_to_jezero((28., 28.)), (12., -12.))
        self.assertEqual(g.jezero_to_planner((12., -12.)), (28., 28.))
        self.assertEqual(g.jezero_to_cell((-16., 16.)), (0, 0))
        self.assertEqual(g.jezero_to_cell((-12., 12.)), (1, 1))
        self.assertEqual(g.planner_to_cell((4., 4.)), (1, 1))
        for xy in ((12., 0.), (0., -12.), (-16.0001, 0.), (0., 16.0001)):
            with self.subTest(xy=xy), self.assertRaises(ValueError):
                g.jezero_to_cell(xy)
        for xy in ((28., 1.), (1., 28.), (-.001, 0.), (0., -.001)):
            with self.subTest(xy=xy), self.assertRaises(ValueError):
                g.planner_to_cell(xy)
        self.assertEqual(g.jezero_to_product_cell((-256., 256.)), (0, 0))
        for xy in ((256., 0.), (0., -256.)):
            with self.assertRaises(ValueError):
                g.jezero_to_product_cell(xy)

    def test_crop_position_and_rejections(self):
        g = self.g
        self.assertEqual(g.to_product_cell((4, 2)), (64, 62))
        self.assertEqual(g.cell_jezero((4, 2)), (-6., -2.))
        self.assertEqual(g.cell_jezero((2, 4)), (2., 6.))
        self.assertEqual(g.metadata()["crop_affine_gdal"], [-16., 4., 0., 16., 0., -4.])
        for cell in ((7, 0), (-1, 0), (True, 0), (1., 0), [0, 0]):
            with self.assertRaises(ValueError):
                g.to_product_cell(cell)
        for window in (CropWindow(127, 0, 2, 1), CropWindow(0, 128, 1, 1)):
            with self.assertRaises(ValueError):
                replace(g, window=window)
        for args in ((0, 0, 0, 1), (-1, 0, 1, 1), (0, False, 1, 1)):
            with self.assertRaises(ValueError):
                CropWindow(*args)
        for affine in ((0., 0., 0., 0., 0., 0.), (0., 4., 1., 0., 0., -4.),
                       (0., 4., 0., 0., 0., 4.)):
            with self.assertRaises(ValueError):
                replace(g, affine_gdal=affine)

    def test_metadata_contract_rejections(self):
        good = synthetic_metadata()
        validate_metadata(good)
        changes = dict(shape=[8, 9], cell_m=20., side_m=31., affine_gdal=[-16., 4., 0., 16., 0., 4.],
                       row_order="south_to_north", longitude_direction="west", mars_sphere_radius_m=6378137,
                       vertical_reference="WGS84", schema_version=True, terrain_sha256="oops",
                       local_crs_wkt=good["local_crs_wkt"].replace("3396190", "6378137"),
                       center_lon_east_deg=77.46, resampling="nearest")
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_metadata(dict(good, **{key: value}))
        for key, value in dict(instrument="MRO/HiRISE", native_post_spacing_m=1,
                               source_pixel_size=[1., 1.], valid_fraction=2.,
                               window_col_row_width_height=[99, 99, 2, 2]).items():
            bad = deepcopy(good)
            bad["sources"]["prior"][key] = value
            with self.subTest(source_key=key), self.assertRaises(ValueError):
                validate_metadata(bad)
        with self.assertRaises(ValueError):
            validate_metadata({})

    def test_core_and_transform_import_without_optional_dependencies(self):
        script = """
import builtins
original = builtins.__import__
def restricted(name, *a, **k):
    if name.split('.')[0] in {'numpy','rasterio','pyproj','matplotlib','scipy'}:
        raise AssertionError('CORE attempted optional import: '+name)
    return original(name, *a, **k)
builtins.__import__ = restricted
import mars_route_planner, mars_mission_resources, mission_api, jezero_adapter
from demo_stage03 import example_request
assert mission_api.plan_mission(example_request('rover')).status.value == 'SUCCESS'
"""
        run = subprocess.run([sys.executable, "-S", "-c", script], cwd=Path(__file__).parent,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)


@unittest.skipUnless(HAS_NUMPY, "Optional NumPy missing: synthetic NPZ fixtures require requirements-jezero.txt")
class SyntheticNpzUnits(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.prior = np.arange(64, dtype=np.float32).reshape(8, 8)
        self.meta = synthetic_metadata()
        self.write()

    def write(self, reference_shape=(8, 8), valid_shape=(8, 8)):
        import numpy as np
        np.savez_compressed(self.folder/"terrain.npz", prior=self.prior,
                            reference=np.full(reference_shape, -888., dtype=np.float32),
                            valid=np.zeros(valid_shape, dtype=bool))
        self.meta["terrain_sha256"] = digest((self.folder/"terrain.npz").read_bytes())
        self.write_meta()

    def write_meta(self):
        (self.folder/"metadata.json").write_text(json.dumps(self.meta), encoding="utf-8")

    def test_nodata_is_none_and_blocked_no_filling_or_vertical_offset(self):
        import numpy as np
        self.prior[2, 2] = np.nan
        self.prior[2, 3] = np.inf
        self.prior[3, 2] = np.float32(float(self.meta["sources"]["prior"]["source_nodata"]))
        self.meta["sources"]["prior"]["valid_fraction"] = 61/64
        self.write()
        a = load_ctx_crop(self.folder, CropWindow(1, 1, 4, 4))
        nav = RiskAwareAStar(a.terrain.snapshot)
        for cell in ((1, 1), (1, 2), (2, 1)):
            self.assertIsNone(a.terrain.snapshot.heights_m[cell[0]][cell[1]])
            self.assertFalse(nav.traversable(cell))
        self.assertEqual(a.terrain.snapshot.heights_m[0][0], 9.)
        self.assertEqual(a.terrain.snapshot.resolution_m, 4.)
        self.assertEqual(a.provenance["crop_unknown_cells"], 3)
        self.assertEqual(a.provenance["coordinates"]["height_offset_applied_m"], 0.)
        self.assertEqual(a.mapping.cell_jezero((0, 0)), (-10., 10.))

    def test_only_ctx_payload_is_read_even_with_invalid_joint_mask(self):
        import numpy as np
        original = np.lib.npyio.NpzFile.__getitem__
        accessed = []
        def guarded(product, key):
            accessed.append(key)
            self.assertEqual(key, "prior", "Held-out payload was accessed")
            return original(product, key)
        with patch.object(np.lib.npyio.NpzFile, "__getitem__", guarded):
            a = load_ctx_crop(self.folder, CropWindow(1, 1, 3, 3))
        self.assertEqual(accessed, ["prior"])
        self.assertEqual(a.provenance["parent_unknown_cells"], 0)
        self.assertEqual(a.terrain.snapshot.heights_m[0][0], 9.)
        self.assertFalse(a.provenance["inventory"]["reference"]["decoded"])
        self.assertFalse(a.provenance["inventory"]["valid"]["decoded"])

    def test_integrity_and_all_layer_dimensions_rejected(self):
        with (self.folder/"terrain.npz").open("ab") as f:
            f.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            load_ctx_crop(self.folder, CropWindow(1, 1, 2, 2))
        for ref, valid in (((7, 8), (8, 8)), ((8, 8), (8, 7))):
            self.write(ref, valid)
            with self.assertRaisesRegex(ValueError, "dimensions"):
                load_ctx_crop(self.folder, CropWindow(1, 1, 2, 2))
        self.prior = self.prior[:7]
        self.write()
        with self.assertRaisesRegex(ValueError, "dimensions"):
            load_ctx_crop(self.folder, CropWindow(1, 1, 2, 2))

    def test_validity_metadata_rejected_and_provenance_hash_detached(self):
        self.meta["sources"]["prior"]["valid_fraction"] = .5
        self.write_meta()
        with self.assertRaisesRegex(ValueError, "valid fraction"):
            load_ctx_crop(self.folder, CropWindow(1, 1, 2, 2))
        self.meta["sources"]["prior"]["valid_fraction"] = 1.
        self.write_meta()
        a = load_ctx_crop(self.folder, CropWindow(1, 1, 2, 2))
        b = load_ctx_crop(self.folder, CropWindow(2, 1, 2, 2))
        p = a.provenance
        expected = p.pop("adaptation_sha256")
        self.assertEqual(digest(strict_json(p).encode("utf-8")), expected)
        self.assertNotEqual(expected, b.provenance["adaptation_sha256"])
        p["source"]["instrument"] = "changed"
        self.assertEqual(a.provenance["source"]["instrument"], "MRO/CTX")


if __name__ == "__main__":
    unittest.main()
