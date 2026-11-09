"""Bounded CTX-only adapter. No simulator, search, resampling or consumption model.

NumPy is imported only inside load_ctx_crop. HiRISE and the joint valid mask are
inventoried by NPY headers, never decoded or passed to the planner. Metadata
validation intentionally supports the existing Jezero importer's schema only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
import re
from zipfile import ZipFile

from mars_route_planner import Terrain
from mission_api import LocalFrame, TerrainReference

CTX_URL = ("https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/"
           "CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif")
VERTICAL_REFERENCE = "source product MOLA topography / DeltaGeoid; no Earth datum conversion"
RESAMPLING = "bilinear; CTX remains 20 m information on the 4 m computational grid"


def strict_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class CropWindow:
    row: int
    column: int
    rows: int
    columns: int

    def __post_init__(self):
        _require(all(type(v) is int for v in asdict(self).values()), "Window requires integers")
        _require(self.row >= 0 and self.column >= 0 and self.rows > 0 and self.columns > 0,
                 "Invalid crop window")


@dataclass(frozen=True)
class GridMapping:
    """Product/crop cells (row,column), planner XY east/south, Jezero XY east/north.

    Raster containment is half open in index space: [0, rows) x [0, columns).
    Thus west/north outer edges belong to the raster; east/south edges do not.
    Vertex/transport methods separately allow all outer corners, without clipping.
    """
    parent_shape: tuple[int, int]
    affine_gdal: tuple[float, float, float, float, float, float]
    window: CropWindow

    def __post_init__(self):
        _require(type(self.parent_shape) is tuple and len(self.parent_shape) == 2
                 and all(type(v) is int and v > 0 for v in self.parent_shape), "Invalid shape")
        a = self.affine_gdal
        _require(type(a) is tuple and len(a) == 6 and all(_finite(v) for v in a), "Invalid affine")
        _require(a[1] > 0 and a[2] == a[4] == 0 and a[5] == -a[1],
                 "Only aligned square pixels, east/right and north/up, are supported")
        w = self.window
        _require(type(w) is CropWindow, "CropWindow required")
        _require(w.row + w.rows <= self.parent_shape[0]
                 and w.column + w.columns <= self.parent_shape[1], "Crop outside parent")

    @property
    def resolution_m(self):
        return self.affine_gdal[1]

    @property
    def frame(self):
        return LocalFrame("JEZERO_CTX_CROP_EAST_SOUTH", self.resolution_m, (0., 0.))

    def _cell(self, cell, shape):
        _require(type(cell) is tuple and len(cell) == 2 and all(type(v) is int for v in cell),
                 "Cell requires (row,column) integers")
        _require(all(0 <= v < n for v, n in zip(cell, shape)), "Cell outside raster")

    def to_product_cell(self, cell):
        self._cell(cell, (self.window.rows, self.window.columns))
        return cell[0] + self.window.row, cell[1] + self.window.column

    def from_product_cell(self, cell):
        self._cell(cell, self.parent_shape)
        local = cell[0] - self.window.row, cell[1] - self.window.column
        self._cell(local, (self.window.rows, self.window.columns))
        return local

    def corner_jezero(self, row_edge, column_edge):
        _require(type(row_edge) is int and type(column_edge) is int
                 and 0 <= row_edge <= self.window.rows
                 and 0 <= column_edge <= self.window.columns, "Vertex outside crop")
        a, w = self.affine_gdal, self.window
        return (a[0] + (w.column + column_edge)*a[1],
                a[3] + (w.row + row_edge)*a[5])

    def product_cell_jezero(self, cell):
        self._cell(cell, self.parent_shape)
        a = self.affine_gdal
        return a[0] + (cell[1]+.5)*a[1], a[3] + (cell[0]+.5)*a[5]

    def cell_jezero(self, cell):
        return self.product_cell_jezero(self.to_product_cell(cell))

    def cell_planner(self, cell):
        self.to_product_cell(cell)
        return tuple(self.frame.waypoint(cell))

    def planner_to_cell(self, xy):
        self._xy(xy)
        x, y = xy
        s, w = self.resolution_m, self.window
        _require(0 <= x < w.columns*s and 0 <= y < w.rows*s, "Point outside crop")
        return math.floor(y/s), math.floor(x/s)

    @staticmethod
    def _xy(xy):
        _require(isinstance(xy, (tuple, list)) and len(xy) == 2
                 and all(_finite(v) for v in xy), "Finite metric XY required")

    def planner_to_jezero(self, xy):
        self._xy(xy)
        x, y = xy
        s, w = self.resolution_m, self.window
        _require(0 <= x <= w.columns*s and 0 <= y <= w.rows*s, "Point outside crop extent")
        left, top = self.corner_jezero(0, 0)
        return left + x, top - y

    def jezero_to_planner(self, xy):
        self._xy(xy)
        left, top = self.corner_jezero(0, 0)
        result = xy[0]-left, top-xy[1]
        self.planner_to_jezero(result)  # Validate closed extent for coordinate transport.
        return result

    def jezero_to_product_cell(self, xy):
        self._xy(xy)
        a = self.affine_gdal
        row, column = (a[3]-xy[1])/a[1], (xy[0]-a[0])/a[1]
        _require(0 <= row < self.parent_shape[0] and 0 <= column < self.parent_shape[1],
                 "Point outside parent raster")
        return math.floor(row), math.floor(column)

    def jezero_to_cell(self, xy):
        return self.from_product_cell(self.jezero_to_product_cell(xy))

    def metadata(self):
        left, top = self.corner_jezero(0, 0)
        right, bottom = self.corner_jezero(self.window.rows, self.window.columns)
        return dict(parent_shape=list(self.parent_shape), window=asdict(self.window),
                    window_index_bounds="row/column start inclusive, end exclusive",
                    parent_affine_gdal=list(self.affine_gdal),
                    crop_affine_gdal=[left, self.resolution_m, 0., top, 0., -self.resolution_m],
                    jezero_frame="JEZERO_LOCAL_EQUIRECTANGULAR_EAST_NORTH",
                    planner_frame=asdict(self.frame), jezero_bounds_m=[left, bottom, right, top],
                    point_containment="west/north inclusive; east/south exclusive",
                    pixel_centers="(column+0.5,row+0.5); integer edges are outer corners",
                    planner_to_jezero="E=crop_left+X; N=crop_top-Y",
                    height_offset_applied_m=0., interpolation="none; direct crop")


def validate_metadata(meta):
    """Reject incompatible exporter contracts, including contradictory CRS metadata."""
    _require(isinstance(meta, dict), "Metadata object required")
    required = {"schema_version", "dataset_type", "shape", "cell_m", "side_m", "affine_gdal",
                "row_order", "longitude_direction", "mars_sphere_radius_m", "vertical_reference",
                "resampling", "local_crs_wkt", "center_lon_east_deg", "center_lat_planetocentric_deg",
                "sources", "terrain_sha256"}
    _require(required <= meta.keys(), "Missing Jezero metadata fields")
    _require(type(meta["schema_version"]) is int and meta["schema_version"] == 1
             and meta["dataset_type"] == "USGS_MRO_REAL_RASTER_CROPS", "Unsupported dataset schema")
    shape, s = meta["shape"], meta["cell_m"]
    _require(type(shape) is list and len(shape) == 2
             and all(type(n) is int and 0 < n <= 512 for n in shape)
             and shape[0] == shape[1], "Expected bounded square parent shape")
    _require(_finite(s) and s == 4. and _finite(meta["side_m"])
             and meta["side_m"] == shape[0]*s, "Inconsistent computational resolution/extent")
    half = meta["side_m"]/2
    _require(type(meta["affine_gdal"]) is list and len(meta["affine_gdal"]) == 6
             and all(_finite(v) for v in meta["affine_gdal"])
             and meta["affine_gdal"] == [-half, s, 0., half, 0., -s], "Inconsistent affine/extent")
    _require(meta["row_order"] == "north_to_south" and meta["longitude_direction"] == "east"
             and meta["mars_sphere_radius_m"] == 3396190, "Unsupported Mars orientation/sphere")
    _require(meta["vertical_reference"] == VERTICAL_REFERENCE
             and meta["resampling"] == RESAMPLING, "Unsupported height/resampling contract")
    lon, lat = meta["center_lon_east_deg"], meta["center_lat_planetocentric_deg"]
    _require(_finite(lon) and -180 <= lon <= 360 and _finite(lat) and -85 < lat < 85,
             "Invalid planetary centre")
    wkt = meta["local_crs_wkt"]
    _require(isinstance(wkt, str) and 'PROJECTION["Equirectangular"]' in wkt
             and 'AXIS["Easting",EAST]' in wkt and 'AXIS["Northing",NORTH]' in wkt
             and 'UNIT["metre",1' in wkt, "Expected metric Mars equirectangular WKT")
    spheres = re.findall(r'SPHEROID\["[^"]+",([\d.]+),([\d.]+)\]', wkt)
    _require(len(spheres) == 1 and tuple(map(float, spheres[0])) == (3396190., 0.),
             "WKT sphere inconsistent with Mars metadata")
    for name, expected in (("standard_parallel_1", lat), ("latitude_of_origin", lat),
                           ("central_meridian", lon), ("false_easting", 0.), ("false_northing", 0.)):
        values = re.findall(r'PARAMETER\["' + name + r'",([-+\d.eE]+)\]', wkt)
        _require(len(values) == 1 and float(values[0]) == expected, "Inconsistent WKT " + name)
    _require(_hash(meta["terrain_sha256"]), "Invalid terrain SHA-256")
    _require(isinstance(meta["sources"], dict) and isinstance(meta["sources"].get("prior"), dict),
             "Missing CTX source")
    prior = meta["sources"]["prior"]
    _require({"url", "instrument", "doi", "native_post_spacing_m", "source_pixel_size",
              "source_window_sha256", "valid_fraction", "source_nodata", "citation",
              "source_shape", "window_col_row_width_height", "source_crs_wkt"} <= prior.keys(),
             "Missing CTX provenance")
    _require(prior["instrument"] == "MRO/CTX" and prior["url"] == CTX_URL
             and prior["doi"] == "10.5066/P906QQT8" and prior["native_post_spacing_m"] == 20
             and prior["source_pixel_size"] == [20., 20.], "Unsupported CTX product/scale")
    _require(_hash(prior["source_window_sha256"]) and _finite(prior["valid_fraction"])
             and 0 <= prior["valid_fraction"] <= 1, "Invalid source integrity metadata")
    _require(prior["source_nodata"] == "-3.4028226550889045e+38", "Unsupported source nodata")
    source_shape, win = prior["source_shape"], prior["window_col_row_width_height"]
    _require(type(source_shape) is list and len(source_shape) == 2
             and all(type(v) is int and v > 0 for v in source_shape), "Invalid native source shape")
    _require(type(win) is list and len(win) == 4 and all(type(v) is int for v in win)
             and min(win[:2]) >= 0 and min(win[2:]) > 0
             and win[0]+win[2] <= source_shape[1] and win[1]+win[3] <= source_shape[0],
             "Invalid native source window")
    source_wkt = prior["source_crs_wkt"]
    _require(isinstance(source_wkt, str) and 'PROJECTION["Equirectangular"]' in source_wkt
             and '3396190,0' in source_wkt and 'UNIT["metre",1' in source_wkt,
             "Unsupported native Mars CRS")


@dataclass(frozen=True)
class AdaptedTerrain:
    terrain: TerrainReference
    frame: LocalFrame
    mapping: GridMapping
    provenance_json: str

    @property
    def provenance(self):
        return json.loads(self.provenance_json)  # Detached; cannot mutate recorded provenance.


def load_ctx_crop(folder: Path, window: CropWindow) -> AdaptedTerrain:
    import numpy as np  # Optional dependency isolated from CORE and coordinate unit tests.

    folder = Path(folder)
    metadata_bytes = (folder/"metadata.json").read_bytes()
    meta = json.loads(metadata_bytes, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    validate_metadata(meta)
    payload = (folder/"terrain.npz").read_bytes()
    file_hash = digest(payload)
    _require(file_hash == meta["terrain_sha256"], "Terrain SHA-256 mismatch")
    mapping = GridMapping(tuple(meta["shape"]), tuple(meta["affine_gdal"]), window)
    inventory = {}
    # Inspect shapes/dtypes without decoding reference or the HiRISE-dependent mask.
    with ZipFile(BytesIO(payload)) as archive:
        _require(sorted(archive.namelist()) == ["prior.npy", "reference.npy", "valid.npy"],
                 "Unexpected NPZ members")
        for name in ("prior", "reference", "valid"):
            with archive.open(name+".npy") as member:
                version = np.lib.format.read_magic(member)
                _require(version in ((1, 0), (2, 0)), "Unsupported NPY format")
                reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                          else np.lib.format.read_array_header_2_0)
                shape, fortran, dtype = reader(member)
                _require(shape == tuple(meta["shape"]), "NPZ layer dimensions inconsistent: " + name)
                _require(dtype == (np.dtype("bool") if name == "valid" else np.dtype("float32"))
                         and not fortran, "Unexpected dtype/order: " + name)
                inventory[name] = dict(shape=list(shape), dtype=str(dtype), decoded=name == "prior",
                                       role={"prior": "public CTX prior", "reference": "held-out HiRISE",
                                             "valid": "joint CTX/HiRISE mask; not used"}[name])
    with np.load(BytesIO(payload), allow_pickle=False) as product:
        prior = product["prior"]  # The ONLY array payload accessed.
    known = np.isfinite(prior) & (prior != np.float32(float(meta["sources"]["prior"]["source_nodata"])))
    _require(math.isclose(float(known.mean()), meta["sources"]["prior"]["valid_fraction"],
                          rel_tol=0., abs_tol=1e-12), "CTX valid fraction inconsistent")
    w = window
    heights = [[float(prior[r, c]) if known[r, c] else None
                for c in range(w.column, w.column+w.columns)]
               for r in range(w.row, w.row+w.rows)]
    zero = [[0.]*w.columns for _ in range(w.rows)]
    terrain = TerrainReference.capture(Terrain(heights, [[False]*w.columns for _ in range(w.rows)],
                                                zero, zero, mapping.resolution_m),
                                       f"jezero-ctx-r{w.row}-c{w.column}-{w.rows}x{w.columns}")
    provenance = dict(adapter_schema="jezero-ctx-adapter-1", input_layer="prior", input_role="public CTX prior",
                      terrain_file="terrain.npz", metadata_file="metadata.json", terrain_file_sha256=file_hash,
                      adaptation_hash_format="sha256 of canonical JSON excluding adaptation_sha256; sorted keys, ASCII, compact, UTF-8",
                      metadata_file_sha256=digest(metadata_bytes), source=meta["sources"]["prior"],
                      source_window_hash_verification="recorded only; native source tile absent",
                      package_integrity="verified SHA-256 against existing metadata; not an external signature",
                      inventory=inventory, parent_known_cells=int(known.sum()),
                      parent_unknown_cells=int(known.size-known.sum()),
                      crop_unknown_cells=sum(h is None for row in heights for h in row),
                      coordinates=mapping.metadata(), snapshot=terrain.identity(),
                      local_crs_wkt=meta["local_crs_wkt"], mars_sphere_radius_m=meta["mars_sphere_radius_m"],
                      retrieved_utc=meta.get("retrieved_utc"), upstream_versions=meta.get("versions"),
                      center_lat_planetocentric_deg=meta["center_lat_planetocentric_deg"],
                      center_lon_east_deg=meta["center_lon_east_deg"], longitude_direction="east",
                      vertical_reference=meta["vertical_reference"], resampling_upstream=meta["resampling"],
                      height_policy="CTX absolute elevations unchanged; HiRISE-derived origin_z_m ignored",
                      validity_policy="CTX finite and not source nodata; unknown -> None -> CORE blocking; no fill",
                      layers=dict(obstacles="No observed obstacle layer; False means no additional scenario obstacle, not physical absence",
                                  risk="Unavailable; zeros disable additional penalty, not measured zero risk",
                                  roughness="Unavailable; zeros disable additional penalty, not measured smoothness",
                                  slope="Existing CORE gradient and edge slopes from this CTX crop; one-sided at crop boundaries"),
                      limitations=["Real orbital terrain; CTX native 20 m information resampled upstream to 4 m, no new detail",
                                   "Experimental prior-only planning with incomplete local knowledge, no local certification",
                                   "Demonstration targets and agent parameters simulated, no science detection or physical/EVA validation",
                                   "No HiRISE payload, joint validity mask, sensor or estimated/observed state used"])
    provenance["adaptation_sha256"] = digest(strict_json(provenance).encode("utf-8"))
    return AdaptedTerrain(terrain, mapping.frame, mapping, strict_json(provenance))
