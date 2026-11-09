"""One bounded CTX acquisition; offline runtime uses the resulting JSON only."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import numpy as np
import rasterio
from rasterio.warp import reproject, transform_bounds, transform, Resampling
from rasterio.windows import from_bounds, Window
from rasterio.transform import from_origin
from jezero_adapter import CTX_URL

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/mission_planner_ctx_2km'


def main():
    OUT.mkdir(exist_ok=True)
    if (OUT/'terrain.json').exists():
        raise RuntimeError('Prepared data already exists; refusing to overwrite evidence')
    target='+proj=eqc +lat_ts=18.45 +lat_0=18.45 +lon_0=77.45 +R=3396190 +units=m +no_defs'
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
        with rasterio.open(CTX_URL) as src:
            box=transform_bounds(target,src.crs,-1000,-1000,1000,1000,densify_pts=21)
            win=from_bounds(*box,src.transform)
            left,top=math.floor(win.col_off)-2,math.floor(win.row_off)-2
            win=Window(left,top,math.ceil(win.width)+4,math.ceil(win.height)+4)
            raw=src.read(1,window=win,masked=True)
            if not np.all(~raw.mask):raise RuntimeError('Unknown source elevations; no fill authorized')
            np.save(OUT/'source-window.npy',raw.data,allow_pickle=False)
            dest=np.full((100,100),np.nan,dtype='float32')
            reproject(raw.data,dest,src_transform=src.window_transform(win),src_crs=src.crs,
                      src_nodata=src.nodata,dst_transform=from_origin(-1000,1000,20,20),dst_crs=target,
                      dst_nodata=np.nan,resampling=Resampling.average)
            if not np.all(np.isfinite(dest)):raise RuntimeError('Incomplete output coverage; no fill authorized')
            payload=json.dumps(dict(resolution_m=20.,heights_m=dest.tolist()),allow_nan=False,separators=(',',':')).encode()
            (OUT/'terrain.json').write_bytes(payload)
            lon,lat=transform(target,src.crs.geodetic_crs if hasattr(src.crs,'geodetic_crs') else '+proj=longlat +R=3396190', [0.,1000.],[0.,1000.])
            meta=dict(schema='ctx-bounded-window-1',retrieved_utc=datetime.now(timezone.utc).isoformat(),url=CTX_URL,
                      source_instrument='MRO/CTX',source_native_resolution_m=20,source_crs=src.crs.to_wkt(),
                      source_transform=list(src.transform),source_window=[win.col_off,win.row_off,win.width,win.height],
                      source_window_transform=list(src.window_transform(win)),source_window_sha256=hashlib.sha256((OUT/'source-window.npy').read_bytes()).hexdigest(),
                      output_sha256=hashlib.sha256(payload).hexdigest(),output_crs=target,bounds_en_m=[-1000,-1000,1000,1000],
                      shape=[100,100],resolution_m=20,method='GDAL average reproject; no upsampling, no unknown fill',
                      rasterio_version=rasterio.__version__,vertical_reference='MOLA topography / DeltaGeoid; absolute CTX heights, no offset',
                      control_points=dict(local_en_m=[[0,0],[1000,1000]],longitude_east=lon,latitude_planetocentric=lat),
                      limitations=['No HiRISE read','No observed local obstacle/risk/roughness layers','20 m cannot resolve rocks','Not whole Jezero'])
            (OUT/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
            print('Prepared CTX 2 km, 100x100 at 20 m; source window',win,flush=True)


if __name__=='__main__':main()
