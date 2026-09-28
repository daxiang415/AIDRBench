"""v0.26: restore appropriate operating and sensitivity displays from ready CSVs."""
import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/aidrbench-completeness-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

BLUE = '#235A78'
TEAL = '#269383'
ORANGE = '#B27640'
GRAY = '#85929B'
DARK = '#293740'
CASES = ['f05','f10','f20','f40','f60']
SHARES = np.array([5,10,20,40,60])
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],
    'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,
    'ytick.labelsize':7,'legend.fontsize':6.5,'legend.frameon':False,
    'text.parse_math':False,'svg.fonttype':'none','pdf.fonttype':42,
    'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,
    'savefig.facecolor':'white'})


def label(ax, letter, title):
    ax.set_title(title, loc='left', pad=15)
    ax.annotate(letter, xy=(0,1.07), xycoords='axes fraction', xytext=(-23,0),
                textcoords='offset points', fontsize=11, fontweight='bold')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    used, outputs = {}, {}

    def read(name):
        p = args.data / name
        used[name] = hashlib.sha256(p.read_bytes()).hexdigest()
        return json.loads(p.read_text()) if p.suffix == '.json' else pd.read_csv(p)

    def save(fig, name, foot):
        fig.text(.035,.025,foot,fontsize=6.2,va='bottom',linespacing=1.5)
        stem = args.output / f'AIDRBench_{name}'
        fig.savefig(stem.with_suffix('.pdf'))
        fig.savefig(stem.with_suffix('.svg'))
        fig.savefig(stem.with_suffix('.png'), dpi=300)
        fig.savefig(stem.with_suffix('.tiff'), dpi=600, pil_kwargs={'compression':'tiff_lzw'})
        for ext in ['pdf','svg','png','tiff']:
            p = args.output / f'AIDRBench_{name}.{ext}'
            outputs[p.name] = dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
        plt.close(fig)

    audit, definitions = read('source_audit.json'), read('case_definitions.json')
    steps = read('decision_steps.csv')
    fig = plt.figure(figsize=(7.205,6.75))
    grid = fig.add_gridspec(2,2,height_ratios=[1,1.35],hspace=.7,wspace=.65)
    a,b,flow = fig.add_subplot(grid[0,0]),fig.add_subplot(grid[0,1]),fig.add_subplot(grid[1,:])
    names = ['online_inference','offline_inference','training','dev','other','unknown']
    display = ['Online inference','Offline inference','Training','Development','Other','Unknown']
    values = [100*audit['shares'][c] for c in names]
    a.barh(display[::-1],values[::-1],color=[ORANGE,TEAL,BLUE,GRAY,GRAY,GRAY][::-1],height=.65)
    for y,v in enumerate(values[::-1]): a.text(v+.7,y,f'{v:.2f}',va='center',fontsize=7)
    a.set_xlim(0,68);a.set_xlabel('Requested GPU-hours (%)')
    label(a,'a','Observed workload composition')
    train=np.array([c['eligible_shares']['training']*100 for c in definitions])
    offline=np.array([c['eligible_shares']['offline_inference']*100 for c in definitions])
    b.bar(range(5),train,color=BLUE,label='Training',width=.65)
    b.bar(range(5),offline,bottom=train,color=TEAL,label='Offline inference',width=.65)
    b.set_xticks(range(5),['5','10','20','40*','60†']);b.set_xlabel('Work eligible for deferral (%)')
    b.set_ylim(0,73);b.set_yticks([0,20,40,60]);b.set_ylabel('Eligible share of all work (%)')
    b.legend(loc='upper left');b.axvline(2.5,color=GRAY,ls=':',lw=.8)
    label(b,'b','Declared operating permissions')
    flow.set_axis_off();flow.set_xlim(0,1);flow.set_ylim(0,1)
    label(flow,'c','From workload evidence to a commitment decision')
    for i,(title,detail,decision) in enumerate(steps[['step','criterion','decision']].itertuples(index=False,name=None)):
        y=.91-i*.235
        flow.add_patch(FancyBboxPatch((.012,y-.11),.545,.15,
            boxstyle='round,pad=0.012,rounding_size=0.012',edgecolor=BLUE,facecolor='#F3F7F8',linewidth=.75))
        flow.text(.027,y+.006,title,fontsize=7.2,va='center',fontweight='bold',color=DARK)
        flow.text(.027,y-.065,detail,fontsize=6.2,va='center',color=DARK)
        flow.annotate('',xy=(.61,y-.035),xytext=(.575,y-.035),arrowprops={'arrowstyle':'->','color':GRAY,'lw':.8})
        flow.text(.623,y-.035,decision,fontsize=6.4,va='center',linespacing=1.35,color=DARK)
        if i<3: flow.annotate('',xy=(.28,y-.19),xytext=(.28,y-.127),arrowprops={'arrowstyle':'->','color':BLUE,'lw':.8})
    fig.subplots_adjust(left=.18,right=.98,top=.92,bottom=.13)
    save(fig,'Figure_1','a: descriptive source totals, not energy shares or an industry estimate. b: online jobs are never deferred.\n* Nearly all batch work opts in. † Business composition changes. c: scenario feasibility and contract reliability differ.')

    pairs,example = read('paired_resource_supply_margins.csv'),read('supply_hourly_example.csv')
    trace = read('reference_operation_example.csv')
    fig,axes = plt.subplots(2,2,figsize=(7.205,6.85));a,b,c,d=axes.ravel()
    a.scatter(pairs.chronological,pairs.permuted,color=BLUE,s=21,alpha=.7,edgecolor='white',linewidth=.35)
    a.axvline(0,color=GRAY,ls='--',lw=.8);a.axhline(0,color=GRAY,ls='--',lw=.8)
    a.set_xlim(-1.3,1.5);a.set_ylim(-1.75,3.2);a.set_xticks([-1,0,1])
    a.set_xlabel('Original minimum margin (kW)');a.set_ylabel('Permuted minimum margin (kW)')
    for xy,mask,align in [((-.08,3.03),(pairs.chronological<0)&(pairs.permuted>=0),'right'),((.08,3.03),(pairs.chronological>=0)&(pairs.permuted>=0),'left'),((-.08,-1.6),(pairs.chronological<0)&(pairs.permuted<0),'right'),((.08,-1.6),(pairs.chronological>=0)&(pairs.permuted<0),'left')]:
        a.text(*xy,f'{int(mask.sum())} cases',fontsize=6.3,ha=align)
    label(a,'a','Hourly order changes supply margins')
    for weight,color,name in [('job_count',BLUE,'Submission counts'),('resource_gpu_h',ORANGE,'Task resource-time')]:
        e=example[(example.weight==weight)&(example.ordering=='chronological')&(example.hour<168)].sort_values('hour')
        b.step(e.hour,e.available_reduction_kw,where='post',color=color,lw=.85,label=name)
    b.axhline(.95*e.request_kw.iloc[0],color=DARK,ls='--',lw=.8,label='Required delivery (95%)')
    for _,g in e[e.event_active].groupby('event_id'):b.axvspan(g.hour.min(),g.hour.max()+1,color=GRAY,alpha=.16,lw=0)
    b.set_xlim(0,168);b.set_ylim(-.8,27);b.set_xticks([0,48,96,144]);b.set_yticks([0,5,10,15,20])
    b.set_xlabel('Hour');b.set_ylabel('Available baseline reduction (kW)');b.legend(loc='upper left',fontsize=6.1)
    label(b,'b','Supply troughs can rule out delivery')
    for program,color,name in [('H4P16',BLUE,'4 h: 5.60 kW'),('H8P16',TEAL,'8 h: 4.42 kW')]:
        t=trace[trace.program==program].sort_values('hour')
        c.step(t.hour,-t.incremental_power_kw,where='post',color=color,lw=.95,label=name)
        c.step(t.hour,t.requested_reduction_kw,where='post',color=color,lw=.7,ls=':')
        d.step(t.hour,t.excess_backlog_gpu_h,where='post',color=color,lw=1,label=name)
    for ax in [c,d]:
        ax.axhline(0,color=GRAY,lw=.6);ax.axvspan(168,216,color=GRAY,alpha=.10,lw=0)
        ax.set_xlim(0,216);ax.set_xticks([0,48,96,144,192]);ax.set_xlabel('Hour');ax.legend(loc='upper left',fontsize=6.3)
    c.set_ylim(-21.5,8)
    c.legend(loc='upper right',fontsize=6.3)
    c.set_ylabel('Baseline minus response power (kW)');d.set_ylabel('Additional backlog (GPU-h)')
    label(c,'c','Response is followed by recovery');label(d,'d','Deferred work is subsequently cleared')
    fig.subplots_adjust(left=.115,right=.98,top=.93,bottom=.15,wspace=.55,hspace=.66)
    save(fig,'Figure_4','a: all 80 matched resource-time realisations at 2.95 kW. b: lowest workload-test seed, 990000; calls shaded.\nc,d: lowest confirmation seed, 989000, at independently qualified reference offers; illustrative, not a reliability estimate.\nc: dotted lines are requests; negative values are recovery power. Grey tail (168–216 h) allows workload clearance.')

    structural=read('structural_full_request.csv')
    variants=['u50d100g10','u50d50g10','u65d100g10','u65d50g10','u65d50g20','u80d100g10','u80d50g10','u80d50g20']
    rowlabels=['50 / 1× / 10','50 / ½× / 10','65 / 1× / 10','65 / ½× / 10','65 / ½× / 20','80 / 1× / 10','80 / ½× / 10','80 / ½× / 20']
    columns=[('fresh','H8P16'),('repeated','H8P16'),('repeated','H8P24')]
    fig,axes=plt.subplots(2,2,figsize=(7.205,7.1))
    for ax,letter,endpoint,metric,title,cmap in zip(axes.ravel(),'abcd',
        ['success_1pct','success_zero','success_1pct','success_1pct'],
        ['successes','successes','instantaneous_supply_limited_trials','failed_deadline_miss'],
        ['Joint success: ≤1% missed work','Joint success: zero missed work','Immediate supply shortage','More than 1% missed work'],
        ['Blues','Blues','Oranges','Oranges']):
        frame=structural[structural.endpoint==endpoint].set_index(['variant','kind','program'])
        matrix=np.array([[frame.loc[(v,k,p),metric] for k,p in columns] for v in variants])
        im=ax.imshow(matrix,vmin=0,vmax=300,cmap=cmap,aspect='auto',interpolation='none')
        for (i,j),val in np.ndenumerate(matrix):ax.text(j,i,str(int(val)),ha='center',va='center',fontsize=7,color='white' if val>190 else DARK)
        ax.set_xticks(range(3),['Fresh\nlast call','Four calls\n16-h starts','Four calls\n24-h starts'],fontsize=6.7)
        ax.set_yticks(range(8),rowlabels,fontsize=6.8);ax.tick_params(length=0)
        ax.set_ylabel('Utilisation (%) / deadline / GPU share (%)',fontsize=7)
        for spine in ax.spines.values():spine.set_visible(False)
        label(ax,letter,title)
    fig.subplots_adjust(left=.20,right=.98,top=.92,bottom=.14,wspace=.8,hspace=.54)
    save(fig,'Supplementary_Figure_6','Each cell: count out of 300 independent frozen confirmation scenarios; full 5.90-kW stress request, 8-h events.\n10% eligible work. Deadline multipliers apply to the reference slack. All no-response baselines pass service checks.\nFailure categories overlap. Changing start spacing also moves earlier calls; this is not a pure interval-effect experiment.')

    pv=read('pv_operating_summary.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.2));a,b,c,d=axes.ravel()
    for ax,bess in [(a,False),(b,True)]:
        for operation,color,marker,name in [('rigid',GRAY,'o','Rigid'),('flexible',TEAL,'s','Flexible')]:
            g=pv[(pv.analysis=='pv_hosting')&(pv.bess_enabled==bess)&(pv.dc_operation==operation)&(pv.metric=='pv_rated_kw')].set_index('case').loc[CASES]
            ax.plot(SHARES,g.minimum,marker=marker,ms=4,lw=1,color=color,label=name)
        ax.set_ylabel('PV hosting capacity (kW)');ax.legend(loc='upper left')
    for ax,metric,ylabel in [(c,'total_pv_curtailed_kwh','Mean curtailed PV energy (kWh)'),(d,'total_grid_import_kwh','Mean grid import (MWh)')]:
        for bess,color in [(False,BLUE),(True,TEAL)]:
            for operation,marker,style in [('rigid','o','--'),('flexible','s','-')]:
                g=pv[(pv.analysis=='fixed_pv_operation')&(pv.bess_enabled==bess)&(pv.dc_operation==operation)&(pv.metric==metric)].set_index('case').loc[CASES]
                divisor=1000 if metric=='total_grid_import_kwh' else 1
                ax.plot(SHARES,g['mean']/divisor,marker=marker,ms=3.5,lw=.9,ls=style,color=color,label=f'{operation.title()}, '+('BESS' if bess else 'no BESS'))
        ax.set_ylabel(ylabel)
    c.set_ylim(-.7,20)
    c.legend(loc='upper left',fontsize=6.1,ncol=2,columnspacing=.8)
    d.text(.97,.90,'Curves nearly coincide',transform=d.transAxes,ha='right',fontsize=6.5,color=DARK)
    for ax,letter,title in zip(axes.ravel(),'abcd',['Hosting without storage','Hosting with storage','Fixed 500-kW PV: curtailment','Fixed 500-kW PV: grid supply']):
        ax.set_xticks(SHARES,['5','10','20','40*','60†']);ax.set_xlabel('Eligible work (%)');label(ax,letter,title)
    fig.subplots_adjust(left=.12,right=.98,top=.91,bottom=.16,wspace=.48,hspace=.65)
    save(fig,'Supplementary_Figure_7','a,b: minimum hosting over 100 scenarios per cell. c,d: arithmetic means over the same 100 paired scenarios.\nFull-information PV planning with zero missed work; these are not causal-controller guarantees or confidence bounds.\n* Nearly all batch work opts in. † Business composition changes. Small storage effects may be below solver resolution.')

    life=read('reserve_life_sensitivity.csv');econ=read('economic_price_sensitivity.csv')
    fig,axes=plt.subplots(2,2,figsize=(7.205,6.0))
    configs=[('economic_life_years','Hardware economic life (years)','Reserved hardware amortisation'),
             ('effective_displaced_value_usd_gpu_h','Displaced-work value (US$/GPU-h)','Opportunity cost of displaced work'),
             ('delay_price','Waiting price (10⁻³ US$/GPU-h/h)','Valuation of additional waiting'),
             ('fixed_site_cost','Annual site fee (thousand US$)','Fixed participation fees')]
    for i,(ax,(field,xlabel,title)) in enumerate(zip(axes.ravel(),configs)):
        if i==0:g=life.copy()
        elif i==1:g=econ[(econ.delay_price==.005)&(econ.fixed_site_cost==25000)&(econ.missed_work_price==0)]
        elif i==2:g=econ[(econ.effective_displaced_value_usd_gpu_h==0)&(econ.fixed_site_cost==25000)&(econ.missed_work_price==0)]
        else:g=econ[(econ.delay_price==.005)&(econ.effective_displaced_value_usd_gpu_h==0)&(econ.missed_work_price==0)]
        for duration,color,marker in [(4,BLUE,'o'),(8,TEAL,'s')]:
            z=g[g.duration_h==duration].sort_values(field)
            assert z[field].is_unique and z.qualified.all()
            x=z[field]/1000 if field=='fixed_site_cost' else z[field]*1000 if field=='delay_price' else z[field]
            ax.plot(x,z.risk_adjusted_capacity_payment_usd_kw_year,color=color,marker=marker,ms=4,lw=1,label=f'{duration} h')
            ax.set_xticks(x)
        ax.set_xlabel(xlabel);ax.set_ylabel('Threshold (US$/offered kW/year)');ax.set_ylim(bottom=0)
        label(ax,'abcd'[i],title)
    axes[0,0].legend(loc='lower left')
    fig.subplots_adjust(left=.13,right=.98,top=.91,bottom=.16,wspace=.52,hspace=.65)
    save(fig,'Supplementary_Figure_8','10% eligible work; qualified single-event offers, 5.90 kW; 50 independent calls/year; proportional 1-MW accounting.\na: reserved headroom. b–d: one monetary factor at a time, without added reserve cost; other inputs at their stated reference.\nPoints are 95th-percentile annual-cost thresholds, not confidence bounds. These products differ from Fig. 6 repeated calls.')
    (args.output/'completeness_manifest.json').write_text(json.dumps(dict(version='0.26',source_tables=used,outputs=outputs),indent=2)+'\n')


if __name__=='__main__':
    main()
