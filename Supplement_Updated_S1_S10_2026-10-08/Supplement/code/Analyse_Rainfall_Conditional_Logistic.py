"""Exact conditional logistic regression for detected grid-days.

Conditions on grid x year-month event totals. Computes the elementary-symmetric
polynomial denominator and its first moments by dynamic programming, without
enumerating combinations. Two-way clustered sandwich intervals are approximate.
Detection-subset checks cannot correct cloud-dependent observation availability.
"""
from pathlib import Path
import argparse, itertools, json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import t

CATEGORIES=['0–10','>10–30','>30–60','>60–100']; TERMS=CATEGORIES+['Earlier rainfall, per 50 mm']

def prepare(data,outcome):
    d=data.loc[data.rain_windows_complete].copy()
    d['ym']=d.year*100+d.month; d.sort_values(['grid_id','ym','date_utc'],inplace=True)
    d['stratum']=d.groupby(['grid_id','ym'],sort=False).ngroup()
    s=d.groupby('stratum')[outcome].agg(['sum','size']); ids=s.index[(s['sum']>0)&(s['sum']<s['size'])]
    d=d.loc[d.stratum.isin(ids)].copy(); d['stratum']=d.groupby(['grid_id','ym'],sort=False).ngroup()
    binid=np.digitize(d.rain_1_7_mm.to_numpy(),[10,30,60,100],right=True)
    X=np.c_[(binid[:,None]==np.arange(4)).astype(float),d.rain_8_30_mm.to_numpy()/50]
    y=d[outcome].to_numpy(float); g=d.stratum.to_numpy(); first=np.r_[0,np.flatnonzero(np.diff(g))+1]
    n=np.diff(np.r_[first,len(d)]); k=np.add.reduceat(y,first).astype(int)
    means=np.add.reduceat(X,first)/n[:,None]; X=X-means[g]
    padded=np.zeros((len(first),n.max(),X.shape[1])); mask=np.zeros(padded.shape[:2],bool)
    pos=np.arange(len(d))-first[g]; padded[g,pos]=X; mask[g,pos]=True
    observed=np.add.reduceat(y[:,None]*X,first)
    return d,padded,mask,k,observed,first,len(s)

def moments(beta,X,mask,k):
    G,N,P=X.shape; K=k.max(); v=X@beta; vmax=np.max(np.where(mask,v,-np.inf),axis=1)
    weights=np.where(mask,np.exp(v-vmax[:,None]),0)
    Z=np.zeros((G,K+1)); Z[:,0]=1; M=np.zeros((G,K+1,P))
    for i in range(N):
        j=min(i+1,K); old=Z[:,:j].copy(); om=M[:,:j].copy(); w=weights[:,i,None]
        Z[:,1:j+1]+=w*old
        M[:,1:j+1]+=w[:,:,None]*(om+old[:,:,None]*X[:,i,None,:])
    z=Z[np.arange(G),k]; assert (z>0).all() and np.isfinite(z).all()
    expected=M[np.arange(G),k]/z[:,None]
    return np.log(z)+k*vmax,expected

def fit_model(data,outcome,label):
    d,X,mask,k,observed,first,total=prepare(data,outcome)
    def calc(b,full=False):
        logz,expected=moments(b,X,mask,k); scores=observed-expected
        if full:return scores
        return float(logz.sum()-observed.sum(axis=0)@b),-scores.sum(axis=0)
    fit=minimize(calc,np.zeros(X.shape[-1]),jac=True,method='BFGS',options={'gtol':1e-5,'maxiter':120})
    if np.max(np.abs(fit.jac))>1e-3:raise RuntimeError(f'{label}: gradient not converged {fit.jac}')
    scores=calc(fit.x,True); eps=1e-4; H=np.column_stack([(calc(fit.x+np.eye(5)[i]*eps)[1]-calc(fit.x-np.eye(5)[i]*eps)[1])/(2*eps) for i in range(5)]); H=(H+H.T)/2
    def meat(labels):
        _,ii=np.unique(labels,return_inverse=True); count=ii.max()+1
        agg=np.zeros((count,5)); np.add.at(agg,ii,scores)
        if count<2:raise RuntimeError('Insufficient clusters')
        return agg.T@agg,count
    m1,c1=meat(d.grid_id.to_numpy()[first]); m2,c2=meat(d.ym.to_numpy()[first]); mi,ci=meat(np.arange(len(first)))
    # Common finite-cluster multiplier and t critical value use the smaller
    # cluster dimension. This convention is applied to every specification.
    cluster_min=min(c1,c2); factor=cluster_min/(cluster_min-1)
    inv=np.linalg.inv(H); cov=inv@((m1+m2-mi)*factor)@inv
    if (np.diag(cov)<=0).any():raise RuntimeError('Nonpositive two-way variance')
    se=np.sqrt(np.diag(cov)); b=fit.x; critical=t.ppf(.975,cluster_min-1)
    rows=pd.DataFrame({'model':label,'outcome':outcome,'term':TERMS,'beta':b,'two_way_cluster_se':se,
        'odds_ratio':np.exp(b),'ci95_low':np.exp(b-critical*se),'ci95_high':np.exp(b+critical*se),
        'reference_rain7_mm':'>100','grid_days_available':len(data),'detected_grid_days_available':int(data[outcome].sum()),
        'strata_total':total,'informative_strata':len(first),'informative_grid_days':len(d),
        'spatial_clusters':c1,'temporal_clusters':c2,'ci_degrees_freedom':cluster_min-1,
        'maximum_absolute_gradient':np.max(np.abs(fit.jac))})
    return rows

