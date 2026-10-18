"""Build full-year historical rainfall panel and audit FIRMS detection records.

Positive-only FIRMS records cannot measure clear-sky observation availability.
All detection subsets below are sensitivity checks, not cloud corrections.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import pandas as pd
from Data_IO import get_raster, province_and_peat, hits

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw',type=Path,required=True)
    ap.add_argument('--rain',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); out=a.output; (out/'data').mkdir(parents=True,exist_ok=True); (out/'tables').mkdir(exist_ok=True); (out/'evidence').mkdir(exist_ok=True)
    provinces=json.loads((a.raw/'batas_5_provinsi_kalimantan.geojson').read_text())['features']
    peat=json.loads((a.raw/'BIGID6 200').read_text())['features']; assert len(peat)==100
    names=['fire_archive_M-C61_813388.csv','fire_archive_M-C61_813389.csv','fire_nrt_M-C61_813389.csv']
    frames=[]; audits=[]; manifests=[]
    for name in names:
        path=a.raw/name; f=pd.read_csv(path,low_memory=False); f['source_file']=name
        f['source_processing']='NRT' if 'nrt' in name else 'standard'
        audits.append({'file':name,'rows':len(f),'first_date':f.acq_date.min(),'last_date':f.acq_date.max(),
            'exact_duplicate_rows':int(f.drop(columns=['source_file','source_processing']).duplicated().sum()),
            'type_field_present':'type' in f,'clear_sky_or_cloud_mask_present':False})
        manifests.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
        frames.append(f)
    raw=pd.concat(frames,ignore_index=True); raw['date_utc']=pd.to_datetime(raw.acq_date)
    raw['year']=raw.date_utc.dt.year; raw['month']=raw.date_utc.dt.month
    key=['latitude','longitude','acq_date','acq_time','satellite']; assert not raw.duplicated(key).any()
    raw['province'], raw['inside_ID6']=province_and_peat(raw[['longitude','latitude']].to_numpy(),provinces,peat)
    raw=raw.loc[raw.province.ne('') & raw.date_utc.between('2020-01-01','2026-09-26')].copy()
    raw['grid_id']=120*np.floor((5-raw.latitude)/.1).astype(int)+np.floor((raw.longitude-108)/.1).astype(int)
    raw.to_csv(out/'data/MODIS_Classified_2020_2026.csv.xz',index=False,float_format='%.8g')
    matched=raw.loc[raw.date_utc.dt.strftime('%m-%d').le('09-26')]
    annual=matched.groupby('year').inside_ID6.agg(['size','sum']).reset_index().rename(columns={'size':'all_detections','sum':'within_ID6'})
    annual['outside_ID6']=annual.all_detections-annual.within_ID6; annual['within_ID6_percent']=100*annual.within_ID6/annual.all_detections
    assert annual.all_detections.tolist()==[2741,3011,2591,14073,7712,5391,53476]
    assert annual.within_ID6.tolist()==[180,496,255,2242,387,516,17934]
    annual.to_csv(out/'tables/Table_1_MODIS_Matched_Annual.csv',index=False)
    province_index=pd.MultiIndex.from_product([range(2020,2027),[f['properties']['wadmpr'] for f in provinces],[False,True]],names=['year','province','inside_ID6'])
    matched.groupby(['year','province','inside_ID6']).size().reindex(province_index,fill_value=0).rename('detections').reset_index().to_csv(out/'tables/Table_S1_MODIS_Province.csv',index=False)
    # These summaries are CONDITIONAL ON DETECTION. They do not quantify observation opportunities.
    diagnostic=[]
    for y,g in matched.groupby('year'):
        diagnostic.append({'year':y,'detections':len(g),'Terra_percent':100*g.satellite.eq('Terra').mean(),
            'daytime_percent':100*g.daynight.eq('D').mean(),'confidence_ge80_percent':100*g.confidence.ge(80).mean(),
            'scan_le1p5_track_le1p5_percent':100*(g['scan'].le(1.5)&g.track.le(1.5)).mean(),
            'median_scan_km':g['scan'].median(),'median_track_km':g.track.median(),
            'dates_with_any_detection':g.date_utc.nunique(),'NRT_percent':100*g.source_processing.eq('NRT').mean()})
    pd.DataFrame(diagnostic).to_csv(out/'tables/Table_S2_MODIS_Detection_Characteristics.csv',index=False)
    pd.DataFrame(audits).to_csv(out/'evidence/FIRMS_File_Audit.csv',index=False)
    lon=108+.1*(np.arange(120)+.5); lat=5-.1*(np.arange(100)+.5); xx,yy=np.meshgrid(lon,lat); xy=np.c_[xx.ravel(),yy.ravel()]
    prov,centre=province_and_peat(xy,provinces,peat); frac=np.zeros(len(xy))
    for dx in (np.arange(5)+.5)/5-.5:
        for dy in (np.arange(5)+.5)/5-.5:
            inside=np.zeros(len(xy),bool)
            for f in peat: inside |= hits(xy+[dx*.1,dy*.1],f['geometry'])
            frac += inside/25
    ids=np.flatnonzero((prov!='')&(frac>0)); assert len(ids)==773
    pd.DataFrame({'grid_id':ids,'longitude':xy[ids,0],'latitude':xy[ids,1],'province':prov[ids],
        'peat_fraction_25point':frac[ids],'grid_centre_on_peat':centre[ids]}).to_csv(out/'data/Rainfall_Grid_Definition.csv',index=False)
    dates=[]; cubes=[]; rq=[]
    for name in ['GSMaP_v8_GC_2019_Dec.tif']+[f'GSMaP_v8_GC_{y}.tif' for y in range(2020,2026)]:
        path=a.rain/name; d,v=get_raster(path); dates.append(d); cubes.append(v[:,ids//120,ids%120])
        rq.append({'file':name,'days':len(d),'first_date':str(d[0].date()),'last_date':str(d[-1].date()),'missing_selected_cell_days':int(np.isnan(cubes[-1]).sum())})
        manifests.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
    all_dates=pd.DatetimeIndex(np.concatenate(dates)); assert all_dates.equals(pd.date_range('2019-12-02','2025-12-31'))
    rain=np.concatenate(cubes); valid=np.isfinite(rain); c=np.vstack([np.zeros(len(ids)),np.cumsum(np.where(valid,rain,0),axis=0,dtype=float)])
    n=np.vstack([np.zeros(len(ids),dtype=int),np.cumsum(valid,axis=0)])
    d=pd.date_range('2020-01-01','2025-12-31'); k=all_dates.get_indexer(d)
    p=pd.DataFrame({'date_utc':np.repeat(d.values,len(ids)),'grid_id':np.tile(ids,len(d)),
        'year':np.repeat(d.year,len(ids)),'month':np.repeat(d.month,len(ids)),
        'province':np.tile(prov[ids],len(d)),'grid_centre_on_peat':np.tile(centre[ids],len(d)),
        'peat_fraction_25point':np.tile(frac[ids],len(d)),
        'rain_1_7_mm':(c[k]-c[k-7]).ravel(),'rain_8_30_mm':(c[k-7]-c[k-30]).ravel(),
        'rain_windows_complete':((n[k]-n[k-7]==7)&(n[k-7]-n[k-30]==23)).ravel()})
    p.loc[~p.rain_windows_complete,['rain_1_7_mm','rain_8_30_mm']]=np.nan
    f=raw.loc[raw.year.le(2025)&raw.inside_ID6&raw.grid_id.isin(ids)].copy()
    subsets={'type0':f.type.eq(0),'all':np.ones(len(f),bool),'confidence80':f.type.eq(0)&f.confidence.ge(80),
        'terra':f.type.eq(0)&f.satellite.eq('Terra'),'aqua':f.type.eq(0)&f.satellite.eq('Aqua'),
        'day':f.type.eq(0)&f.daynight.eq('D'),'night':f.type.eq(0)&f.daynight.eq('N'),
        'small_footprint':f.type.eq(0)&f['scan'].le(1.5)&f.track.le(1.5),
        'high_conf_all':f.confidence.ge(80)}
    for label,sel in subsets.items():
        counts=f.loc[sel].groupby(['date_utc','grid_id']).size().rename('detections_'+label)
        p=p.join(counts,on=['date_utc','grid_id']); p['detections_'+label]=p['detections_'+label].fillna(0).astype('int32')
        p['any_'+label]=p['detections_'+label].gt(0).astype('int8')
    assert len(p)==1694416 and p.any_type0.sum()==3059
    p.to_csv(out/'data/Panel_MODIS_GSMaP_2020_2025_Full_Year.csv.xz',index=False,float_format='%.8g')
    p.groupby('year').agg(grid_days=('grid_id','size'),detected_grid_days=('any_type0','sum'),type0_detections=('detections_type0','sum'),complete_rain_grid_days=('rain_windows_complete','sum')).reset_index().to_csv(out/'evidence/Rainfall_Panel_Audit.csv',index=False)
    pd.DataFrame(rq).to_csv(out/'evidence/GSMaP_Raster_Audit.csv',index=False)
    for name in ['batas_5_provinsi_kalimantan.geojson','BIGID6 200']:
        path=a.raw/name; manifests.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
    pd.DataFrame(manifests).to_csv(out/'evidence/Input_SHA256.csv',index=False)
    print(json.dumps({'historical_grid_days':len(p),'historical_detected_grid_days':int(p.any_type0.sum()),'cells':len(ids),'FIRMS_rows_in_provinces':len(raw),'cloud_correction_possible_from_FIRMS_CSV':False}))

if __name__=='__main__':main()
