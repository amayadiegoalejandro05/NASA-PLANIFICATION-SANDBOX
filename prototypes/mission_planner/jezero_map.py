"""Explicit planetary display transforms and bounded CTX regional aggregation.

Only the existing public CTX prior is decoded. Display imagery is never input
to planning. No Earth CRS and no HiRISE elevations.
"""
from dataclasses import asdict
import json
import math
import struct
import zlib
from jezero_adapter import CropWindow, GridMapping, load_ctx_crop, digest, strict_json
from mars_route_planner import Terrain
from mission_api import TerrainReference

RADIUS = 3396190.
LON0, LAT0 = 77.45, 18.45


def en_to_planet(east, north):
    return [LAT0 + math.degrees(north/RADIUS),
            LON0 + math.degrees(east/(RADIUS*math.cos(math.radians(LAT0))))]


def planet_to_en(lat, lon):
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in (lat, lon)):
        raise ValueError('Coordenadas planetarias finitas requeridas')
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Latitud planetocéntrica/longitud este fuera de rango')
    return [RADIUS*math.radians(lon-LON0)*math.cos(math.radians(LAT0)),
            RADIUS*math.radians(lat-LAT0)]


def regional(folder):
    adapted = load_ctx_crop(folder, CropWindow(4,4,120,120))
    t = adapted.terrain.snapshot
    heights=[]
    for r in range(24):
        row=[]
        for c in range(24):
            values=[t.heights_m[y][x] for y in range(r*5,r*5+5) for x in range(c*5,c*5+5)]
            row.append(sum(values)/25 if all(v is not None for v in values) else None)
        heights.append(row)
    zero=[[0.]*24 for _ in range(24)]
    ref=TerrainReference.capture(Terrain(heights,[[False]*24 for _ in range(24)],zero,zero,20.),'jezero-ctx-regional-480m-20m')
    mapping=GridMapping((24,24),(-240.,20.,0.,240.,0.,-20.),CropWindow(0,0,24,24))
    provenance=dict(source=adapted.provenance, derived_schema='ctx-regional-1',
        aggregation='Area mean of 5x5 existing 4 m CTX prior samples; any unknown -> unknown; no filling',
        source_native_resolution_m=20, input_grid_resolution_m=4, output_grid_resolution_m=20,
        parent_window=[4,124,4,124], bounds_east_north_m=[-240,-240,240,240],
        loss='Averages the upstream bilinear prior; smooths extremes, no native detail recovered',
        scientific_limit='Regional DEM average does not resolve rocks, paths or subcell hazards',
        mapping=mapping.metadata(), snapshot=ref.identity(), display_convention='Planetocentric latitude, east longitude; sphere radius 3396190 m',
        display_to_jezero='E=R*cos(lat0)*(lon-lon0) radians; N=R*(lat-lat0) radians',
        layers_do_not_enter_planner=True)
    provenance['derivation_sha256']=digest(strict_json(provenance).encode())
    return ref,mapping,provenance


def png(rgb):
    h,w=len(rgb),len(rgb[0])
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+bytes(v for pixel in row for v in pixel) for row in rgb)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


def raster(ref,kind):
    """Display-only elevation color and hillshade, never consumption inputs."""
    import numpy as np
    a=np.array([[v if v is not None else float('nan') for v in row] for row in ref.snapshot.heights_m])
    lo,hi=float(np.nanmin(a)),float(np.nanmax(a))
    if kind=='relief':
        south,east=np.gradient(a,ref.snapshot.resolution_m)
        # Normal dot light from NW, 45 degrees altitude; south-positive grid.
        light=(-.5,-.5,math.sqrt(.5))
        v=np.clip((-east*light[0]-south*light[1]+light[2])/np.sqrt(1+east**2+south**2),0,1)
        shade=(45+v*190).astype('uint8')
        pixels=[[(int(x),)*3 for x in row] for row in shade]
    else:
        v=np.clip((a-lo)/max(hi-lo,1e-9),0,1)
        pixels=[[(int(40+x*195),int(105+x*65),int(154-x*100)) for x in row] for row in v]
    return png(pixels),dict(min_m=lo,max_m=hi,kind=kind,resolution_m=ref.snapshot.resolution_m,
        illumination='Calculated NW azimuth 315°, altitude 45°' if kind=='relief' else 'Added color; absolute CTX elevation in m')


LAYERS={
    'orbital':dict(product='JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0',extension='png',max_zoom=13,
        source='NASA MRO / CTX · USGS / NASA Trek',type='Mosaico orbital controlado, escala de grises',resolution='6 m/píxel nativo',
        bounds=[[18.2110274,77.1604655],[18.7211945,77.6991776]],
        limitation='Cobertura parcial del cráter; no revela transitabilidad. Solo visualización.'),
    'relief':dict(product='Mars_MOLA_blend200ppx_HRSC_Shade_clon0dd_200mpp_lzw',extension='jpg',max_zoom=8,
        source='NASA MGS / MOLA + ESA Mars Express / HRSC · NASA Trek',type='Relieve sombreado derivado de DEM',resolution='200 m/píxel de producto; resolución de origen variable',
        bounds=[[-89.999224,-180],[90,179.9984479]],limitation='Contexto global; detalle regional sustituido explícitamente por sombreado CTX local.'),
}
