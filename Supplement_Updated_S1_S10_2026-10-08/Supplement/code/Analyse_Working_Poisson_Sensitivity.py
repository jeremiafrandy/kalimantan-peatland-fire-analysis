"""Working Poisson mean sensitivity only; binary primary model is logistic."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm,t
def conditional_poisson(data, outcome, predictors=('rain_1_7_mm', 'rain_8_30_mm')):
    """Exact stratum conditional likelihood for a Poisson mean, robust SE.

    The daily binary outcome is modelled as a conditional incidence ratio.
    Score covariance uses two-way grid-cell and calendar month-year clusters,
    subtracting their cell x month-year intersections. Year-month blocks are
    shared across grids. No inference is drawn about undetected fires.
    """
    d = data[['grid_id', 'year', 'month', outcome, *predictors]].copy()
    d['yearmonth'] = d['year'] * 100 + d['month']
    d.sort_values(['grid_id', 'yearmonth'], inplace=True, kind='stable')
    # Month-year nests inside grid-cell and has 26–31 days per stratum.
    idx = pd.MultiIndex.from_frame(d[['grid_id', 'yearmonth']])
    _, groups = np.unique(idx, return_inverse=True)
    first = np.r_[0, np.flatnonzero(np.diff(groups)) + 1]
    y = d[outcome].to_numpy(dtype=np.float64)
    X = d[list(predictors)].to_numpy(dtype=np.float64) / 50.
    events = np.add.reduceat(y, first)
    use_group = events > 0
    informative_rows = np.repeat(use_group, np.diff(np.r_[first, len(d)]))
    d = d.loc[informative_rows].copy()
    X, y = X[informative_rows], y[informative_rows]
    _, groups = np.unique(pd.MultiIndex.from_frame(d[['grid_id', 'yearmonth']]),
                          return_inverse=True)
    first = np.r_[0, np.flatnonzero(np.diff(groups)) + 1]
    events = np.add.reduceat(y, first)
    n_groups = len(first)
    ncols = X.shape[1]
    sum_y_x = X.T @ y

    def calc(beta, extra=False):
        v = X @ beta
        high = np.maximum.reduceat(v, first)
        ev = np.exp(v - high[groups])
        sums = np.add.reduceat(ev, first)
        weights = ev / sums[groups]
        expected = np.column_stack([
            np.add.reduceat(weights * X[:, j], first) for j in range(ncols)])
        loglike = sum_y_x @ beta - np.sum(events * (high + np.log(sums)))
        grad = sum_y_x - (events[:, None] * expected).sum(axis=0)
        if not extra:
            return -loglike, -grad
        centred = X - expected[groups]
        H = centred.T @ (centred * (events[groups] * weights)[:, None])
        observed = np.column_stack([
            np.add.reduceat(y * X[:, j], first) for j in range(ncols)])
        scores = observed - events[:, None] * expected
        return H, scores, expected

    fit = minimize(calc, np.zeros(ncols), method='BFGS', jac=True,
                   options={'gtol': 1e-4, 'maxiter': 200})
    if not fit.success and np.linalg.norm(fit.jac) > 1e-3:
        raise RuntimeError(f'Model did not converge: {fit.message}; {fit.jac}')
    H, scores, expected = calc(fit.x, extra=True)
    ggrid = d.grid_id.to_numpy()[first]
    gmonth = d.yearmonth.to_numpy()[first]

    def meat_by(labels):
        _, indices = np.unique(labels, return_inverse=True)
        aggregated = np.zeros((indices.max() + 1, ncols))
        np.add.at(aggregated, indices, scores)
        return aggregated.T @ aggregated

    # Cameron–Gelbach–Miller two-way covariance for crossed clusters.
    meat = meat_by(ggrid) + meat_by(gmonth) - scores.T @ scores
    invH = np.linalg.inv(H)
    g_min = min(len(np.unique(ggrid)), len(np.unique(gmonth)))
    cov = invH @ (meat * g_min / (g_min - 1)) @ invH
    critical = t.ppf(.975, g_min - 1)
    if np.any(np.diag(cov) <= 0):
        raise RuntimeError('Nonpositive two-way cluster variance; inspect clusters.')
    se = np.sqrt(np.diag(cov))
    z = fit.x / se
    table = pd.DataFrame({
        'predictor': list(predictors), 'difference_mm': 50,
        'beta': fit.x, 'two_way_cluster_se': se,
        'incidence_ratio_per_50mm': np.exp(fit.x),
        'ci_95_low': np.exp(fit.x - critical * se),
        'ci_95_high': np.exp(fit.x + critical * se),
        'p_two_sided_approx': 2 * norm.sf(np.abs(z)),
        'outcome': outcome, 'grid_months_total': len(use_group),
        'grid_months_informative': n_groups,
        'observations_total': len(data),
        'observations_informative': len(d),
        'detected_grid_days_total': int(data[outcome].sum()),
        'spatial_clusters': len(np.unique(ggrid)),
        'temporal_clusters': len(np.unique(gmonth)),
    })
    return table


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    p=pd.read_csv(a.output/'data/Panel_MODIS_GSMaP_2020_2025_Full_Year.csv.xz',parse_dates=['date_utc'])
    tables=[]
    for label, d in [('Full year working Poisson',p),('Matched-window working Poisson',p.loc[p.date_utc.dt.strftime('%m-%d').le('09-26')])]:
        r=conditional_poisson(d,'any_type0');r['model']=label;tables.append(r)
    pd.concat(tables,ignore_index=True).to_csv(a.output/'tables/Table_S9_Working_Poisson_Sensitivity.csv',index=False)
    print(pd.concat(tables)[['model','predictor','incidence_ratio_per_50mm','ci_95_low','ci_95_high']].to_string(index=False))
if __name__=='__main__':main()
