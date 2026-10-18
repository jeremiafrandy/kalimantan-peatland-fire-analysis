"""Generate manuscript figures from the same authoritative CSV tables.

The sensor/CAMS inputs are the verified raw-data rerun outputs from 5 Oct 2026.
This script does not infer source-specific smoke exposure or health outcomes.
"""
from pathlib import Path
import argparse, json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Patch
from matplotlib.lines import Line2D
from scipy.stats import spearmanr

GREEN,RED,BLACK='#378970','#c6272f','#171c20'

def poly_parts(geom):return [geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']

def ring(coords,hole=False):
    r=np.asarray(coords); stride=max(1,math.ceil((len(r)-1)/950)); r=np.vstack([r[:-1:stride],r[0]])
    area=np.sum(r[:-1,0]*r[1:,1]-r[1:,0]*r[:-1,1])/2
    if (area<0)!=hole:r=r[::-1]
    return r

def maps(ax,provinces,peat):
    for f in peat:
        for p in poly_parts(f['geometry']):
            vertices=[];codes=[]
            for i,raw in enumerate(p):
                r=ring(raw,i>0);vertices.extend(r);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(r)-2)+[MPath.CLOSEPOLY])
            ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=GREEN,edgecolor='none',alpha=.77,rasterized=True))
    for f in provinces:
        for p in poly_parts(f['geometry']):
            r=ring(p[0]);ax.plot(r[:,0],r[:,1],color='#566f80',lw=.55)
    ax.set(xlim=(108,120),ylim=(-5,5),xlabel='Longitude (°E)',ylabel='Latitude (°)')
    ax.set_aspect('equal');ax.set_xticks([108,111,114,117,120]);ax.set_yticks([-5,-2.5,0,2.5,5]);ax.grid(alpha=.15)

