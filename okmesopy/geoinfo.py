
import pandas as pd

from io import StringIO
from urllib.request import urlopen

class OKMesoGeoInfo(pd.DataFrame):
    
    @classmethod
    def from_file_obj(cls, fobj):
        txt = fobj.read().decode('utf-8')
        return pd.read_csv(StringIO(txt))

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