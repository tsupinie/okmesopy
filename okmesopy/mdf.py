
import numpy as np

import pandas as pd

#import pint

from io import StringIO
import warnings
from urllib.request import urlopen
from datetime import datetime, timedelta
from collections import defaultdict


_url_base = "http://www.mesonet.org/data/public/"

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
    def from_file_obj(cls, fobj):
        txt = fobj.read().decode('utf-8')
        df = pd.read_fwf(StringIO(txt), infer_nrows=288, skiprows=2)

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
        if 'sort' not in kwargs:
            kwargs['sort'] = False

        other_rain = other['RAIN'].copy()
        other_rain += other.meta['RAIN_prev_day']

        new_df = super(MesonetTextFile, self).append(other, **kwargs)
        new_df['RAIN'] = self['RAIN'].append(other_rain)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UserWarning)
            new_df.meta = self.meta

        return new_df


class MTS(MesonetTextFile):

    @classmethod
    def from_file_obj(cls, fobj):
        mts = super(MTS, cls).from_file_obj(fobj)

        mts.meta['RAIN_prev_day'] = mts.loc[0, 'RAIN']
        mts.loc[0, 'RAIN'] = 0.

        mts.set_index('TIME', inplace=True)

        mts.meta['STID'] = mts['STID'][0]
        mts.meta['STNM'] = mts['STNM'][0]

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
        return cls.from_file_obj(urlobj)

    @classmethod
    def _concat(cls, dfs, join='outer'):
        keys = [df.meta['STID'] for df in dfs]

        rain_prev_accum = defaultdict(int)
        rain_copies = defaultdict(list)

        for key, df in zip(keys, dfs):
            df_rain_copy = df['RAIN'].copy()
            df_rain_copy += rain_prev_accum[key]

            rain_copies[key].append(df_rain_copy)
            rain_prev_accum[key] += df.meta['RAIN_prev_day']

        for key, key_rain in rain_copies.items():
            rain_copies[key] = pd.concat(key_rain)

        unique_keys = list(set(keys))

        new_df = pd.concat(dfs, join=join, keys=unique_keys)
        new_df['RAIN'] = pd.concat(rain_copies, keys=unique_keys)

        new_df.index.set_names(['STID', 'TIME'], inplace=True)
        new_df = new_df.swaplevel().sort_index(level=0)

        if len(unique_keys) == 1:
            new_df.set_index(new_df.index.droplevel(level=1), inplace=True)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UserWarning)
            new_df.meta = dfs[0].meta

        return new_df


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
            new_df.meta = dfs[0].meta
        new_df.index.set_names(['TIME', 'STID'], inplace=True)

        return new_df


def concat(dfs, join='outer'):
    unique_types = list(set(type(df).__name__ for df in dfs))
    if len(unique_types) > 1:
        raise ValueError("Can't handle mixed MTS and MDF files in concatenation")

    return type(dfs[0])._concat(dfs, join=join)
