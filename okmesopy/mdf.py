
import numpy as np

import pandas as pd

#import pint

from io import StringIO
import warnings
from urllib.request import urlopen
from datetime import datetime, timedelta
from collections import defaultdict


_url_base = "http://www.mesonet.org/data/public/"


import numpy as np

def _matric_potential(dtref):
    return -2083 / (1 + np.exp(-3.35 * (dtref - 3.17)))

def _vol_water_content(dtref, wcr, wcs, alpha, n):
    mp = _matric_potential(dtref)
    return wcr + (wcs - wcr) / (1 + (-alpha * mp) ** n) ** (1 - 1 / n)


class MesonetTextFile(pd.DataFrame):
    _units = {
        'RELH': 'percent',
        'TAIR': 'deg_C',
        'WSPD': 'm/s',
        'WDIR': 'degrees',
        'RAIN': 'mm',
        'PRES': 'hPa',
        'SRAD': 'W/m^2',
        'TA9M': 'deg_C',
        'WS2M': 'm/s',
        'SKIN': 'deg_C',
    }

    @classmethod
    def from_file_obj(cls, fobj, infer_rows=288):
        txt = fobj.read().decode('utf-8')
        df = pd.read_fwf(StringIO(txt), infer_nrows=infer_rows, skiprows=2)

        _units = MesonetTextFile._units
        unit_cols = list(set(list(df)) & set(list(_units.keys())))
#       df = df.astype({var: f'pint[{_units[var]}]' for var in unit_cols})

        for col in df:
            if col not in ['STID', 'STNM']:
                df.loc[df[col] < -900, col] = float('nan')
        
        dt_line = txt.split("\n")[1]
        dt_base = datetime.strptime(dt_line[5:], "%Y %m %d %H %M %S")

        df['TIME'] = [dt_base + timedelta(minutes=float(t)) for t in df['TIME']]

        meso_file = cls(data=df)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UserWarning)
            meso_file.meta = {}

        return meso_file

    @classmethod
    def from_file(cls, fname):
        # Warn if it looks like the user has the extension wrong.
        with open(fname, 'rb') as fobj:
            mdf = cls.from_file_obj(fobj)

        return mdf

    def append(self, other, **kwargs):
        return concat([self, other], **kwargs)

    def __getitem__(self, *args):
        ret = super(MesonetTextFile, self).__getitem__(*args)

        if type(ret) == pd.DataFrame:
            ret = type(self)(ret)

            with warnings.catch_warnings():
                warnings.simplefilter('ignore', category=UserWarning)
                ret.meta = self.meta

        return ret


