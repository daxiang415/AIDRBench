"""Draw four replacement figures from delivered ready tables; no fitting or statistics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/aidrbench-tradeoff-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'text.parse_math':False,
 'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,
 'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white'})
BLUE='#235A78';TEAL='#269383';ORANGE='#B27640';GRAY='#85929B';DARK='#293740'
BASE=[f'u{u}d{d}g10' for u in [50,65,80] for d in [100,50]]
ALL=BASE+['u65d50g20','u80d50g20']
LABELS=['50 / ref.','50 / tight','65 / ref.','65 / tight','80 / ref.','80 / tight']

def label(ax,letter,title):
    ax.set_title(title,loc='left',pad=13)
    ax.annotate(letter,xy=(0,1.075),xycoords='axes fraction',xytext=(-22,0),textcoords='offset points',fontsize=11,fontweight='bold')

def save(fig,path,foot):
    fig.text(.04,.02,foot,fontsize=6.3,ha='left',va='bottom',linespacing=1.5)
    fig.savefig(path.with_suffix('.pdf'))
    fig.savefig(path.with_suffix('.svg'))
    fig.savefig(path.with_suffix('.png'),dpi=300)
    fig.savefig(path.with_suffix('.tiff'),dpi=600)
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--previous-data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);used={}
    def read(name,old=False):
        path=(a.previous_data if old else a.data)/name;used[('previous/' if old else 'tradeoffs/')+name]=hashlib.sha256(path.read_bytes()).hexdigest();return pd.read_csv(path)
    selected=read('selected_offers_confirmed.csv');summary=read('confirmation_summary.csv');week=read('temporal_week_summary.csv')
    fig=plt.figure(figsize=(7.205,6.5));gs=fig.add_gridspec(2,2,height_ratios=[1.08,1]);ax=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])]
    x=np.arange(6)
    for endpoint,shift,color,name in [('success_1pct',-.16,BLUE,'At most 1% missed work'),('success_zero',.16,TEAL,'Zero missed work')]:
        z=selected[(selected.program=='H8P16')&(selected.endpoint==endpoint)].set_index('variant').loc[BASE]
        for i,r in enumerate(z.itertuples()):
            if pd.isna(r.selected_capacity_kw):ax[0].text(i+shift,.18,'NS',ha='center',fontsize=6.5,color=color,rotation=90)
            else:ax[0].bar(i+shift,r.selected_capacity_kw,.29,color=color)
        ax[0].bar([],[],color=color,label=name)
    ax[0].set_ylim(0,6.5);ax[0].set_ylabel('Selected, confirmed offer (kW)');ax[0].set_xticks(x,LABELS,rotation=40,ha='right')
    ax[0].set_xlabel('Offered utilisation (%) / deadline setting');ax[0].legend(handles=[Patch(color=BLUE,label='At most 1% missed work'),Patch(color=TEAL,label='Zero missed work')],loc='upper left',bbox_to_anchor=(0,1.01),fontsize=6.4,frameon=False)
    label(ax[0],'a','The service standard changes the offer')
    z=summary[(summary.program=='H8P16')&(summary.kind=='repeated')&(summary.fraction==1)&(summary.endpoint=='success_1pct')].set_index('variant').loc[BASE]
    ax[1].bar(x-.16,z.instantaneous_supply_limited_trials/z.trials*100,.30,color=GRAY,label='Insufficient immediate power')
    ax[1].bar(x+.16,z.failed_deadline_miss/z.trials*100,.30,color=ORANGE,label='More than 1% missed work')
    ax[1].set_ylabel('Scenarios affected (%)');ax[1].set_ylim(0,121);ax[1].set_yticks([0,25,50,75,100]);ax[1].set_xticks(x,LABELS,rotation=40,ha='right')
    ax[1].set_xlabel('Offered utilisation (%) / deadline setting');ax[1].legend(loc='upper left',fontsize=6.4,frameon=False)
    label(ax[1],'b','Different limits at the same request')
    for ordering,offset,color,name in [('chronological',-.17,BLUE,'Observed order: 63/80'),('permuted',.17,ORANGE,'Permuted hours: 76/80')]:
        w=week[(week.ordering==ordering)&(week.gpu_allocation_pct==10)&(week.program=='H8P16')&(week.fraction==.75)].sort_values('week')
        ax[2].bar(w.week+offset,w.successes_1pct,.31,color=color,label='4.42 kW, '+name)
    ax[2].plot(np.arange(8),np.repeat(10,8),'D',ms=4,color=TEAL,label='2.95 kW, zero misses: 80/80 in each order')
    ax[2].set_ylim(0,15.5);ax[2].set_yticks([0,2,4,6,8,10]);ax[2].set_xticks(range(8),[str(i+1) for i in range(8)])
    ax[2].set_xlabel('Observed production week');ax[2].set_ylabel('Successful realisations\n(out of 10 per week)');ax[2].legend(loc='upper left',fontsize=6.8,ncol=1,frameon=False)
    label(ax[2],'c','Transfer depends on request and production timing')
    fig.subplots_adjust(left=.12,right=.98,top=.91,bottom=.17,wspace=.5,hspace=.95)
    save(fig,a.output/'AIDRBench_Figure_3','10% eligible work; four 8-h calls, 16-h start spacing (8-h gaps); MPC with all recovery windows.\na,b: n = 300 independent scenarios per condition. NS: no development candidate selected, not zero capacity.\nc: eight observed weeks × ten synthetic realisations; aggregate counts are descriptive. Tight deadlines halve slack.')

    comp=read('cost_components.csv');cost=read('structural_economic_primary.csv');front=read('ready_duration_price_curves.csv')
    fig,axs=plt.subplots(2,2,figsize=(7.205,6.25));aa=axs.ravel()
    c=comp[(comp.kind=='single')&(comp.program=='H4')].set_index('case').loc[['f05','f10','f20','f40','f60']]
    aa[0].bar(range(5),c.net_operating_cost_per_kw_q95,color=TEAL,label='Net operating exposure')
    aa[0].bar(range(5),c.fixed_fee_per_kw,bottom=c.net_operating_cost_per_kw_q95,color=GRAY,label='Fixed site fee')
    aa[0].set_xticks(range(5),['5','10','20','40*','60†']);aa[0].set_xlabel('Work eligible for deferral (%)');aa[0].set_ylabel('Payment (US$/kW-year)');aa[0].set_ylim(0,2050)
    aa[0].legend(frameon=False,fontsize=6.8);aa[0].text(1,910,'95% fixed',ha='center',fontsize=6.5,color=DARK);label(aa[0],'a','Fixed fees dominate the original screen')
    specs=[('H4P16',.75,BLUE,'4 h, 16-h spacing'),('H8P16',.5,TEAL,'8 h, 16-h spacing'),('H8P24',.5,ORANGE,'8 h, 24-h spacing')]
    for i,(prog,f,color,name) in enumerate(specs):
        z=cost[(cost.variant=='u65d100g10')&(cost.program==prog)&(cost.fraction==f)&cost.offerable_success_zero].sort_values('site_fee_annual_usd')
        # Primary contains zero and reference fees; sensitivities contain the full grid.
        sens=read('structural_economic_sensitivity.csv') if i==0 else sens
        z=sens[(sens.variant=='u65d100g10')&(sens.program==prog)&(sens.fraction==f)&(sens.waiting_price==.005)&(sens.missed_work_price==0)].sort_values('site_fee_annual_usd')
        aa[1].plot(z.site_fee_annual_usd/1000,z.payment_per_kw,'o-',color=color,ms=3,label=name)
    aa[1].set_xlabel('Annual site fee (US$ thousand)');aa[1].set_ylabel('Payment (US$/kW-year)');aa[1].legend(frameon=False,fontsize=6.4);label(aa[1],'b','Shared fees lower entry thresholds')
    for i,(prog,f,color,name) in enumerate(specs):
        z=cost[(cost.variant=='u65d100g10')&(cost.program==prog)&(cost.fraction==f)&(cost.site_fee_annual_usd==0)].iloc[0]
        aa[2].bar(i,z.payment_per_kw,color=color);aa[2].text(i,z.payment_per_kw+10,f'{z.payment_per_kw:.0f}',ha='center',fontsize=7)
    aa[2].set_xticks(range(3),['4 h / 16 h','8 h / 16 h','8 h / 24 h']);aa[2].set_xlabel('Call duration / start spacing');aa[2].set_ylabel('Payment (US$/kW-year)');aa[2].set_ylim(0,480);label(aa[2],'c','Operating costs remain with no site fee')
    for endpoint,color,name in [('success_1pct',BLUE,'1%: 4.42 vs 4.42 kW'),('success_zero',TEAL,'Zero: 2.95 vs 4.42 kW')]:
        z=front[(front.endpoint==endpoint)&(front.long_program=='H8P16')&(front.site_fee_annual_usd==0)].sort_values('short_price')
        aa[3].plot(z.short_price,z.required_long_price_vs_short_and_opt_out,color=color,lw=1.6,label=name)
    aa[3].plot([0,2000],[0,2000],color=GRAY,ls=':',lw=.8,label='Equal price per kW')
    aa[3].set_xlabel('4-h capacity price (US$/kW-year)');aa[3].set_ylabel('Minimum 8-h price\n(US$/kW-year)');aa[3].legend(loc='upper left',fontsize=6.2,frameon=False);label(aa[3],'d','Longer service needs a different tariff')
    fig.subplots_adjust(left=.12,right=.98,top=.90,bottom=.19,wspace=.48,hspace=.72)
    save(fig,a.output/'AIDRBench_Figure_6','a: 50 independent single calls/year; US$25,000/year fixed fee. * Broad batch opt-in. † Changed business mix.\nb–d: 10% eligibility, 65% offered utilisation, reference deadlines; 12 independent four-call series/year.\nb,c: zero-miss selected offers. d: minimum price to beat both the 4-h choice and opting out; site fee zero.\nAll panels: proportional 1-MW accounting, waiting US$0.005/GPU-h/h; conditional costs, not observed profits.')

    old=read('confirmation_summary.csv',True);target=read('target_call_pairs.csv')
    fig=plt.figure(figsize=(7.205,7.3));gs=fig.add_gridspec(3,2,height_ratios=[1,1,1.35]);a0=fig.add_subplot(gs[0,0]);a1=fig.add_subplot(gs[0,1]);a2=fig.add_subplot(gs[1:,:])
    for j,(ctrl,col,name) in enumerate([('original',GRAY,'Original MPC'),('all_window_mpc',TEAL,'Corrected MPC'),('all_window_greedy',ORANGE,'Corrected greedy')]):
        cases=['f10'] if ctrl=='all_window_greedy' else ['f05','f10','f20','f40','f60']
        positions=np.array([['f05','f10','f20','f40','f60'].index(c) for c in cases])
        z=old[(old.program=='H8G12')&(old.controller==ctrl)&(old.fraction==1)].set_index('case').loc[cases]
        y=z.success_fraction.to_numpy()*100;lo=z.wilson_lower.to_numpy()*100
        a0.errorbar(positions+(j-1)*.12,y,yerr=[y-lo,np.zeros(len(z))],fmt='os^'[j],ms=3,capsize=2,color=col,label=name)
    a0.axhline(95,color=DARK,lw=.7,ls='--');a0.set_ylim(65,103);a0.set_ylabel('Programme success (%)');a0.set_xticks(range(5),['5','10','20','40*','60†']);a0.set_xlabel('Eligible work (%)');a0.legend(fontsize=6,frameon=False,loc='lower left');label(a0,'a','Earlier controller repair')
    z=target[target.program=='H8P16'].set_index('variant').loc[BASE]
    a1.plot(range(6),z.fresh_target_electrical_successes/3,'o',color=GRAY,ms=6,label='Fresh last call')
    a1.plot(range(6),z.repeated_target_electrical_successes/3,'x',color=TEAL,ms=6,label='Last of four calls')
    a1.set_ylim(65,104);a1.set_ylabel('Last-call electrical success (%)');a1.set_xticks(range(6),LABELS,rotation=40,ha='right');a1.legend(fontsize=6,frameon=False,loc='lower right');label(a1,'b','Identical last-call electrical outcomes')
    a2.set_xlim(-.5,3.5);a2.set_ylim(7.7,-1.05);a2.set_yticks(range(8),LABELS+['65 / tight / 20% GPU','80 / tight / 20% GPU']);a2.set_xticks(range(4),['16 h / 1%','16 h / zero','24 h / 1%','24 h / zero']);a2.xaxis.tick_top();a2.tick_params(length=0)
    a2.set_xlabel('Start spacing / missed-work standard');a2.xaxis.set_label_position('top');a2.set_ylabel('Offered utilisation (%) / deadline setting')
    for i,v in enumerate(ALL):
        for j,(prog,endpoint) in enumerate([('H8P16','success_1pct'),('H8P16','success_zero'),('H8P24','success_1pct'),('H8P24','success_zero')]):
            r=selected[(selected.variant==v)&(selected.program==prog)&(selected.endpoint==endpoint)].iloc[0]
            txt='Not selected' if pd.isna(r.selected_fraction) else f'{r.selected_capacity_kw:.2f} kW\n{int(r.confirmation_successes)}/300'
            a2.add_patch(plt.Rectangle((j-.47,i-.45),.94,.90,facecolor='#EDF3F5' if endpoint=='success_1pct' else '#EDF5F1',edgecolor='white'))
            a2.text(j,i,txt,ha='center',va='center',fontsize=7.3,color=GRAY if pd.isna(r.selected_fraction) else DARK)
    for sp in a2.spines.values():sp.set_visible(False)
    label(a2,'c','Complete eight-hour offer selections')
    a2.title.set_position((0,1.1))
    fig.subplots_adjust(left=.22,right=.98,top=.90,bottom=.16,hspace=1.05,wspace=.5)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_3','a: earlier seeds 970000–970299, 8-h calls with 12-h gaps; one-sided 95% Wilson lower bounds.\nb,c: new seeds 985000–985299; 10% eligible work. b: same results at 24-h spacing and 20% GPU controls.\nc: all selected entries pass pointwise confirmation; absent selections are not zero-capacity estimates.\nReference 4-h / 16-h programme: 4.42 kW, 300/300 under both service standards. * and † as in Fig. 6.')

    sens=read('structural_economic_sensitivity.csv');entry=read('structural_entry_examples.csv')
    fig,axs=plt.subplots(2,2,figsize=(7.205,6.5));a0,a1,a2,a3=axs.ravel()
    for prog,f,col,name in specs:
        z=sens[(sens.variant=='u65d100g10')&(sens.program==prog)&(sens.fraction==f)&(sens.site_fee_annual_usd==0)&(sens.missed_work_price==0)].sort_values('waiting_price')
        a0.plot(z.waiting_price,z.payment_per_kw,'o-',ms=3,color=col,label=name)
    a0.set_xlabel('Waiting price (US$/GPU-h/h)');a0.set_ylabel('Payment (US$/kW-year)');a0.legend(fontsize=6.2,frameon=False);label(a0,'a','Waiting exposure in zero-miss offers')
    for f,col,name in [(.5,TEAL,'2.95 kW: zero-miss selection'),(.75,BLUE,'4.42 kW: 1% selection'),(1,GRAY,'5.90 kW: unqualified comparator')]:
        z=sens[(sens.variant=='u65d100g10')&(sens.program=='H8P16')&(sens.fraction==f)&(sens.site_fee_annual_usd==0)&(sens.waiting_price==.005)].sort_values('missed_work_price')
        a1.plot(z.missed_work_price,z.payment_per_kw,'o-',ms=3,color=col,label=name)
    a1.set_xlabel('Missed-work price (US$/GPU-h)');a1.set_ylabel('Payment (US$/kW-year)');a1.legend(fontsize=6,frameon=False);label(a1,'b','Service losses and conditional cost')
    for prog,f,col,name in specs:
        z=entry[entry.program==prog].sort_values('fee');a2.plot(z.fee/1000,z.annual_net_value_lower/1000,'o-',color=col,ms=3,label=name)
    a2.axhline(0,color=DARK,lw=.8,ls='--');a2.set_xlabel('Annual site fee (US$ thousand)');a2.set_ylabel('5th-percentile annual net value\n(US$ thousand)');a2.legend(fontsize=6.2,frameon=False);label(a2,'c','Fees change entry, not conditional ranking')
    for fee,col,name in [(0,TEAL,'No site fee'),(2500,BLUE,'US$2,500 shared fee'),(25000,GRAY,'US$25,000 site fee')]:
        z=front[(front.endpoint=='success_zero')&(front.long_program=='H8P16')&(front.site_fee_annual_usd==fee)].sort_values('short_price')
        a3.plot(z.short_price,z.required_long_price_vs_short_and_opt_out,color=col,lw=1.5,label=name)
    a3.set_xlabel('4-h capacity price (US$/kW-year)');a3.set_ylabel('Minimum 8-h price\n(US$/kW-year)');a3.legend(fontsize=6.2,frameon=False);label(a3,'d','Long-service tariff including opt-out')
    fig.subplots_adjust(left=.14,right=.98,top=.90,bottom=.17,hspace=.8,wspace=.48)
    save(fig,a.output/'AIDRBench_Supplementary_Figure_5','Reference structural workload; 10% eligibility, 65% offered utilisation, reference deadlines; 12 series/year.\na,b: zero site fee. c: both duration prices are US$250 per offered accounting kW-year.\nAn unqualified request has no offerable economic value; its cost is diagnostic. Sharing divides fees only.\nReserve-life and displaced-value sensitivities remain in Supplementary Table 9 and the complete Source Data.')
    (a.output/'tradeoffs_figure_sources.json').write_text(json.dumps(dict(backend='Python/matplotlib',sources_sha256=used,figures=['3','6','S3','S5'],minimum_declared_font_pt=6),indent=2)+'\n')

if __name__=='__main__':main()
