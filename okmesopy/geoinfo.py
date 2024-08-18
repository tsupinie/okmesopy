
import numpy as np

import pandas as pd

import pint_pandas
from metpy.units import units

from io import StringIO
from urllib.request import urlopen
from datetime import datetime
from zoneinfo import ZoneInfo

pint_pandas.PintType.ureg = units

tz_utc = ZoneInfo('utc')

class OKMesoGeoInfo(pd.DataFrame):
    _units = {
        'rang': 'miles',
        'nlat': 'deg',
        'elon': 'deg',
        'elev': 'm',
        'WCR05': 'cm^3/cm^3',
        'WCS05': 'cm^3/cm^3',
        'A05': '1/kPa',
        'N05': 'dimensionless',
        'BULK5': 'g/cm^3',
        'GRAV5': 'percent',
        'SAND5': 'percent',
        'SILT5': 'percent',
        'CLAY5': 'percent',
        'WCR10': 'cm^3/cm^3',
        'WCS10': 'cm^3/cm^3',
        'A10': '1/kPa',
        'N10': 'dimensionless',
        'WCR25': 'cm^3/cm^3',
        'WCS25': 'cm^3/cm^3',
        'A25': '1/kPa',
        'N25': 'dimensionless',
        'BULK25': 'g/cm^3',
        'GRAV25': 'percent',
        'SAND25': 'percent',
        'SILT25': 'percent',
        'CLAY25': 'percent',
        'WCR60': 'cm^3/cm^3',
        'WCS60': 'cm^3/cm^3',
        'A60': '1/kPa',
        'N60': 'dimensionless',
        'BULK60': 'g/cm^3',
        'GRAV60': 'percent',
        'SAND60': 'percent',
        'SILT60': 'percent',
        'CLAY60': 'percent',
        'WCR75': 'cm^3/cm^3',
        'WCS75': 'cm^3/cm^3',
        'A75': '1/kPa',
        'N75': 'dimensionless',
        'BULK75': 'g/cm^3',
        'GRAV75': 'percent',
        'SAND75': 'percent',
        'SILT75': 'percent',
        'CLAY75': 'percent',
    }
    
    @classmethod
    def from_file_obj(cls, fobj):
        txt = fobj.read().decode('utf-8')
        df = pd.read_csv(StringIO(txt), dtype={'elev': np.float64})
        df.set_index('stid', inplace=True)

        soil_params = ['WCR%02d', 'WCS%02d', 'A%02d', 'N%02d', 'BULK%d', 'GRAV%d', 'SAND%d', 'SILT%d', 'CLAY%d']
        depths = [5, 10, 25, 60, 75]

        for depth in depths:
            for param in soil_params:
                col = param % depth
                if col in df.columns:
                    df.loc[df[col] < -900, col] = float('nan')

        for depth in depths:
            col = 'TEXT%d' % depth
            if col in df.columns:
                df.loc[df[col] == '-999', col] = ''
        
        df['datc'] = pd.to_datetime(df['datc'], format='%Y%m%d', utc=True)
        df['datd'] = pd.to_datetime(df['datd'], format='%Y%m%d', utc=True)
        df.loc[df['datd'] > datetime.now(tz=tz_utc), 'datd'] = float('nan')

        _units = OKMesoGeoInfo._units
        unit_cols = list(set(list(df)) & set(list(_units.keys())))
        df = df.astype({var: f'pint[{_units[var]}]' for var in unit_cols})

        return df

    @classmethod
    def from_file(cls, fname):
        with open(fname) as fobj:
            geo = cls.from_file_obj(fobj)
        return geo

    @classmethod
    def from_web(cls):
        url = "https://www.mesonet.org/index.php/api/siteinfo/from_all_active_with_geo_fields/format/csv/geoinfo.csv"
        urlobj = urlopen(url)
        return cls.from_file_obj(urlobj)

if __name__ == "__main__":
    omgi = OKMesoGeoInfo.from_web()
    print(omgi)