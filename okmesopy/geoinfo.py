
import pandas as pd

from io import StringIO
from urllib.request import urlopen

class OKMesoGeoInfo(pd.DataFrame):
    
    @classmethod
    def from_file_obj(cls, fobj):
        txt = fobj.read().decode('utf-8')
        df = pd.read_csv(StringIO(txt))
        df.set_index('stid', inplace=True)

        soil_params = ['WCR%02d', 'WCS%02d', 'A%02d', 'N%02d', 'BULK%d', 'GRAV%d', 'SAND%c', 'SILT%d', 'CLAY%d']
        depths = [5, 10, 25, 60, 75]

        for depth in depths:
            for param in soil_params:
                col = param % depth
                if col in df.columns:
                    df.loc[df[col] < -900, col] = float('nan')
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