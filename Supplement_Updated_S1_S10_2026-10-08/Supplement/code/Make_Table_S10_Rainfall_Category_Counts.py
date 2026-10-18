"""Reproduce Table S10 from the released analytic panel without refitting a model.

Recent rainfall is D-7 through D-1. Informative strata have both binary
detection outcomes within grid cell x year-month. Count grid-days, not points.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd

CAPTION = ('Table S10. Distribution of analytic grid-days and recorded '
           'vegetation-fire detection grid-days across preceding seven-day '
           'rainfall categories, 2020–2025.')
NOTE = ('Informative strata contained both detection and non-detection grid-days '
        'within the same grid cell and year-month. Counts describe the '
        'observations available to the analysis and should not be interpreted '
        'as population-wide fire probabilities.')
LABELS = ['0–10', '>10–30', '>30–60', '>60–100', '>100']
EXPECTED = np.array([[136716,9974,1498], [272585,9244,758],
                     [500096,11413,499], [460728,8023,214],
                     [324291,4629,90]])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1])
    a = ap.parse_args(); out = a.output
    path = out/'data/Panel_MODIS_GSMaP_2020_2025_Full_Year.csv.xz'
    cols = ['date_utc','grid_id','year','month','rain_windows_complete',
            'rain_1_7_mm','any_type0']
    d = pd.read_csv(path, usecols=cols, parse_dates=['date_utc'])
    assert not d.duplicated(['grid_id','date_utc']).any()
    assert d.any_type0.isin([0,1]).all()
    d = d.loc[d.rain_windows_complete.eq(True)].copy()
    assert np.isfinite(d.rain_1_7_mm).all() and d.rain_1_7_mm.ge(0).all()
    d['ym'] = d.year*100 + d.month
    grouped = d.groupby(['grid_id','ym'])['any_type0']
    sums, sizes = grouped.transform('sum'), grouped.transform('size')
    informative = sums.gt(0) & sums.lt(sizes)
    category = np.digitize(d.rain_1_7_mm.to_numpy(), [10,30,60,100], right=True)
    rows = []
    for i, label in enumerate(LABELS):
        selected = category == i
        rows.append([label, int(selected.sum()), int((selected & informative).sum()),
                     int(d.loc[selected & informative,'any_type0'].sum())])
    headers = ['preceding_seven_day_rainfall_mm','complete_panel_grid_days',
               'informative_strata_grid_days','recorded_detection_grid_days_informative_strata']
    table = pd.DataFrame(rows, columns=headers)
    assert np.array_equal(table.iloc[:,1:].to_numpy(), EXPECTED), 'Released counts differ'
    totals = table.iloc[:,1:].sum().astype(int).tolist()
    assert totals == [1694416,43283,3059]
    table.loc[len(table)] = ['Total', *totals]
    (out/'tables').mkdir(exist_ok=True)
    table.to_csv(out/'tables/Table_S10_Rainfall_Category_Counts.csv', index=False)
    counts = grouped.agg(['sum','size'])
    number = int(((counts['sum']>0) & (counts['sum']<counts['size'])).sum())
    assert number == 1420
    verification = {
        'operation':'Descriptive count verification; no statistical model refit',
        'panel':str(path.relative_to(out)),
        'panel_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'stratum':'grid_id x year-month',
        'outcome':'at least one recorded presumed vegetation-fire detection (type = 0)',
        'rainfall_window':'D-7 through D-1; no rainfall from day D',
        'bins':'[0,10], (10,30], (30,60], (60,100], (100,infinity)',
        'complete_grid_days':totals[0], 'informative_grid_days':totals[1],
        'detection_grid_days_in_informative_strata':totals[2],
        'informative_strata':number, 'counts_match_requested_table':True,
        'caption':CAPTION, 'note':NOTE}
    (out/'evidence').mkdir(exist_ok=True)
    (out/'evidence/Table_S10_Verification.json').write_text(
        json.dumps(verification,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(table.to_string(index=False))

if __name__ == '__main__': main()
