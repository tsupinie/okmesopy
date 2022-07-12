
import numpy as np

import pandas as pd

def _matric_potential(dtref):
    return -2083 / (1 + np.exp(-3.35 * (dtref - 3.17)))

def _vol_water_content(dtref, wcr, wcs, alpha, n):
    mp = _matric_potential(dtref)
    return wcr + (wcs - wcr) / (1 + (-alpha * mp) ** n) ** (1 - 1 / n)

def compute_soil_vwc(mdf, geoinfo):
    depths = [int(col[3:]) for col in geoinfo.columns if col.startswith('WCR')]
    geoinfo = geoinfo.drop(geoinfo[~geoinfo.index.isin(mdf.index)].index)

    def vwc_at_depth(depth):
        try:
            vwc = _vol_water_content(mdf[f'TR{depth:02d}'], geoinfo[f'WCR{depth:02d}'], geoinfo[f'WCS{depth:02d}'], 
                                     geoinfo[f'A{depth:02d}'], geoinfo[f'N{depth:02d}'])
        except KeyError:
            vwc = None
        return vwc

    vwcs = [ vwc_at_depth(depth) for depth in depths ]
    vwcs = {f'VWC{depth:02d}': vwc for depth, vwc in zip(depths, vwcs) if vwc is not None}

    return pd.DataFrame(vwcs)

if __name__ == "__main__":
    from mdf import MDF
    from geoinfo import OKMesoGeoInfo

    from datetime import datetime

    geoinfo = OKMesoGeoInfo.from_web()

    mdf = MDF.from_web(datetime(2022, 7, 12, 21, 0))
    print(compute_soil_vwc(mdf, geoinfo))