def save(fig,out,name):
    for ext in ['png','pdf']:fig.savefig(out/'figures'/f'{name}.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=a.output
    plt.rcParams.update({'font.size':11,'font.family':'DejaVu Sans','savefig.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
    provinces=json.loads((a.raw/'batas_5_provinsi_kalimantan.geojson').read_text())['features'];peat=json.loads((a.raw/'BIGID6 200').read_text())['features']
    modis=pd.read_csv(out/'data/MODIS_Classified_2020_2026.csv.xz',parse_dates=['date_utc'],low_memory=False)
    matched=modis.loc[modis.date_utc.dt.strftime('%m-%d').le('09-26')]
    fig,axs=plt.subplots(1,2,figsize=(12,5.8),layout='constrained')
    for ax,y,letter in zip(axs,[2023,2026],['A','B']):
        maps(ax,provinces,peat);g=matched.loc[matched.year.eq(y)]
        for ispeat,c,alpha,size in [(False,BLACK,.35,2.6),(True,RED,.65,3.4)]:
            s=g.loc[g.inside_ID6.eq(ispeat)];ax.scatter(s.longitude,s.latitude,s=size,c=c,alpha=alpha,lw=0,rasterized=True)
        ax.set_title(f'{letter}  {y}'+(' provisional' if y==2026 else ' archive'),loc='left',weight='bold')
    fig.legend(handles=[Patch(color=GREEN,label='Mapped peatland (ID 6)'),Line2D([],[],marker='o',color=RED,linestyle='',label='Detection within ID 6'),Line2D([],[],marker='o',color=BLACK,linestyle='',label='Detection outside ID 6')],loc='outside upper center',ncol=3,frameon=False)
    save(fig,out,'Figure_2_MODIS_ID6_2023_2026')
    primary=pd.read_csv(out/'tables/Table_2_Rainfall_Primary.csv').iloc[:4]
    fig,ax=plt.subplots(figsize=(7.2,4.0),layout='constrained');x=np.arange(4)
    ax.errorbar(x,primary.odds_ratio,yerr=np.vstack([primary.odds_ratio-primary.ci95_low,primary.ci95_high-primary.odds_ratio]),fmt='o',color=GREEN,capsize=5,lw=1.8)
    ax.axhline(1,color='#777777',ls='--',lw=1);ax.set_yscale('log');ax.set_xticks(x,['0–10','>10–30','>30–60','>60–100']);ax.set_xlabel('Rainfall over the preceding seven days (mm)');ax.set_ylabel('Odds ratio for a MODIS detection day');ax.set_ylim(.5,22)
    ax.text(.97,.97,'Reference: >100 mm',transform=ax.transAxes,ha='right',va='top',fontsize=10)
    save(fig,out,'Figure_3_Rainfall_Detection_Odds')
    sensor=pd.read_csv(out/'evidence/Sensor_Daily_Reproduced.csv',parse_dates=['date']).set_index('date')
    cams=pd.read_csv(out/'evidence/CAMS_Cell_Daily_UTC_WIB.csv',parse_dates=['date']).set_index('date')
    burn=pd.read_csv(out/'data/Burned_Area_Daily_2023.csv',parse_dates=['date']).set_index('date')
    daily=sensor.join(cams[['cams_utc_ug_m3','cams_wib_ug_m3']],validate='one_to_one').join(burn,validate='one_to_one')
    daily.to_csv(out/'data/Sensor_CAMS_Burn_Daily_2023.csv')
    monthly=daily.groupby(daily.index.month).agg(sensor_mean=('pm25_reporting_sites','mean'),fixed_two_mean=('pm25_fixed_two_sites','mean'),excluding_KR06_mean=('pm25_without_KR06','mean'),cams_UTC_mean=('cams_utc_ug_m3','mean'),cams_WIB_mean=('cams_wib_ug_m3','mean'),days=('pm25_reporting_sites','count'))
    monthly.index.name='month';monthly.to_csv(out/'tables/Table_S7_Sensor_CAMS_Monthly.csv')
    corr=[]
    for column in ['cams_utc_ug_m3','cams_wib_ug_m3','burned_within_ID6_km2','burned_outside_ID6_km2']:
        pair=daily[['pm25_reporting_sites',column]].dropna();changes=pair.diff().dropna()
        corr.append({'comparison':column,'paired_days':len(pair),'rho_levels':spearmanr(pair.iloc[:,0],pair.iloc[:,1]).statistic,'rho_first_differences':spearmanr(changes.iloc[:,0],changes.iloc[:,1]).statistic,'comparison_mean':pair.iloc[:,1].mean(),'sensor_mean':pair.iloc[:,0].mean()})
    pd.DataFrame(corr).to_csv(out/'tables/Table_S8_Sensor_CAMS_Burn_Comparisons.csv',index=False)
    bmonthly=pd.read_csv(out/'tables/Table_S5_Burned_Area_Monthly.csv')
    fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained');x=np.arange(4)
    for name,c,offset in [('Within BIG ID 6',GREEN,-.19),('Outside BIG ID 6','#777777',.19)]:
        vals=bmonthly.loc[bmonthly['class'].eq(name)].sort_values('month');axs[0].bar(x+offset,vals.burned_fraction_percent,width=.36,color=c,label=name)
    axs[0].set_xticks(x,['Aug','Sep','Oct','Nov']);axs[0].set_ylabel('Monthly burned fraction of valid land (%)');axs[0].set_title('A  Mapped burning',loc='left',weight='bold');axs[0].legend(frameon=False,fontsize=9)
    axs[1].plot(x,monthly.sensor_mean,'o-',color=RED,label='Published outdoor sensors');axs[1].plot(x,monthly.cams_UTC_mean,'s--',color='#426f91',label='CAMS shared cell (UTC)');axs[1].set_xticks(x,['Aug*','Sep','Oct','Nov']);axs[1].set_ylabel('PM₂.₅ (µg m⁻³)');axs[1].set_title('B  Air-quality context',loc='left',weight='bold');axs[1].legend(frameon=False,fontsize=9)
    save(fig,out,'Figure_4_Burning_and_PM25_2023')
    sensitivity=pd.read_csv(out/'tables/Table_S4_MODIS_Observation_Sensitivity.csv');s=sensitivity.loc[sensitivity.term.eq('0–10')].iloc[::-1]
    fig,ax=plt.subplots(figsize=(8,4.3),layout='constrained');y=np.arange(len(s));ax.errorbar(s.odds_ratio,y,xerr=np.vstack([s.odds_ratio-s.ci95_low,s.ci95_high-s.odds_ratio]),fmt='o',color=GREEN,capsize=4);ax.set_yticks(y,s.model);ax.set_xscale('log');ax.axvline(1,color='#777777',ls='--');ax.set_xlabel('Odds ratio: 0–10 mm versus >100 mm preceding rainfall');ax.set_xlim(.8,70)
    save(fig,out,'Figure_S2_MODIS_Observation_Sensitivity')
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    for col,label,c,ls in [('pm25_reporting_sites','Reporting sensor sites',RED,'-'),('pm25_fixed_two_sites','Fixed two sites',GREEN,':'),('cams_utc_ug_m3','CAMS UTC','#426f91','--')]:ax.plot(daily.index,daily[col],label=label,color=c,ls=ls,lw=1.2)
    ax.set_ylabel('PM₂.₅ (µg m⁻³)');ax.legend(frameon=False,fontsize=9);ax.set_xlabel('Date in 2023');save(fig,out,'Figure_S3_Daily_PM25_2023')
    print(json.dumps({'October_sensor_mean':monthly.loc[10,'sensor_mean'],'paired_days':len(daily),'correlations':corr},default=float))

if __name__=='__main__':main()