def verify_core():
    X=np.array([[[1.,0,0,0,.1],[0,1,0,0,.2],[0,0,1,0,.4],[0,0,0,1,.3],[0,0,0,0,.5]]]); mask=np.ones((1,5),bool); k=np.array([2]); b=np.array([.8,-.2,.4,.1,-.4])
    logz,m=moments(b,X,mask,k); combinations=list(itertools.combinations(range(5),2)); sums=np.array([X[0,list(c)].sum(0) for c in combinations]); w=np.exp(sums@b)
    assert np.allclose(logz,np.log(w.sum()),rtol=1e-10) and np.allclose(m,(w[:,None]*sums).sum(0)/w.sum(),rtol=1e-10)
    eps=1e-6; fd=np.array([(moments(b+np.eye(5)[i]*eps,X,mask,k)[0]-moments(b-np.eye(5)[i]*eps,X,mask,k)[0])/(2*eps) for i in range(5)]).ravel()
    assert np.allclose(m[0],fd,atol=1e-6)
    return {'exact_subset_enumeration_check':True,'finite_difference_gradient_check':True}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); out=a.output
    d=pd.read_csv(out/'data/Panel_MODIS_GSMaP_2020_2025_Full_Year.csv.xz',parse_dates=['date_utc'])
    configs=[('Primary full year','any_type0',d),('Matched January–26 September','any_type0',d.loc[d.date_utc.dt.strftime('%m-%d').le('09-26')]),
        ('July–November','any_type0',d.loc[d.month.between(7,11)]),('Excluding 2023','any_type0',d.loc[d.year.ne(2023)]),
        ('All thermal anomalies','any_all',d),('High confidence, all types','any_high_conf_all',d),
        ('High confidence, vegetation type','any_confidence80',d),('Terra only','any_terra',d),('Aqua only','any_aqua',d),
        ('Daytime only','any_day',d),('Nighttime only','any_night',d),('Scan and track ≤1.5 km','any_small_footprint',d),
        ('Cell centre in ID 6','any_type0',d.loc[d.grid_centre_on_peat]),('At least 25% sampled peat','any_type0',d.loc[d.peat_fraction_25point.ge(.25)])]
    results=[]
    for label,outcome,data in configs:
        r=fit_model(data,outcome,label); results.append(r)
        print(label,r.iloc[0][['odds_ratio','ci95_low','ci95_high','informative_strata']].to_dict(),flush=True)
    table=pd.concat(results,ignore_index=True); table.to_csv(out/'tables/Table_S3_Rainfall_All_Sensitivity_Models.csv',index=False)
    table.loc[table.model.eq('Primary full year')].to_csv(out/'tables/Table_2_Rainfall_Primary.csv',index=False)
    table.loc[table.model.isin(['Primary full year','Terra only','Aqua only','Daytime only','Nighttime only','High confidence, vegetation type','Scan and track ≤1.5 km'])].to_csv(out/'tables/Table_S4_MODIS_Observation_Sensitivity.csv',index=False)
    (out/'evidence/Conditional_Logistic_Verification.json').write_text(json.dumps(verify_core(),indent=2))

if __name__=='__main__':main()