class MTS(MesonetTextFile):

    @classmethod
    def from_file_obj(cls, fobj, mts1m=False):
        infer_rows = 1440 if mts1m else 288
        mts = super(MTS, cls).from_file_obj(fobj, infer_rows=infer_rows)

        mts.meta['STID'] = mts['STID'][0]
        mts.meta['STNM'] = mts['STNM'][0]
        mts.meta['RAIN_prev_day'] = {mts.meta['STID']: mts.loc[0, 'RAIN']}
        mts.loc[0, 'RAIN'] = 0.

        mts.set_index('TIME', inplace=True)

        del mts['STID']
        del mts['STNM']

        return mts

    @classmethod
    def from_web(cls, date, stid, mts1m=False):
        if stid.lower() in ['nwcm', 'osub']:
            subpath = 'nwc/mts-1m' if mts1m else 'nwc/mts-5m'
        else:
            if mts1m:
                raise ValueError("1-minute data are unavailable for standard Mesonet sites")
            subpath = 'mesonet/mts'

        url = f"{_url_base}/{subpath}/{date:%Y/%m/%d/%Y%m%d}{stid.lower()}.mts"

        urlobj = urlopen(url)
        return cls.from_file_obj(urlobj, mts1m=mts1m)

    @classmethod
    def _concat(cls, dfs, join='outer'):
        keys = [df.meta['STID'] for df in dfs]

        rain_prev = {}
        rain_prev_accum = defaultdict(int)
        rain_copies = defaultdict(list)

        for key, df in zip(keys, dfs):
            rain_prev_accum[key] += df.meta['RAIN_prev_day'][key]

            df_rain_copy = df['RAIN'].copy()
            df_rain_copy += rain_prev_accum[key]

            rain_copies[key].append(df_rain_copy)
            if key not in rain_prev:
                rain_prev[key] = df.meta['RAIN_prev_day'][key]

        for key, key_rain in rain_copies.items():
            rain_copies[key] = pd.concat(key_rain) - rain_prev[key]

        unique_keys = list(set(keys))

        dfs_keys = defaultdict(list)
        for key, df in zip(keys, dfs):
            dfs_keys[key].append(df)

        for key, key_df in dfs_keys.items():
            dfs_keys[key] = pd.concat(key_df, join=join)

        new_df = pd.concat(dfs_keys, join=join, keys=unique_keys)
        new_df['RAIN'] = pd.concat(rain_copies, keys=unique_keys)

        new_df.index.set_names(['STID', 'TIME'], inplace=True)
        new_df = new_df.swaplevel().sort_index(level=0)

        if len(unique_keys) == 1:
            new_df.set_index(new_df.index.droplevel(level=1), inplace=True)

        new_df = cls(new_df)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UserWarning)
            new_df.meta = {'RAIN_prev_day': rain_prev}
            if len(unique_keys) == 1:
                new_df.meta['STID'] = unique_keys[0]

        return new_df
    
    def compute_soil_vwc(self, geoinfo):
        stn_meta = geoinfo[geoinfo.index == self.meta['STID']]
        depths = [int(col[3:]) for col in geoinfo.columns if col.startswith('WCR')]

        def vwc_at_depth(depth):
            try:
                vwc = _vol_water_content(self[f'TR{depth:02d}'], stn_meta[f'WCR{depth:02d}'].values, stn_meta[f'WCS{depth:02d}'].values, 
                                         stn_meta[f'A{depth:02d}'].values, stn_meta[f'N{depth:02d}'].values)
            except KeyError:
                vwc = None
            return vwc

        vwcs = [ vwc_at_depth(depth) for depth in depths ]
        vwcs = {f'VWC{depth:02d}': vwc for depth, vwc in zip(depths, vwcs) if vwc is not None}

        return pd.DataFrame(vwcs)        


class MDF(MesonetTextFile):

    @classmethod
    def from_file_obj(cls, fobj):
        mdf = super(MDF, cls).from_file_obj(fobj)

        mdf.set_index('STID', inplace=True)

        mdf.meta['TIME'] = mdf['TIME'][0]
        del mdf['TIME']

        return mdf

    @classmethod
    def from_web(cls, date):
        url = f"{_url_base}/mesonet/mdf/{date:%Y/%m/%d/%Y%m%d%H%M}.mdf"

        urlobj = urlopen(url)
        return cls.from_file_obj(urlobj)

    @classmethod
    def _concat(cls, dfs, join='outer'):
        keys = [df.meta['TIME'] for df in dfs]

        new_df = pd.concat(dfs, join=join, keys=keys)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UserWarning)
            new_df.meta = {}
        new_df.index.set_names(['TIME', 'STID'], inplace=True)

        return cls(new_df)

    def compute_soil_vwc(self, geoinfo):
        depths = [int(col[3:]) for col in geoinfo.columns if col.startswith('WCR')]
        geoinfo = geoinfo.drop(geoinfo[~geoinfo.index.isin(self.index)].index)

        def vwc_at_depth(depth):
            try:
                vwc = _vol_water_content(self[f'TR{depth:02d}'], geoinfo[f'WCR{depth:02d}'], geoinfo[f'WCS{depth:02d}'], 
                                         geoinfo[f'A{depth:02d}'], geoinfo[f'N{depth:02d}'])
            except KeyError:
                vwc = None
            return vwc

        vwcs = [ vwc_at_depth(depth) for depth in depths ]
        vwcs = {f'VWC{depth:02d}': vwc for depth, vwc in zip(depths, vwcs) if vwc is not None}

        return pd.DataFrame(vwcs)


def concat(dfs, join='outer'):
    unique_types = list(set(type(df).__name__ for df in dfs))
    if len(unique_types) > 1:
        raise ValueError("Can't handle mixed MTS and MDF files in concatenation")

    return type(dfs[0])._concat(dfs, join=join)
