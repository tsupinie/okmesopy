# okmesopy
Readers for Oklahoma Mesonet data and time series files

okmesopy provides a thin-ish wrapper around a Pandas data frame. There is an included `concat()` function that is also a thin-ish wrapper around the pandas `concat()` function. The okmesopy `concat()` handles properly pasting data files together, including accumulating rainfall for MTS files. okmesopy also provides a way to read the latest meta data from the web.

Additionally, okmesopy uses pint-pandas to provide a units-aware data frame, and the correct units for each variable are included by default. See the pint-pandas documentation for more info. The units registry is the one used in MetPy, so you can pass quantities directly to MetPy.

There is no paywall for downloading the data. However, if you're going to use it, and you live outside the US state of Oklahoma, or if you're part of a television media or other commercial entity (even within the state of Oklahoma), the Oklahoma Mesonet does charge a fee to help cover their operating costs. See [here](https://mesonet.org/about/data-access-and-pricing) for more details.

## Installation
```
$ python setup.py install
```

## Dependencies
* Pandas
* pint-pandas
* MetPy

## Usage
```python
>>> from okmesopy import MDF, MTS, concat, OKMesoGeoInfo
>>> from datetime import datetime, timedelta
>>> from metpy import dewpoint_from_relative_humidity
>>>
>>> meta = OKMesoGeoInfo.from_web() # Read the latest metadata from the web
>>> mdf1 = MDF.from_file("/path/to/data/202007120200.mdf") # Load an MDF from a local file
>>> mdf2 = MDF.from_web(datetime(2020, 7, 12, 2, 5)) # Load an MDF file from the web
>>> mdf1['TAIR'].loc['NRMN'].to('degF') # Convert units in the file
<Quantity(91.94, 'degree_Fahrenheit')>
>>> dewpoint_from_relative_humidity(mdf['TAIR'].loc['NRMN'], mdf['RELH'].loc['NRMN']) # Pass quantities directly to MetPy calculation functions
<Quantity(23.6395585, 'degree_Celsius')>
>>> soil_vwc = mdf1.compute_soil_vwc(meta) # Compute soil volumetric water content
>>> concat([mdf1, mdf2]) # Concatenate the two data files
                          STNM  RELH  TAIR  WSPD  WVEC   WDIR  WDSD  WSSD  WMAX   RAIN    PRES  SRAD  TA9M  WS2M  TS10  TB10  TS05  TS25  TS60  TR05  TR25  TR60
                    STID                                                                                                                                        
2020-07-12 02:00:00 ACME   110  65.0  30.6   3.4   3.4  146.0   5.7   0.4   4.1   0.00  965.22   0.0  31.4   2.3  31.8  35.9  32.7  29.0  25.5  3.09  3.13  2.11
                    ADAX     1  69.0  31.0   1.3   1.3  160.0  14.7   0.3   2.1   0.00  977.41   0.0  31.6   0.1  31.5  35.5  32.8  30.2   NaN  1.44  1.73   NaN
                    ALTU     2  42.0  34.8   5.4   5.3  153.0   7.3   0.6   6.5   0.00  961.22   1.0  35.1   3.5  32.5  35.1  32.4  29.3   NaN  2.48  3.48   NaN
                    ALV2   116  92.0  22.5   3.4   3.3  109.0  14.7   0.8   4.9  11.68  960.79   1.0  22.4   2.7  27.6  36.0  28.5  26.9   NaN  3.63  3.68   NaN
                    ANT2   135  67.0  31.2   1.3   1.3  166.0  19.5   0.6   3.6   0.00  991.23   0.0  31.7   0.2  30.9  37.2  31.6  28.3  25.9  3.63  2.50  1.96
...                        ...   ...   ...   ...   ...    ...   ...   ...   ...    ...     ...   ...   ...   ...   ...   ...   ...   ...   ...   ...   ...   ...
2020-07-12 02:05:00 WILB   105  62.0  32.0   2.8   2.8  173.0   5.6   0.3   3.6   0.00  988.31   0.0  32.9   1.8   NaN   NaN   NaN   NaN   NaN   NaN   NaN   NaN
                    WIST   106  84.0  29.2   0.1   0.1  356.0   3.4   0.1   0.4   0.00  994.98   0.0  31.1   0.0   NaN   NaN   NaN   NaN   NaN   NaN   NaN   NaN
                    WOOD   107  83.0  25.7   4.5   4.4   56.0   8.5   0.5   6.2   0.76  940.47   0.0  26.1   3.1   NaN   NaN   NaN   NaN   NaN   NaN   NaN   NaN
                    WYNO   108  73.0  26.7  13.1  12.9   69.0   7.8   3.2  19.1   0.00  978.53   0.0  26.4   9.7   NaN   NaN   NaN   NaN   NaN   NaN   NaN   NaN
                    YUKO   142  62.0  32.1   6.5   6.5  190.0   7.0   0.8   8.2   0.00  963.14   0.0  32.8   4.4   NaN   NaN   NaN   NaN   NaN   NaN   NaN   NaN

[240 rows x 22 columns]
```
