"""Audit the released daily sensor file and reproduce its summary statistics.

No physical channel substitution, humidity correction, or time-zone conversion
is inferred from a field label. Date-offset checks are sensitivity analyses only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import spearmanr

START, END = '2023-08-16', '2023-11-30'
EXPECTED_MD5 = 'e811953a84db4fd14a33f67dd8f483dd'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sensor',type=Path,required=True)
    p.add_argument('--daily-comparison',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    with xr.open_dataset(a.sensor,engine='h5netcdf') as opened:
        ds=opened.load()
    pm=ds.daily_mean_pm25
    assert pm.attrs['units'] == 'ug m-3'
    assert set(map(str,ds.channel.values)) == {'A','B'}
    b_count=int(pm.sel(channel='B').count())
    assert b_count==0
    outdoor=pm.sel(sensor_type='outdoor',channel='A',time=slice(START,END)).transpose('time','site')
    values=pd.DataFrame(outdoor.values,index=pd.DatetimeIndex(outdoor.time.values),columns=list(map(str,outdoor.site.values)))
    reporting=values.mean(axis=1); fixed=values[['PLK_01','SBG_01']].mean(axis=1)
    without=values.drop(columns='KR_06').mean(axis=1)
    daily=pd.DataFrame({'date':values.index,'pm25_reporting_sites':reporting.values,
        'pm25_fixed_two_sites':fixed.values,'pm25_without_KR06':without.values,
        'n_reporting_sites':values.notna().sum(axis=1).values})
    daily.to_csv(a.output/'Sensor_Daily_Reproduced.csv',index=False)
    monthly=[]
    for m in [8,9,10,11]:
        select=values.index.month==m
        monthly.append({'month':m,'days':int(select.sum()),'mean_reporting_sites':float(reporting[select].mean()),
            'mean_fixed_two_sites':float(fixed[select].mean()),'mean_without_KR06':float(without[select].mean()),
            'site_days':int(values.loc[select].notna().sum().sum())})
    pd.DataFrame(monthly).to_csv(a.output/'Sensor_Monthly_Reproduced.csv',index=False)
    comparison=pd.read_csv(a.daily_comparison,parse_dates=['date']).set_index('date')
    if 'pm25_cams_cell_ug_m3' not in comparison and 'pm25_cams_site_mean_ug_m3' in comparison:
        comparison=comparison.rename(columns={'pm25_cams_site_mean_ug_m3':'pm25_cams_cell_ug_m3'})
    columns=['pm25_sensor_mean_ug_m3','pm25_cams_cell_ug_m3','burned_peat_km2','burned_outside_id6_km2']
    missing=set(columns)-set(comparison.columns)
    if missing: raise ValueError('Missing comparison fields: '+str(missing))
    same=comparison.join(reporting.rename('raw_sensor_mean'))
    overlap=same[['pm25_sensor_mean_ug_m3','raw_sensor_mean']].dropna()
    maximum_difference=float((overlap.iloc[:,0]-overlap.iloc[:,1]).abs().max())
    assert maximum_difference < 1e-4
    alignment=[]
    for offset in [-1,0,1]:
        shifted=reporting.copy(); shifted.index=shifted.index+pd.Timedelta(days=offset)
        pair=comparison[columns[1:]].join(shifted.rename('sensor')).dropna()
        for name in columns[1:]:
            diff=pair[[name,'sensor']].diff().dropna()
            alignment.append({'sensor_date_offset_days':offset,'comparison':name,'paired_days':len(pair),
                'rho_daily_levels':float(spearmanr(pair[name],pair.sensor).statistic),
                'rho_first_differences':float(spearmanr(diff[name],diff.sensor).statistic)})
    pd.DataFrame(alignment).to_csv(a.output/'Date_Label_Offset_Sensitivity.csv',index=False)
    md5=hashlib.md5(a.sensor.read_bytes()).hexdigest()
    note={'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_doi':'10.5281/zenodo.13767528','paper_doi':'10.1029/2024GH001125',
        'source_md5':md5,'expected_repository_md5':EXPECTED_MD5,'source_md5_matches_repository':md5==EXPECTED_MD5,
        'source_sha256':hashlib.sha256(a.sensor.read_bytes()).hexdigest(),
        'dimensions':dict(ds.sizes),'global_attributes':ds.attrs,
        'variable_attributes':{k:dict(v.attrs) for k,v in ds.variables.items()},
        'time_encoding':{k:str(v) for k,v in ds.time.encoding.items() if k in ['units','calendar','dtype']},
        'time_zone_explicit_in_metadata':False,'physical_channel_mapping_explicit_in_metadata':False,
        'nonmissing_channel_B':b_count,'study_site_days':int(values.notna().sum().sum()),
        'study_days':len(values),'reporting_sites_min':int(values.notna().sum(axis=1).min()),
        'reporting_sites_max':int(values.notna().sum(axis=1).max()),
        'maximum_difference_from_archived_daily_summary':maximum_difference,
        'KR06_max_after_failure':float(values.loc['2023-09-27':,'KR_06'].max()),
        'complete_sites':list(values.columns[values.notna().all(axis=0)]),
        'packages':{k:version(k) for k in ['numpy','pandas','scipy','xarray','h5netcdf','h5py']},
        'interpretation':['Published methods specify a mean of both physical channels except PA03/KR06, for which Channel B was used.',
            'The released file has nonmissing values under field A only. Its field labels do not explicitly describe the composite-to-physical-channel mapping.',
            'Midnight daily date labels and CF-style reference units do not independently establish the averaging window.',
            'A date-offset sensitivity check does not reconstruct hourly observations or validate a timezone conversion.']}
    (a.output/'Sensor_Verification.json').write_text(json.dumps(note,indent=2,default=str))
    print(json.dumps({'source_md5_matches_repository':md5==EXPECTED_MD5,
        'maximum_difference_from_archived_daily_summary':maximum_difference,
        'study_site_days':note['study_site_days'],'monthly':monthly,'alignment':alignment},indent=2))

if __name__=='__main__': main()
