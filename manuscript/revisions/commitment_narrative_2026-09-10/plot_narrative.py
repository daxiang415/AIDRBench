"""Draw v0.25 panels directly from ready tables; never rerun or resample trials."""
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

plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':6.5,'text.parse_math':False,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'savefig.facecolor':'white'})
BLUE='#235A78';TEAL='#269383';ORANGE='#B27640';GRAY='#85929B';DARK='#293740'
CASES=['f05','f10','f20','f40','f60']

def label(ax,letter,title):
    ax.set_title(title,loc='left',pad=15)
    ax.annotate(letter,xy=(0,1.07),xycoords='axes fraction',xytext=(-23,0),textcoords='offset points',fontsize=11,fontweight='bold')

def save(fig,path,foot):
    fig.text(.04,.017,foot,fontsize=6.2,va='bottom',linespacing=1.5)
    fig.savefig(path.with_suffix('.pdf'));fig.savefig(path.with_suffix('.svg'))
    fig.savefig(path.with_suffix('.png'),dpi=300);fig.savefig(path.with_suffix('.tiff'),dpi=600)
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);used={}
    def read(name):
        p=a.data/name;used[name]=hashlib.sha256(p.read_bytes()).hexdigest();return pd.read_csv(p)
    selected=read('refinement_selected_confirmed.csv');pi=read('ready_pi_categories.csv');summary=read('timing_cross_summary.csv');week=read('weighted_week_summary.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,7.05));ax=axes.ravel()
    for j,(endpoint,color,marker,name) in enumerate([('success_1pct',BLUE,'o','At most 1% missed work'),('success_zero',TEAL,'s','Zero missed work')]):
        z=selected[selected.endpoint==endpoint].set_index('program').loc[['H4P16','H8P16']];y=z.confirmation_successes.to_numpy()/300
        ax[0].errorbar(np.arange(2)+(j-.5)*.15,y,yerr=[y-z.confirmation_lower,np.zeros(2)],fmt=marker,color=color,ms=5,capsize=3,label=name)
    for i,p in enumerate(['H4P16','H8P16']):
        k=selected[selected.program==p].selected_capacity_kw.iloc[0]
        ax[0].text(i,1.015,f'{k:.2f} kW',ha='center',fontsize=8)
    ax[0].axhline(.95,color=GRAY,ls='--',lw=.8);ax[0].set_ylim(.942,1.045);ax[0].set_xlim(-.5,1.5);ax[0].set_yticks([.95,.975,1]);ax[0].set_ylabel('Success fraction and lower bound');ax[0].set_xticks([0,1],['Four hours','Eight hours']);ax[0].legend(loc='upper center',bbox_to_anchor=(.5,-.15),frameon=False)
    label(ax[0],'a','Independently qualified duration products')
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
    save(fig,a.output/'AIDRBench_Figure_3','10% eligible work; four calls. a: n = 300 independent scenarios per product; 95% overall success target.\nb: prespecified mechanism cases, not a prevalence estimate. c,d: eight observed weeks × ten synthetic realisations.\nHourly permutation changes order and alignment with calls and community demand; it does not isolate autocorrelation.')

    pairs=read('paired_resource_supply_margins.csv');example=read('supply_hourly_example.csv')
    fig=plt.figure(figsize=(7.205,7.35));grid=fig.add_gridspec(2,2,height_ratios=[1,1.22]);ax1=fig.add_subplot(grid[0,0]);ax2=fig.add_subplot(grid[0,1]);flow=fig.add_subplot(grid[1,:])
    ax1.scatter(pairs.chronological,pairs.permuted,color=BLUE,s=20,alpha=.7,edgecolor='white',linewidth=.35)
    ax1.axvline(0,color=GRAY,ls='--',lw=.8);ax1.axhline(0,color=GRAY,ls='--',lw=.8)
    ax1.set_xlim(-1.3,1.5);ax1.set_ylim(-1.75,3.2);ax1.set_xticks([-1,0,1]);ax1.set_xlabel('Original minimum margin (kW)');ax1.set_ylabel('Permuted minimum margin (kW)')
    for xy,condition,alignment in [((-.08,3.03),(pairs.chronological<0)&(pairs.permuted>=0),'right'),((.08,3.03),(pairs.chronological>=0)&(pairs.permuted>=0),'left'),((-.08,-1.6),(pairs.chronological<0)&(pairs.permuted<0),'right'),((.08,-1.6),(pairs.chronological>=0)&(pairs.permuted<0),'left')]:
        n=int(condition.sum());ax1.text(*xy,f'{n} realisations',fontsize=6.2,ha=alignment,color=DARK)
    label(ax1,'a','Paired changes in the supply margin')
    for weight,color,name in [('job_count',BLUE,'Submission counts'),('resource_gpu_h',ORANGE,'Task resource-time')]:
        e=example[(example.weight==weight)&(example.ordering=='chronological')&(example.hour<168)].sort_values('hour')
        ax2.step(e.hour,e.available_reduction_kw,where='post',color=color,lw=.85,label=name)
    req=float(e.request_kw.iloc[0]);ax2.axhline(.95*req,color=DARK,ls='--',lw=.8,label='Required delivery (95%)')
    for _,g in e[e.event_active].groupby('event_id'):ax2.axvspan(g.hour.min(),g.hour.max()+1,color=GRAY,alpha=.18,lw=0)
    ax2.set_xlim(0,168);ax2.set_ylim(-.8,27);ax2.set_xticks([0,48,96,144]);ax2.set_yticks([0,5,10,15,20]);ax2.set_xlabel('Hour in the arrival horizon');ax2.set_ylabel('Available baseline reduction (kW)');ax2.legend(loc='upper left',ncol=1,frameon=False,fontsize=6.1)
    label(ax2,'b','Low-supply hours rule out delivery')
    flow.set_axis_off();flow.set_xlim(0,1);flow.set_ylim(0,1)
    flow.text(-.04,1.06,'c',fontweight='bold',fontsize=11,transform=flow.transAxes);flow.text(0,1.06,'Different evidence supports different decisions',fontsize=9,transform=flow.transAxes)
    steps=read('decision_steps.csv')[['step','criterion','decision']].itertuples(index=False,name=None)
    for i,(title,detail,decision) in enumerate(steps):
        y=.92-i*.235
        flow.add_patch(FancyBboxPatch((.014,y-.115),.556,.15,boxstyle='round,pad=0.012,rounding_size=0.012',edgecolor=BLUE,facecolor='#F3F7F8',linewidth=.75))
        flow.text(.030,y+.005,title,fontsize=7.4,va='center',fontweight='bold',color=DARK)
        flow.text(.030,y-.067,detail,fontsize=6.2,va='center',color=DARK)
        flow.annotate('',xy=(.62,y-.035),xytext=(.582,y-.035),arrowprops={'arrowstyle':'->','color':GRAY,'lw':.8})
        flow.text(.635,y-.035,decision,fontsize=6.4,va='center',linespacing=1.4,color=DARK)
        if i<3:flow.annotate('',xy=(.285,y-.19),xytext=(.285,y-.128),arrowprops={'arrowstyle':'->','color':BLUE,'lw':.8})
    fig.subplots_adjust(left=.115,right=.98,top=.91,bottom=.12,wspace=.53,hspace=.49)
    save(fig,a.output/'AIDRBench_Figure_4','a: all 80 paired resource-time realisations; fixed 2.95 kW; negative margin is an instantaneous shortage.\nb: lowest protocol seed, 990000, selected without reference to outcome; shaded hours are calls. Full 216-h data retained.\nc: a scenario failure is not automatic rejection of a probabilistic contract; a feasible PI schedule is not a causal certificate.')

    dev=read('refinement_development_summary.csv');structural=read('confirmation_summary.csv');cross=read('external_cross_score_weekly.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.9));ax=axes.ravel()
    for i,p in enumerate(['H4P16','H8P16']):
        for endpoint,color,marker,name in [('success_1pct',BLUE,'o','At most 1%'),('success_zero',TEAL,'s','Zero missed work')]:
            g=dev[(dev.program==p)&(dev.endpoint==endpoint)].sort_values('capacity_kw');ax[i].plot(g.capacity_kw,g.wilson_lower,marker=marker,ms=4,color=color,label=name)
        ax[i].axhline(.95,color=GRAY,ls='--',lw=.8);ax[i].set_ylim(.83,1);ax[i].set_ylabel('Development Wilson lower bound');ax[i].set_xlabel('Tested request (kW)');ax[i].legend(frameon=False,loc='lower left');label(ax[i],'ab'[i],['Four-hour local candidate grid','Eight-hour local candidate grid'][i])
    variants=[f'u{u}d{d}g10' for u in [50,65,80] for d in [100,50]]
    g=structural[(structural.program=='H8P16')&(structural.kind=='repeated')&(structural.fraction==1)&(structural.endpoint=='success_1pct')].set_index('variant').loc[variants];x=np.arange(6)
    ax[2].bar(x-.17,g.instantaneous_supply_limited_trials/3,.31,color=GRAY,label='Immediate shortage');ax[2].bar(x+.17,g.failed_deadline_miss/3,.31,color=ORANGE,label='More than 1% missed');ax[2].set_xticks(x,['50 / ref','50 / tight','65 / ref','65 / tight','80 / ref','80 / tight'],rotation=35,ha='right',rotation_mode='anchor');ax[2].set_ylim(0,132);ax[2].set_yticks([0,25,50,75,100]);ax[2].set_ylabel('Scenarios affected (%)');ax[2].legend(frameon=False,fontsize=6.2,loc='upper left');label(ax[2],'c','Broader structural context')
    g=cross[cross.fraction==.75].sort_values('week');x=g.week.to_numpy()
    ax[3].bar(x,g.successes_zero,color=BLUE,label='Success at 4.42 kW');ax[3].bar(x,g.instantaneous_shortage,bottom=g.successes_zero,color=GRAY,label='Immediate shortage');ax[3].plot(x,np.repeat(10,8),'D',color=TEAL,ms=4,label='At 2.95 kW: all succeed');ax[3].set_ylim(0,14);ax[3].set_yticks([0,2,4,6,8,10]);ax[3].set_xticks(range(8),range(1,9));ax[3].set_xlabel('Observed week');ax[3].set_ylabel('Realisations per week');ax[3].legend(loc='upper left',fontsize=6.2,frameon=False);label(ax[3],'d','Fixed-request cross-scoring agrees')
    fig.subplots_adjust(left=.125,right=.98,top=.91,bottom=.18,wspace=.5,hspace=.7)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_3','a,b: n = 100 independent development scenarios per candidate; finite grid. c: n = 300; failure families may overlap.\nd: separate 986000-series count test; both service scores coincide at each request; no binomial confidence inference.\nMatched last-call outcomes remain in Table 15; historical selection and score interpretation are in Supplementary Note 7.')

    pv=read('renewable_paired_comparisons.csv');single=read('single_confirm_summary.csv');controls=read('control_causal_summary.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.6));ax=axes.ravel();x=np.arange(5)
    for bess,color,offset in [(False,BLUE,-.07),(True,TEAL,.07)]:
        name='With BESS' if bess else 'Without BESS'
        host=pv[(pv.analysis=='pv_hosting')&(pv.bess_enabled==bess)].set_index('case').loc[CASES]
        use=pv[(pv.analysis=='fixed_pv_operation')&(pv.bess_enabled==bess)].set_index('case').loc[CASES]
        ax[0].scatter(x+offset,host.difference_of_all_scenario_minima,color=color,label=name,s=26)
        ax[1].errorbar(x+offset,use.mean_paired_gain,yerr=[use.mean_paired_gain-use.gain_ci_low,use.gain_ci_high-use.mean_paired_gain],fmt='o',color=color,ms=4,capsize=2,label=name)
    for item in ax[:2]:item.set_xticks(x,['5','10','20','40*','60*']);item.set_xlabel('Eligible work (%)');item.axhline(0,color=GRAY,lw=.7);item.legend(loc='upper left',frameon=False)
    ax[0].set_ylabel('PV hosting gain (kW)');ax[1].set_ylabel('Utilisation gain (percentage points)');label(ax[0],'a','Additional PV hosting');label(ax[1],'b','Use of a fixed 500-kW PV system')
    obs=pd.concat([single[single.notice_h==0],controls]);cset=['f10','f10_g20','f10_g30','f10_rigid150','f10_rigid225']
    for duration,color,offset in [(4,BLUE,-.07),(8,TEAL,.07)]:
        g=obs[obs.duration_h==duration].set_index('case').loc[cset];y=g.successes/g.trials*100
        ax[2].errorbar(x+offset,y,yerr=[y-g.wilson_lower*100,np.zeros(5)],fmt='o',color=color,capsize=2,ms=4,label=f'{duration} h')
    ax[2].axhline(95,color=GRAY,ls='--',lw=.8);ax[2].set_ylim(85,102);ax[2].set_ylabel('Success (%)')
    for bess,color,offset in [(False,BLUE,-.07),(True,TEAL,.07)]:
        g=pv[(pv.analysis=='pv_hosting')&(pv.bess_enabled==bess)].set_index('case').loc[cset];ax[3].scatter(x+offset,g.difference_of_all_scenario_minima,color=color,s=26,label='With BESS' if bess else 'Without BESS')
    ax[3].axhline(0,color=GRAY,lw=.6);ax[3].set_ylabel('PV hosting gain (kW)')
    for item in ax[2:]:item.set_xticks(x,['Primary','GPUs\n20%','GPUs\n30%','Rigid\n150 W','Rigid\n225 W'],fontsize=6.4);item.legend(loc='lower left' if item is ax[2] else 'upper left',frameon=False,fontsize=6.3)
    label(ax[2],'c','Transfer of the same single-event offer');label(ax[3],'d','PV responds to allocation controls')
    fig.subplots_adjust(left=.13,right=.98,top=.91,bottom=.15,wspace=.57,hspace=.72)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_4','a,b: five permission scenarios; *40% and 60% require additional business assumptions. PV: n = 100, zero missed work.\nb: paired 95% bootstrap intervals cover sampling, not optimisation error; tiny BESS effects are unresolved.\nc,d: fixed 10% work eligibility. c: n = 300; one-sided 95% Wilson bounds. Hosting gains are differences of minima.')
    outputs={}
    for prefix,n in [('AIDRBench_Figure_',3),('AIDRBench_Figure_',4),('AIDRBench_Supplementary_Figure_',3),('AIDRBench_Supplementary_Figure_',4)]:
        for ext in ['pdf','svg','png','tiff']:
            p=a.output/f'{prefix}{n}.{ext}';outputs[p.name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    (a.output/'narrative_manifest.json').write_text(json.dumps(dict(version='0.25',source_tables=used,outputs=outputs),indent=2)+'\n')

if __name__=='__main__':main()
