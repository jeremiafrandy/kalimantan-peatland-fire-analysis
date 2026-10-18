"""Check numerators, periods, results, and artifact dependencies for this release."""
from pathlib import Path
import argparse, hashlib, json, py_compile
import numpy as np
import pandas as pd
from PIL import Image

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=a.output
    annual=pd.read_csv(out/'tables/Table_1_MODIS_Matched_Annual.csv');assert annual.year.tolist()==list(range(2020,2027));assert (annual.within_ID6+annual.outside_ID6==annual.all_detections).all()
    p=pd.read_csv(out/'data/Panel_MODIS_GSMaP_2020_2025_Full_Year.csv.xz',parse_dates=['date_utc']);assert not p.duplicated(['grid_id','date_utc']).any()
    assert len(p)==1694416 and p.any_type0.sum()==3059 and p.grid_id.nunique()==773
    assert p.date_utc.min()==pd.Timestamp('2020-01-01') and p.date_utc.max()==pd.Timestamp('2025-12-31')
    assert p.rain_windows_complete.all()
    assert len(p.loc[p.date_utc.dt.strftime('%m-%d').le('09-26')])==1249168
    primary=pd.read_csv(out/'tables/Table_2_Rainfall_Primary.csv');assert np.isclose(primary.iloc[0].odds_ratio,10.499830844,rtol=1e-6)
    assert int(primary.informative_strata.iloc[0])==1420 and int(primary.informative_grid_days.iloc[0])==43283
    assert np.allclose(primary.odds_ratio,np.exp(primary.beta),rtol=1e-10)
    allmodels=pd.read_csv(out/'tables/Table_S3_Rainfall_All_Sensitivity_Models.csv');assert allmodels.model.nunique()==14
    subset=pd.read_csv(out/'tables/Table_S4_MODIS_Observation_Sensitivity.csv');assert subset.loc[subset.term.eq('0–10'),'ci95_low'].gt(1).all()
    burn=pd.read_csv(out/'tables/Table_3_Burned_Area_2023.csv');ratio=burn.burned_fraction_percent.iloc[0]/burn.burned_fraction_percent.iloc[1]
    assert np.isclose(ratio,3.41123241715,rtol=1e-8)
    assert np.allclose(burn.burned_fraction_percent,100*burn.unique_burned_pixels/burn.valid_pixels)
    sensor=pd.read_csv(out/'tables/Table_S7_Sensor_CAMS_Monthly.csv');assert np.isclose(sensor.loc[sensor.month.eq(10),'sensor_mean'].iloc[0],171.159408888,rtol=1e-8)
    comparison=pd.read_csv(out/'tables/Table_S8_Sensor_CAMS_Burn_Comparisons.csv');assert comparison.paired_days.eq(107).all()
    monthly=pd.read_csv(out/'tables/Table_S5_Burned_Area_Monthly.csv');assert monthly.groupby('class').apply(lambda g:int(g.loc[g.burned_fraction_percent.idxmax(),'month']),include_groups=False).eq(10).all()
    for file in (out/'code').glob('*.py'):py_compile.compile(str(file),doraise=True)
    images=[]
    for file in sorted((out/'figures').glob('*.png')):
        with Image.open(file) as im:im.verify()
        images.append(file.name)
    manuscript=out/'manuscript/Manuscript_Consistency_Checked.txt'
    if manuscript.exists():
        text=manuscript.read_text();assert '10.50' in text and '1,694,416' in text and '0.316' not in text
        assert 'Panel A pools' not in text and 'monthly rainfall and MODIS' not in text.lower()
    s10=pd.read_csv(out/'tables/Table_S10_Rainfall_Category_Counts.csv')
    assert s10.iloc[-1,1:].astype(int).tolist()==[1694416,43283,3059]
    assert s10.iloc[:5,1:].sum().astype(int).tolist()==[1694416,43283,3059]
    index=pd.read_csv(out/'Artifact_Index.csv')
    assert index.path.map(lambda path:(out/path).is_file()).all()
    check={'full_year_panel_unique_keys':True,'matched_descriptive_window_separate':True,'primary_logistic_table_verified':True,
        'observation_sensitivity_contrasts_above_one':True,'burned_fraction_table_verified':True,'October_sensor_table_verified':True,
        'code_compilation':True,'image_files_readable':images,'cloud_mask_based_correction_performed':False,
        'smoke_source_attribution_performed':False,'forecast_validation_performed':False,'statistical_models_refitted_in_this_check':False,
        'Table_S10_totals_verified':True,'artifact_index_paths_exist':True,
        'manuscript_text_checked':manuscript.exists()}
    (out/'evidence/Release_Consistency_Check.json').write_text(json.dumps(check,indent=2))
    manifest=[]
    for file in sorted(out.rglob('*')):
        if file.is_file() and '__pycache__' not in str(file) and 'render' not in file.relative_to(out).parts and file.name not in ['Release_SHA256.csv','Figure_Contact_Sheet.png','Manuscript_Contact_Sheet.png']:
            manifest.append({'file':str(file.relative_to(out)),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    pd.DataFrame(manifest).to_csv(out/'evidence/Release_SHA256.csv',index=False)
    print(json.dumps(check,indent=2))

if __name__=='__main__':main()
