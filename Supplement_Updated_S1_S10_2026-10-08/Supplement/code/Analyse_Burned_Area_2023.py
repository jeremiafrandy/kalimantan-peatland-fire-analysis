"""Reproduce centre-classified MCD64A1 burned fractions on its native grid.

Reads provided single-band GeoTIFFs using Pillow. Native spherical sinusoidal
pixel centres are transformed analytically to longitude/latitude (R=6371007.181).
No reprojection/resampling of burned-area values is performed.
"""
from pathlib import Path
import argparse, calendar, hashlib, json
import numpy as np
import pandas as pd
from PIL import Image
from Data_IO import province_and_peat

def read(path):
    with Image.open(path) as im:
        tags={k:im.tag_v2[k] for k in [33550,33922,34735,34736]}
        return np.array(im),tags

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); out=a.output
    provinces=json.loads((a.raw/'batas_5_provinsi_kalimantan.geojson').read_text())['features']; peat=json.loads((a.raw/'BIGID6 200').read_text())['features']
    files={}; cubes=[]; masks=[]; burned=[]; monthly=[]; audit=[]; valid_no_short=[]; valid_no_special=[]; manifest=[]
    for month,doy in [(8,213),(9,244),(10,274),(11,305)]:
        da=next(a.raw.glob(f'MCD64A1.061_Burn_Date_doy2023{doy}*_aid0001.tif')); qa=next(a.raw.glob(f'MCD64A1.061_QA_doy2023{doy}*_aid0001.tif'))
        bd,tags=read(da); q,tq=read(qa); assert tags==tq
        if not cubes:
            meta=tags; shape=bd.shape; sx,sy,_=tags[33550]; tx,ty=tags[33922][3:5]
            assert tags[34736][3:5]==(6371007.181,6371007.181)
            keys=np.array(tags[34735][4:]).reshape(-1,4); assert int(keys[keys[:,0]==3075][0,3])==24
            row,col=np.indices(shape); xm=tx+(col.ravel()+.5)*sx; ym=ty-(row.ravel()+.5)*sy
            lat=ym/6371007.181; lon=xm/(6371007.181*np.cos(lat)); xy=np.c_[np.degrees(lon),np.degrees(lat)]
            prov,onpeat=province_and_peat(xy,provinces,peat); province=prov.reshape(shape)=='Kalimantan Tengah'; pe=onpeat.reshape(shape)&province
            zones={'Within BIG ID 6':pe,'Outside BIG ID 6':province&~pe}; area=sx*sy/1e6
        assert tags==meta and bd.shape==shape
        v=province&(bd>=0)&(q>=0)&((q&1)>0)&((q&2)>0); b=v&(bd>=doy)&(bd<=doy+calendar.monthrange(2023,month)[1]-1)
        cubes.append(bd); masks.append(v); burned.append(b); valid_no_short.append(v&((q&4)==0)); valid_no_special.append(v&((q>>5)==0))
        for name,z in zones.items():
            nv=int((v&z).sum()); nb=int((b&z).sum())
            monthly.append({'month':month,'class':name,'valid_pixels':nv,'burned_pixels':nb,'valid_area_km2':nv*area,'burned_area_km2':nb*area,'burned_fraction_percent':100*nb/nv})
        audit.append({'month':month,'invalid_QA_positive_burns':int((province&(bd>0)&~v).sum()),'positive_burn_dates_outside_month':int((province&(bd>0)&~((bd>=doy)&(bd<=doy+calendar.monthrange(2023,month)[1]-1))).sum())})
        for file in [da,qa]:manifest.append({'file':file.name,'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    any_burn=np.logical_or.reduce(burned); rows=[]; sensitivity=[]
    for scenario,vm in [('Primary centre and QA',masks),('Exclude shortened mapping',valid_no_short),('Exclude special unburned flags',valid_no_special)]:
        all_valid=np.logical_and.reduce(vm)
        for name,z in zones.items():
            nv=int((all_valid&z).sum()); nb=int((all_valid&z&any_burn).sum())
            r={'scenario':scenario,'class':name,'valid_pixels':nv,'unique_burned_pixels':nb,'valid_area_km2':nv*area,'unique_burned_area_km2':nb*area,'burned_fraction_percent':100*nb/nv,'valid_coverage_percent':100*nv/z.sum()}
            sensitivity.append(r)
            if scenario.startswith('Primary'):rows.append(r)
    table=pd.DataFrame(rows); assert table.unique_burned_pixels.tolist()==[4864,7703] and table.valid_pixels.tolist()==[110282,595775]
    table.to_csv(out/'tables/Table_3_Burned_Area_2023.csv',index=False); pd.DataFrame(monthly).to_csv(out/'tables/Table_S5_Burned_Area_Monthly.csv',index=False)
    sens=pd.DataFrame(sensitivity); sens.to_csv(out/'tables/Table_S6_Burned_Area_QA_Sensitivity.csv',index=False)
    daily=[]
    for doy in range(213,335):
        mi=np.searchsorted([213,244,274,305],doy,side='right')-1; r={'date':str((pd.Timestamp('2023-01-01')+pd.Timedelta(days=doy-1)).date())}
        for name,z in zones.items():r['burned_within_ID6_km2' if name.startswith('Within') else 'burned_outside_ID6_km2']=int((masks[mi]&z&(cubes[mi]==doy)).sum())*area
        daily.append(r)
    pd.DataFrame(daily).to_csv(out/'data/Burned_Area_Daily_2023.csv',index=False)
    pd.DataFrame(audit).to_csv(out/'evidence/Burned_Area_QA_Audit.csv',index=False)
    pd.DataFrame(manifest).to_csv(out/'evidence/Burned_Area_Input_SHA256.csv',index=False)
    result={'pixel_area_km2':area,'seasonal_fraction_ratio':float(table.burned_fraction_percent.iloc[0]/table.burned_fraction_percent.iloc[1]),'raster_shape':shape,'QA_sensitivity_ratios':{n:float(g.burned_fraction_percent.iloc[0]/g.burned_fraction_percent.iloc[1]) for n,g in sens.groupby('scenario',sort=False)}}
    (out/'evidence/Burned_Area_Verification.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result))

if __name__=='__main__':main()
