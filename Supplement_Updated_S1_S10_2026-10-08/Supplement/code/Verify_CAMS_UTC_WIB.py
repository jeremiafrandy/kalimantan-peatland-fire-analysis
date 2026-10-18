"""Rebuild CAMS daily PM2.5 at the sensor cell in UTC and local WIB.

WIB grouping is a sensitivity analysis: it does not establish the averaging
timezone of the already-aggregated published sensor data.
"""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from importlib.metadata import version
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import spearmanr

START,END='2023-08-16','2023-11-30'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--grib',type=Path,required=True)
    p.add_argument('--sensor',type=Path,required=True)
    p.add_argument('--daily-comparison',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    with xr.open_dataset(a.sensor,engine='h5netcdf') as ds:
        ds=ds.load()
    sensors=ds.daily_mean_pm25.sel(sensor_type='outdoor',channel='A',time=slice(START,END)).transpose('time','site')
    series=pd.DataFrame(sensors.values,index=pd.DatetimeIndex(sensors.time.values)).mean(axis=1)
    with xr.open_dataset(a.grib,engine='cfgrib',backend_kwargs={'indexpath':''}) as raw:
        assert raw.pm2p5.attrs['units']=='kg m**-3'
        assert raw.pm2p5.attrs['GRIB_stepType']=='instant'
        assert np.array_equal(raw.valid_time.values,raw.time.values)
        assignments=[]
        for name,lat,lon in zip(ds.site.values,ds.lat.values,ds.lon.values):
            i=int(abs(raw.latitude.values-lat).argmin());j=int(abs(raw.longitude.values-lon).argmin())
            assignments.append({'site':str(name),'cell_latitude':float(raw.latitude.values[i]),'cell_longitude':float(raw.longitude.values[j]),'latitude_index':i,'longitude_index':j})
        cells={(x['latitude_index'],x['longitude_index']) for x in assignments}
        assert len(cells)==1
        i,j=next(iter(cells))
        field=raw.pm2p5.isel(latitude=i,longitude=j).load()
        # Preserve the original float32 daily-mean calculation for the UTC check.
        daily_original=field.resample(time='1D').mean()*1e9
        utc_original=daily_original.sel(time=slice(START,END)).to_pandas()
        utc_index=pd.DatetimeIndex(field.time.values).tz_localize('UTC')
        assert not utc_index.has_duplicates
        hourly=pd.Series(field.values.astype(np.float64)*1e9,index=utc_index)
        attrs=dict(raw.pm2p5.attrs); global_attrs=dict(raw.attrs)
    output=pd.DataFrame(index=series.index)
    summaries=[]
    for zone,label in [('UTC','UTC'),('Asia/Jakarta','WIB')]:
        labels=hourly.index.tz_convert(zone).normalize().tz_localize(None)
        grouped=hourly.groupby(labels).agg(['mean','count'])
        grouped.loc[grouped['count']!=8,'mean']=np.nan
        values=grouped['mean'].reindex(series.index)
        if label=='UTC': values=utc_original.where(grouped['count'].reindex(series.index)==8)
        output['cams_'+label.lower()+'_ug_m3']=values
        output['n_observations_'+label.lower()]=grouped['count'].reindex(series.index)
        pair=pd.concat([values.rename('cams'),series.rename('sensor')],axis=1).dropna()
        difference=pair.diff().dropna()
        summaries.append({'daily_convention':label,'paired_days':len(pair),
            'cams_mean_ug_m3':float(pair.cams.mean()),'sensor_mean_ug_m3':float(pair.sensor.mean()),
            'rho_daily_levels':float(spearmanr(pair.cams,pair.sensor).statistic),
            'rho_first_differences':float(spearmanr(difference.cams,difference.sensor).statistic)})
    old=pd.read_csv(a.daily_comparison,parse_dates=['date']).set_index('date')
    model_col='pm25_cams_site_mean_ug_m3' if 'pm25_cams_site_mean_ug_m3' in old else 'pm25_cams_cell_ug_m3'
    check=pd.concat([output.cams_utc_ug_m3.rename('new'),old[model_col].rename('old')],axis=1).dropna()
    maximum=float((check.new-check.old).abs().max())
    assert maximum < 1e-3, 'Raw CAMS rerun does not match archived daily values.'
    output['sensor_reporting_mean_ug_m3']=series
    output.index.name='date';output.to_csv(a.output/'CAMS_Cell_Daily_UTC_WIB.csv')
    pd.DataFrame(summaries).to_csv(a.output/'CAMS_UTC_WIB_Comparison.csv',index=False)
    pd.DataFrame(assignments).to_csv(a.output/'Sensor_CAMS_Cell_Assignments.csv',index=False)
    result={'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'grib_sha256':hashlib.sha256(a.grib.read_bytes()).hexdigest(),
        'grib_bytes':a.grib.stat().st_size,'grib_variable_attributes':attrs,
        'grib_global_attributes':global_attrs,'raw_time_count':len(hourly),
        'raw_time_first_utc':str(hourly.index.min()),'raw_time_last_utc':str(hourly.index.max()),
        'utc_hours_available':sorted(set(map(int,hourly.index.hour))),
        'unique_sensor_model_cells':len(cells),'paired_days':len(series),
        'maximum_difference_from_archived_CAMS_daily_mean':maximum,
        'daily_observations_complete_utc':bool((output.n_observations_utc==8).all()),
        'daily_observations_complete_wib':bool((output.n_observations_wib==8).all()),
        'summaries':summaries,
        'packages':{k:version(k) for k in ['numpy','pandas','scipy','xarray','cfgrib','eccodes']},
        'interpretation':'UTC and WIB daily conventions were evaluated against unchanged released sensor date labels. A higher correlation cannot establish the true sensor averaging window. This check does not validate smoke-source attribution or exposure estimates.'}
    (a.output/'CAMS_Time_Convention_Verification.json').write_text(json.dumps(result,indent=2,default=str))
    print(json.dumps({'maximum_difference_from_archived_CAMS_daily_mean':maximum,'summaries':summaries,
        'complete_utc':result['daily_observations_complete_utc'],'complete_wib':result['daily_observations_complete_wib']},indent=2))

if __name__=='__main__':main()
