"""Draw v0.27 validation panels directly from ready tables; never rerun or resample trials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/aidrbench-narrative-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':6.5,'legend.frameon':False,'text.parse_math':False,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'savefig.facecolor':'white'})
BLUE='#235A78';TEAL='#269383';ORANGE='#B27640';GRAY='#85929B';DARK='#293740'
CASES=['f05','f10','f20','f40','f60']

def label(ax,letter,title):
    ax.set_title(title,loc='left',pad=15)
    ax.annotate(letter,xy=(0,1.07),xycoords='axes fraction',xytext=(-23,0),textcoords='offset points',fontsize=11,fontweight='bold')

def save(fig,path,foot):
    fig.text(.04,.017,foot,fontsize=6.2,va='bottom',linespacing=1.5)
    fig.savefig(path.with_suffix('.pdf'));fig.savefig(path.with_suffix('.svg'))
    fig.savefig(path.with_suffix('.png'),dpi=300);fig.savefig(path.with_suffix('.tiff'),dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);used={}
    def read(name):
        p=a.data/name;used[name]=hashlib.sha256(p.read_bytes()).hexdigest();return pd.read_csv(p)
    selected=read('refinement_selected_confirmed.csv');pi=read('ready_pi_categories.csv');summary=read('timing_cross_summary.csv');week=read('weighted_week_summary.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,7.05));ax=axes.ravel()
    capacity=read('capacity_selected_confirmed.csv')
    values=[]
    for weight in ['job_count','resource_gpu_h']:
        g=capacity[capacity.weight==weight]
        assert g.offerable.all() and g.selected_capacity_kw.nunique()==1
        values.append(float(g.selected_capacity_kw.iloc[0]))
    bars=ax[0].bar([0,1],values,color=[BLUE,ORANGE],width=.55)
    ax[0].bar_label(bars,labels=[f'{v:.2f} kW' for v in values],padding=5,fontsize=8)
    for i in range(2):ax[0].text(i,.25,'300/300',ha='center',color='white',fontsize=8,fontweight='bold')
    ax[0].set_xticks([0,1],['Submission counts','Task resource-time'],fontsize=6.5)
    ax[0].set_ylim(0,3.85);ax[0].set_ylabel('Selected and confirmed offer (kW)')
    ax[0].text(.5,3.45,'2.0 × selected-offer ratio',ha='center',fontsize=7)
    label(ax[0],'a','Workload weights change the offer')
    variants=['u50d100g10','u65d100g10','u65d50g10','u65d50g20','u80d100g10'];left=np.zeros(5)
    for cat,color in [('Immediate shortage',GRAY),('Other infeasible',ORANGE),('PI feasible; causal failure',BLUE),('Both feasible',TEAL)]:
        z=pi[pi.category==cat].set_index('variant').cases.reindex(variants,fill_value=0).to_numpy();ax[1].barh(np.arange(5),z,left=left,color=color,label=cat,height=.65);left+=z
    assert np.array_equal(left,np.repeat(3,5));ax[1].set_yticks(range(5),['50 / ref / 10','65 / ref / 10','65 / tight / 10','65 / tight / 20','80 / ref / 10']);ax[1].invert_yaxis();ax[1].set_xticks([0,1,2,3]);ax[1].set_xlabel('Diagnostic cases (three per setting)');ax[1].set_ylabel('Utilisation / deadline / GPU share');ax[1].legend(loc='upper left',bbox_to_anchor=(-.16,-.18),ncol=2,fontsize=6.1,frameon=False,columnspacing=.7,handlelength=1)
    label(ax[1],'b','Same request, different limits')
    keys=[('job_count','chronological'),('job_count','permuted'),('resource_gpu_h','chronological'),('resource_gpu_h','permuted')]
    g=summary[summary.fraction==.5].set_index(['weight','ordering']).loc[keys]
    for j,(col,color,name) in enumerate([('successes_1pct',BLUE,'At most 1% missed work'),('successes_zero',TEAL,'Zero missed work')]):
        x=np.arange(4)+(j-.5)*.32;bars=ax[2].bar(x,g[col],.29,color=color,label=name)
        ax[2].bar_label(bars,padding=3,fontsize=6.3)
    ax[2].set_xticks(range(4),['Counts\nOriginal','Counts\nPermuted','GPU-h\nOriginal','GPU-h\nPermuted'],fontsize=6.3);ax[2].set_ylim(0,106);ax[2].set_yticks([0,20,40,60,80]);ax[2].set_ylabel('Successes at 2.95 kW (out of 80)');ax[2].legend(loc='upper right',frameon=False,fontsize=6.1)
    label(ax[2],'c','Weights and hourly order both matter')
    for weight,dx,color,name in [('job_count',-.18,BLUE,'Submission counts: 80/80'),('resource_gpu_h',.18,ORANGE,'Task resource-time: 31/80')]:
        w=week[(week.weight==weight)&(week.ordering=='chronological')&(week.fraction==.5)].sort_values('week');ax[3].bar(w.week+dx,w.successes_zero,.33,color=color,label=name)
    ax[3].set_ylim(0,14);ax[3].set_yticks([0,2,4,6,8,10]);ax[3].set_xticks(range(8),range(1,9));ax[3].set_xlabel('Observed week');ax[3].set_ylabel('Chronological zero-miss successes');ax[3].legend(loc='upper left',frameon=False,fontsize=6.2)
    label(ax[3],'d','Resource-time limits transfer by week')
    fig.subplots_adjust(left=.115,right=.98,top=.925,bottom=.125,wspace=.56,hspace=.95)
    save(fig,a.output/'AIDRBench_Figure_3','a: 300 independent model draws from eight fixed observed weeks; both service standards pass; lower bound 0.9911.\nb: three diagnostic cases per setting. c,d: eight observed weeks, each with ten synthetic realisations.\nAll comparisons retain 10% eligible work. The twofold ratio compares finite-grid offers for the stated distribution.')

    dev=read('capacity_development_summary.csv');conf=read('capacity_confirmation_summary.csv')
    fig=plt.figure(figsize=(7.205,6.6));grid=fig.add_gridspec(2,2,height_ratios=[1,1]);ax=[fig.add_subplot(grid[0,0]),fig.add_subplot(grid[0,1]),fig.add_subplot(grid[1,:])]
    for j,(endpoint,color,marker,name) in enumerate([('success_1pct',BLUE,'o','At most 1% missed work'),('success_zero',TEAL,'s','Zero missed work')]):
        z=selected[selected.endpoint==endpoint].set_index('program').loc[['H4P16','H8P16']];y=z.confirmation_successes.to_numpy()/300
        ax[0].errorbar(np.arange(2)+(j-.5)*.15,y,yerr=[y-z.confirmation_lower,np.zeros(2)],fmt=marker,color=color,ms=5,capsize=3,label=name)
    for i,p in enumerate(['H4P16','H8P16']):
        k=selected[selected.program==p].selected_capacity_kw.iloc[0];ax[0].text(i,1.015,f'{k:.2f} kW',ha='center',fontsize=8)
    ax[0].axhline(.95,color=GRAY,ls='--',lw=.8);ax[0].set_ylim(.942,1.04);ax[0].set_xlim(-.5,1.5);ax[0].set_yticks([.95,.975,1]);ax[0].set_ylabel('Success fraction and lower bound');ax[0].set_xticks([0,1],['Four hours','Eight hours']);ax[0].legend(loc='upper center',bbox_to_anchor=(.5,-.15),frameon=False,fontsize=6.1)
    label(ax[0],'a','Reference workload: duration products')
    for weight,color,title in [('job_count',BLUE,'Counts'),('resource_gpu_h',ORANGE,'Resource-time')]:
        for endpoint,style,marker,rule in [('success_1pct','-','o','1%'),('success_zero','--','s','zero')]:
            g=dev[(dev.weight==weight)&(dev.endpoint==endpoint)].sort_values('capacity_kw')
            ax[1].plot(g.capacity_kw,g.wilson_lower,color=color,ls=style,marker=marker,ms=3,lw=.8,label=title+'; '+rule)
    ax[1].axhline(.95,color=GRAY,ls=':',lw=.8);ax[1].set_ylim(-.03,1.08);ax[1].set_xlabel('Tested request (kW)');ax[1].set_ylabel('Development Wilson lower bound');ax[1].legend(loc='lower left',fontsize=6.1)
    label(ax[1],'b','Observed-week mixture: candidate grid')
    keys=[('job_count',.5),('resource_gpu_h',.25),('resource_gpu_h',.5)]
    for j,(endpoint,color,marker,name) in enumerate([('success_1pct',BLUE,'o','At most 1% missed work'),('success_zero',TEAL,'s','Zero missed work')]):
        g=conf[conf.endpoint==endpoint].set_index(['weight','fraction']).loc[keys];y=g.successes/g.trials
        ax[2].errorbar(np.arange(3)+(j-.5)*.07,y,yerr=[y-g.wilson_lower,np.zeros(3)],fmt=marker,color=color,ms=5,capsize=3,label=name)
    for i,(n,y) in enumerate([(300,1.045),(300,1.045),(120,.45)]):ax[2].text(i,y,f'{n}/300',ha='center',fontsize=7)
    ax[2].axhline(.95,color=GRAY,ls='--',lw=.8);ax[2].set_ylim(.28,1.13);ax[2].set_yticks([.4,.6,.8,1.]);ax[2].set_xlim(-.45,2.45);ax[2].set_xticks(range(3),['Counts: 2.95 kW\nSelected','Resource-time: 1.47 kW\nSelected','Resource-time: 2.95 kW\nFixed comparator']);ax[2].set_ylabel('Success fraction and lower bound');ax[2].legend(loc='lower left',ncol=2,fontsize=6.3)
    label(ax[2],'c','Observed-week mixture: independent confirmation')
    fig.subplots_adjust(left=.125,right=.98,top=.91,bottom=.17,wspace=.52,hspace=.75)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_9','a: 300 reference-distribution scenarios per duration; retained from the earlier figure set.\nb: 100 development draws per point. c: 300 new confirmation draws per point; no confirmation reselection.\nb,c condition on eight fixed weekly profiles; four eight-hour calls start 16 h apart. All bounds are pointwise.')

    power=json.loads((a.data/'power_reconciliation.json').read_text());used['power_reconciliation.json']=hashlib.sha256((a.data/'power_reconciliation.json').read_bytes()).hexdigest()
    overhead=read('fixed_overhead_summary.csv');pairs=read('pv_precision_pairs.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.7));ax=axes.ravel()
    vals=list(power['facility_components'].values());names=['Node overhead','All-GPU idle','Rigid increment','Flexible increment']
    ax[0].barh(np.arange(4),vals,color=[GRAY,'#BCC5C9',BLUE,TEAL],height=.6)
    for i,v in enumerate(vals):ax[0].text(v+2,i,f'{v:.2f}',fontsize=7,va='center')
    ax[0].set_yticks(range(4),names,fontsize=6.5);ax[0].invert_yaxis();ax[0].set_xlim(0,139);ax[0].set_xlabel('Facility power including PUE (kW)');label(ax[0],'a','Components of the 193.44-kW peak')
    g=overhead[overhead.program=='H4P16'].sort_values('node_overhead_w');ax[1].plot(g.node_overhead_w,g.single_offer_pct_peak,'o-',color=BLUE,ms=4,lw=1)
    for row in g.itertuples():ax[1].annotate(f'{row.operating_peak_kw:.2f} kW',xy=(row.node_overhead_w,row.single_offer_pct_peak),xytext=(0,9),textcoords='offset points',ha='center',fontsize=6.1)
    ax[1].set_xlim(110,640);ax[1].set_ylim(2.15,3.85);ax[1].set_xticks([150,300,450,600]);ax[1].set_xlabel('Fixed overhead (W/node)');ax[1].set_ylabel('5.90-kW offer / operating peak (%)');label(ax[1],'b','Overhead changes the denominator')
    for i,bess in enumerate([False,True],2):
        g=pairs[(pairs.case=='f10')&(pairs.bess_enabled==bess)&(pairs.analysis=='fixed_pv_operation')];assert len(g)==100
        ax[i].scatter(g.previous_gain,g.strict_gain,s=17,color=TEAL if bess else BLUE,alpha=.65,edgecolor='white',lw=.3)
        end=max(g.previous_gain.max(),g.strict_gain.max())*1.12;start=min(g.previous_gain.min(),g.strict_gain.min(),0)-end*.055
        ax[i].plot([start,end],[start,end],'--',color=GRAY,lw=.75);ax[i].axhline(0,color=GRAY,lw=.6);ax[i].set_xlim(start,end);ax[i].set_ylim(start,end)
        ax[i].set_xlabel('Original utilisation gain (pp)');ax[i].set_ylabel('Strict utilisation gain (pp)');ax[i].ticklabel_format(axis='both',style='sci',scilimits=(-2,2),useMathText=False)
        label(ax[i],'cd'[i-2],'With BESS: gain resolves to zero' if bess else 'No BESS: LP gain is unchanged')
    fig.subplots_adjust(left=.19,right=.98,top=.91,bottom=.16,wspace=.57,hspace=.77)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_10','a,b: deterministic accounting; all hardware and eligible work otherwise fixed. Labels in b give operating peak.\nc,d: 100 paired scenarios; dashed line denotes equality. Strict relative/absolute MIP gaps 1e-7; feasibility 1e-8.\nBESS primary PV-use bounds and the 1e-5-kWh lexicographic lock are distinguished in Table 24; full data retained.')
    outputs={}
    for name in ['AIDRBench_Figure_3','AIDRBench_Supplementary_Figure_9','AIDRBench_Supplementary_Figure_10']:
        for ext in ['pdf','svg','png','tiff']:
            p=a.output/f'{name}.{ext}';outputs[p.name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    (a.output/'validation_plot_manifest.json').write_text(json.dumps(dict(version='0.27',source_tables=used,outputs=outputs),indent=2)+'\n')

if __name__=='__main__':main()
