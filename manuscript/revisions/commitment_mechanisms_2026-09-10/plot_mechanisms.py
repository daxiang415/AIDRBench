"""Publication figures from ready tables only; no simulation, fitting or resampling."""
import argparse,hashlib,json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/aidrbench-mechanism-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':6.5,'text.parse_math':False,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'savefig.facecolor':'white'})
BLUE='#235A78';TEAL='#269383';ORANGE='#B27640';GRAY='#85929B';DARK='#293740'
BASE=[f'u{u}d{d}g10' for u in [50,65,80] for d in [100,50]]
def label(ax,letter,title):
    ax.set_title(title,loc='left',pad=15)
    ax.annotate(letter,xy=(0,1.07),xycoords='axes fraction',xytext=(-23,0),textcoords='offset points',fontsize=11,fontweight='bold')
def save(fig,path,foot):
    fig.text(.04,.017,foot,fontsize=6.2,va='bottom',linespacing=1.5)
    fig.savefig(path.with_suffix('.pdf'));fig.savefig(path.with_suffix('.svg'))
    fig.savefig(path.with_suffix('.png'),dpi=300);fig.savefig(path.with_suffix('.tiff'),dpi=600);plt.close(fig)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--previous-data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);used={}
    def read(name,old=False):
        path=(a.previous_data if old else a.data)/name;used[('previous/' if old else '')+name]=hashlib.sha256(path.read_bytes()).hexdigest();return pd.read_csv(path)
    selected=read('refinement_selected_confirmed.csv');pi=read('ready_pi_categories.csv');cross=read('external_cross_score_weekly.csv');week=read('weighted_week_summary.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,7.05));ax=axes.ravel()
    for j,(endpoint,color,marker,name) in enumerate([('success_1pct',BLUE,'o','At most 1% missed work'),('success_zero',TEAL,'s','Zero missed work')]):
        z=selected[selected.endpoint==endpoint].set_index('program').loc[['H4P16','H8P16']];y=z.confirmation_successes.to_numpy()/300
        ax[0].errorbar(np.arange(2)+(j-.5)*.15,y,yerr=[y-z.confirmation_lower,np.zeros(2)],fmt=marker,color=color,ms=5,capsize=3,label=name)
    for i,k in enumerate([5.603331,4.423682]):ax[0].text(i,1.015,f'{k:.2f} kW',ha='center',fontsize=8)
    ax[0].axhline(.95,color=GRAY,ls='--',lw=.8);ax[0].set_ylim(.942,1.045);ax[0].set_xlim(-.5,1.5);ax[0].set_yticks([.95,.975,1]);ax[0].set_ylabel('Success fraction and lower bound');ax[0].set_xticks([0,1],['Four hours','Eight hours']);ax[0].legend(loc='upper center',bbox_to_anchor=(.5,-.15),frameon=False)
    label(ax[0],'a','Refinement changes the chosen products')
    variants=['u50d100g10','u65d100g10','u65d50g10','u65d50g20','u80d100g10'];left=np.zeros(5)
    for cat,color in [('Immediate shortage',GRAY),('Other infeasible',ORANGE),('PI feasible; causal failure',BLUE),('Both feasible',TEAL)]:
        z=pi[pi.category==cat].set_index('variant').cases.reindex(variants,fill_value=0).to_numpy();ax[1].barh(np.arange(5),z,left=left,color=color,label=cat,height=.65);left+=z
    assert np.array_equal(left,np.repeat(3,5));ax[1].set_yticks(range(5),['50 / ref / 10','65 / ref / 10','65 / tight / 10','65 / tight / 20','80 / ref / 10']);ax[1].invert_yaxis();ax[1].set_xticks([0,1,2,3]);ax[1].set_xlabel('Diagnostic cases (three per setting)');ax[1].set_ylabel('Utilisation / deadline / GPU share');ax[1].legend(loc='upper left',bbox_to_anchor=(-.16,-.18),ncol=2,fontsize=6.1,frameon=False,columnspacing=.7,handlelength=1)
    label(ax[1],'b','Same request, different limits')
    z=cross[cross.fraction==.75].sort_values('week');x=z.week.to_numpy()
    ax[2].bar(x,z.successes_zero,color=BLUE,label='Success at 4.42 kW');ax[2].bar(x,z.instantaneous_shortage,bottom=z.successes_zero,color=GRAY,label='Immediate shortage')
    ax[2].plot(x,np.repeat(10,8),'D',color=TEAL,ms=4,label='At 2.95 kW: all succeed');ax[2].set_ylim(0,14);ax[2].set_yticks([0,2,4,6,8,10]);ax[2].set_xticks(range(8),range(1,9));ax[2].set_xlabel('Observed week');ax[2].set_ylabel('Realisations per week');ax[2].legend(loc='upper left',fontsize=6.2,frameon=False)
    label(ax[2],'c','Both scores give the same outcome')
    for weight,dx,color,name in [('job_count',-.18,BLUE,'Submission counts: 80/80'),('resource_gpu_h',.18,ORANGE,'Task resource-time: 31/80')]:
        w=week[(week.weight==weight)&(week.ordering=='chronological')&(week.fraction==.5)].sort_values('week');ax[3].bar(w.week+dx,w.successes_zero,.33,color=color,label=name)
    ax[3].set_ylim(0,14);ax[3].set_yticks([0,2,4,6,8,10]);ax[3].set_xticks(range(8),range(1,9));ax[3].set_xlabel('Observed week');ax[3].set_ylabel('Successes at the same 2.95 kW');ax[3].legend(loc='upper left',frameon=False,fontsize=6.2)
    label(ax[3],'d','Resource-time weights change transfer')
    fig.subplots_adjust(left=.115,right=.98,top=.925,bottom=.125,wspace=.56,hspace=.95)
    save(fig,a.output/'AIDRBench_Figure_3','10% eligible work; corrected causal control; four calls. a: 300 new independent scenarios per product.\nb: prespecified mechanism cases, not a prevalence estimate. c,d: eight observed weeks × ten synthetic realisations.\nc: both service scores coincide. d: zero-miss score; all baselines feasible; all 49 resource-time failures have supply shortage.')
    exposure=read('physical_operating_exposure.csv');components=read('ready_operating_components.csv');cost=read('refinement_economic_sensitivity.csv');curves=read('ready_refinement_price_curves.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.7));ax=axes.ravel();progs=['H4P16','H8P16'];names=['Four hours\n5.60 kW','Eight hours\n4.42 kW']
    e=exposure[exposure.offerable_zero&(exposure.metric=='delay_exposure_gpu_h_h')].set_index('program').loc[progs]
    mean=e.model_series_mean.to_numpy()/1000;low=e.model_series_p05.to_numpy()/1000;high=e.model_series_p95.to_numpy()/1000
    ax[0].errorbar([0,1],mean,yerr=[mean-low,high-mean],fmt='o',color=BLUE,capsize=4,ms=6);ax[0].set_xticks([0,1],names);ax[0].set_xlim(-.5,1.5);ax[0].set_ylim(0,35);ax[0].set_ylabel('Additional waiting per series\n(1,000 GPU-h × h)');label(ax[0],'a','Measure exposure before pricing')
    positive=np.zeros(2);negative=np.zeros(2)
    for component,color in [('Waiting',TEAL),('Electricity',GRAY),('Delivery credit',BLUE)]:
        c=components[components.component==component].set_index('program').loc[progs];v=c.value_per_kw.to_numpy();ax[1].bar([0,1],v,bottom=np.where(v>0,positive,negative),color=color,label=component,width=.55);positive+=np.maximum(v,0);negative+=np.minimum(v,0)
    net=components.drop_duplicates('program').set_index('program').loc[progs].total_per_kw;ax[1].plot([0,1],net,'D',color=DARK,ms=4,label='Net operating threshold');ax[1].axhline(0,color=DARK,lw=.6);ax[1].set_xticks([0,1],names);ax[1].set_ylim(-55,455);ax[1].set_ylabel('USD per offered kW-year');ax[1].legend(loc='upper left',fontsize=6.1,frameon=False);label(ax[1],'b','Waiting dominates the priced costs')
    for p,color,name in [('H4P16',BLUE,'Four hours'),('H8P16',ORANGE,'Eight hours')]:
        c=cost[cost.offerable_zero&(cost.program==p)&(cost.missed_work_price==0)&(cost.site_fee_annual_usd==0)].sort_values('waiting_price');ax[2].plot(c.waiting_price,c.payment_per_kw,'o-',color=color,ms=4,label=name)
    ax[2].set_xlabel('Waiting price (USD / GPU-h / h)');ax[2].set_xticks([0,.005,.01],['0','0.005','0.010']);ax[2].set_ylabel('Threshold (USD per offered kW-year)');ax[2].legend(frameon=False);label(ax[2],'c','The valuation changes the threshold')
    for price,color in [(0,GRAY),(.005,BLUE),(.01,ORANGE)]:
        c=curves[(curves.waiting_price==price)&(curves.price_4h<=750)].sort_values('price_4h');ax[3].plot(c.price_4h,c.required_price_8h,color=color,label=f'Waiting price {price:g}')
    ax[3].plot([0,750],[0,750],color=DARK,ls=':',lw=.8,label='Equal capacity prices');ax[3].set_xlim(0,750);ax[3].set_ylim(-30,1300);ax[3].set_xlabel('Four-hour price (USD / kW-year)');ax[3].set_ylabel('Required eight-hour price\n(USD / kW-year)');ax[3].legend(loc='upper left',fontsize=6.1,frameon=False);label(ax[3],'d','Price boundary includes opting out')
    fig.subplots_adjust(left=.13,right=.98,top=.91,bottom=.15,wspace=.55,hspace=.75)
    save(fig,a.output/'AIDRBench_Figure_6','Reference workload; zero-loss-qualified duration products; 16-h start spacing. a: mean and scenario p05–p95, n = 300.\nb–d: 1-MW proportional accounting; 12 independent four-call series/year; 2,000 annual draws; all failures retained.\nNo fixed fee. Electricity USD 0.10/kWh; delivered-energy revenue USD 50/MWh; missed-work price zero. Conditional prices.')
    dev=read('refinement_development_summary.csv');oldsummary=read('confirmation_summary.csv',True);target=read('target_call_pairs.csv',True)
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.9));ax=axes.ravel()
    for i,p in enumerate(progs):
        for endpoint,color,marker,name in [('success_1pct',BLUE,'o','At most 1%'),('success_zero',TEAL,'s','Zero loss')]:
            g=dev[(dev.program==p)&(dev.endpoint==endpoint)].sort_values('capacity_kw');ax[i].plot(g.capacity_kw,g.wilson_lower,marker=marker,ms=4,color=color,label=name)
        ax[i].axhline(.95,color=GRAY,ls='--',lw=.8);ax[i].set_ylim(.83,1);ax[i].set_ylabel('Development Wilson lower bound');ax[i].set_xlabel('Tested request (kW)');ax[i].legend(frameon=False,loc='lower left');label(ax[i],'ab'[i],['Four-hour local candidate grid','Eight-hour local candidate grid'][i])
    g=oldsummary[(oldsummary.program=='H8P16')&(oldsummary.kind=='repeated')&(oldsummary.fraction==1)&(oldsummary.endpoint=='success_1pct')].set_index('variant').loc[BASE];x=np.arange(6)
    ax[2].bar(x-.17,g.instantaneous_supply_limited_trials/3,.31,color=GRAY,label='Immediate shortage');ax[2].bar(x+.17,g.failed_deadline_miss/3,.31,color=ORANGE,label='More than 1% missed');ax[2].set_xticks(x,['50 / ref','50 / tight','65 / ref','65 / tight','80 / ref','80 / tight'],rotation=35,ha='right',rotation_mode='anchor');ax[2].set_ylim(0,132);ax[2].set_yticks([0,25,50,75,100]);ax[2].set_ylabel('Scenarios affected (%)');ax[2].legend(frameon=False,fontsize=6.2,loc='upper left');label(ax[2],'c','Broader structural context')
    g=target[(target.program=='H8P16')&target.variant.isin(BASE)].set_index('variant').loc[BASE]
    for col,color,marker,name in [('fresh_target_electrical_successes',GRAY,'o','Last call only'),('repeated_target_electrical_successes',BLUE,'x','With three earlier calls')]:ax[3].plot(x,g[col],marker,ms=6,color=color,label=name)
    ax[3].set_xticks(x,['50 / ref','50 / tight','65 / ref','65 / tight','80 / ref','80 / tight'],rotation=35,ha='right',rotation_mode='anchor');ax[3].set_ylim(200,317);ax[3].set_ylabel('Successful final calls (out of 300)');ax[3].legend(frameon=False,fontsize=6.2,loc='lower right');label(ax[3],'d','Matched last-call outcomes coincide')
    fig.subplots_adjust(left=.125,right=.98,top=.91,bottom=.18,wspace=.5,hspace=.7)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_3','a,b: 100 independent new development seeds per candidate; finite grid; no interpolation-based selection.\nc,d: earlier structural confirmation, 300 paired scenarios; 10% eligible work, full 5.90-kW request, 16-h start spacing.\nTight deadlines halve slack. c: categories may overlap. d: final-call electrical criteria exclude episode-wide service quantities.')
    values=read('ready_annual_values.csv');front=read('refinement_price_frontier.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.7));ax=axes.ravel()
    for wait,color in [(0,BLUE)]:
        g=values[(values.waiting_price==wait)&(values.fee==0)].sort_values('price');ax[0].plot(g.price,g.difference,color=color,label='Waiting price zero')
    ax[0].axhline(0,color=DARK,lw=.7);ax[0].set_xlim(0,75);ax[0].set_ylim(-330,220);ax[0].set_xlabel('Equal capacity price (USD / kW-year)');ax[0].set_ylabel('Annual value: eight minus four hours (USD)');ax[0].legend(frameon=False,fontsize=6.2);ax[0].annotate('Equal value: USD 25.57',xy=(25.571384,0),xytext=(30,80),fontsize=6.5,arrowprops={'arrowstyle':'-','color':GRAY,'lw':.6});label(ax[0],'a','Free waiting permits a rank reversal')
    for j,(loss,color) in enumerate([(0,BLUE),(1,ORANGE)]):
        c=cost[cost.offerable_zero&(cost.waiting_price==.005)&(cost.site_fee_annual_usd==0)&(cost.missed_work_price==loss)].set_index('program').loc[progs];ax[1].bar(np.arange(2)+(j-.5)*.3,c.payment_per_kw,.28,color=color,label=f'Missed work USD {loss}/GPU-h')
    ax[1].set_xticks([0,1],names);ax[1].set_ylim(0,450);ax[1].set_ylabel('Threshold (USD per offered kW-year)');ax[1].legend(frameon=False,fontsize=6.1);label(ax[1],'b','Price every failed trajectory')
    fees=[0,2500,25000];v=values[(values.waiting_price==.005)&(values.price==250)&values.fee.isin(fees)].set_index('fee').loc[fees]
    ax[2].bar(np.arange(3)-.16,v.net4/1000,.29,color=BLUE,label='Four hours');ax[2].bar(np.arange(3)+.16,v.net8/1000,.29,color=ORANGE,label='Eight hours');ax[2].axhline(0,color=DARK,lw=.7);ax[2].set_xticks(range(3),['No fee','Shared\nUSD 2,500','Full\nUSD 25,000']);ax[2].set_ylabel('Annual net-value q05 (1,000 USD)');ax[2].legend(frameon=False,fontsize=6.2,loc='lower left');label(ax[2],'c','Fees change whether to participate')
    for fee,color in zip(fees,[TEAL,BLUE,GRAY]):
        row=front[(front.endpoint=='zero')&(front.waiting_price==.005)&(front.missed_work_price==0)&(front.site_fee_annual_usd==fee)].iloc[0]
        x=np.unique(np.r_[np.arange(0,1501,5),row.four_hour_entry]);y=np.maximum(row.nonparticipation_floor,row.slope*x+row.intercept);ax[3].plot(x,y,color=color,label=f'Fee USD {fee:,}')
    ax[3].set_xlim(0,1500);ax[3].set_xlabel('Four-hour price (USD / kW-year)');ax[3].set_ylabel('Required eight-hour price\n(USD / kW-year)');ax[3].legend(frameon=False,fontsize=6.2);label(ax[3],'d','Entry floors shift with shared fees')
    fig.subplots_adjust(left=.135,right=.98,top=.91,bottom=.15,wspace=.58,hspace=.76)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_5','Refined zero-loss products; same reference workload and annual accounting as Figure 6. All 300 trajectories retained.\na: positive values favour eight hours; b–d: waiting USD 0.005/GPU-h/h; c: equal capacity prices USD 250/kW-year.\nShared access fees do not pool reliability. These are stated-price accounting scenarios, not measured participation.')
    outputs={}
    for prefix,n in [('AIDRBench_Figure_',3),('AIDRBench_Figure_',6),('AIDRBench_Supplementary_Figure_',3),('AIDRBench_Supplementary_Figure_',5)]:
        for ext in ['pdf','svg','png','tiff']:
            path=a.output/f'{prefix}{n}.{ext}';outputs[path.name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    (a.output/'mechanism_manifest.json').write_text(json.dumps(dict(version='0.24',source_tables=used,outputs=outputs),indent=2)+'\n')
if __name__=='__main__':main()
