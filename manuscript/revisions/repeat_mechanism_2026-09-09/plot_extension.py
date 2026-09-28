"""Draw revised figures from ready tables only; no statistical recomputation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/aidrbench-repeat-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],
    'text.parse_math':False,'font.size':8,'axes.titlesize':9,'axes.labelsize':8,
    'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,
    'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,
    'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white'})
CASES=['f05','f10','f20','f40','f60'];LABELS=['5','10','20','40*','60†'];X=np.arange(5)
PROGRAMS=['H4G8','H8G8','H8G12','H8G16'];PLABEL=['4 h / 8 h','8 h / 8 h','8 h / 12 h','8 h / 16 h']
BLUE='#235A78';TEAL='#269383';ORANGE='#B27640';GRAY='#7C8790';DARK='#293740'
COLORS={'original':GRAY,'all_window_mpc':TEAL,'all_window_greedy':ORANGE}
NAMES={'original':'Original MPC','all_window_mpc':'MPC with per-call recovery','all_window_greedy':'Greedy with per-call recovery'}
FOOT='* Nearly all batch work opts in.  † Changed business composition; online jobs are never deferred.'


def label(ax,letter,title):
    ax.set_title(title,loc='left',pad=12)
    ax.text(-.13,1.08,letter,transform=ax.transAxes,fontsize=11,fontweight='bold')


def fractions(ax):
    ax.set_xticks(X,LABELS);ax.set_xlabel('Work eligible for deferral (%)')
    ax.axvline(2.5,color='#B9BDC0',lw=.7,ls=':')


def save(fig,path,foot):
    fig.text(.03,.02,foot,fontsize=6.5,ha='left',va='bottom')
    fig.savefig(path.with_suffix('.pdf'))
    fig.savefig(path.with_suffix('.svg'))
    fig.savefig(path.with_suffix('.png'),dpi=300)
    fig.savefig(path.with_suffix('.tiff'),dpi=600)
    plt.close(fig)


def row_for(summary,case,program,controller,fraction):
    g=summary[(summary.case==case)&(summary.program==program)&(summary.controller==controller)&np.isclose(summary.fraction,fraction)]
    assert len(g)==1,(case,program,controller,fraction)
    return g.iloc[0]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True)
    ap.add_argument('--base-data',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True);used={}
    def read(name,base=False):
        p=(args.base_data if base else args.data)/name
        used[('base/' if base else 'extension/')+name]=hashlib.sha256(p.read_bytes()).hexdigest()
        return pd.read_csv(p)
    summary=read('confirmation_summary.csv');selected=read('selected_offers.csv')
    pairs=read('paired_controller_contrasts.csv');windows=read('illustration_windows.csv')
    # Figure 3: same request, transparent mechanism example, qualified choices.
    fig=plt.figure(figsize=(7.205,5.8));grid=fig.add_gridspec(2,2,height_ratios=[1,1.05])
    a=fig.add_subplot(grid[0,:]);b=fig.add_subplot(grid[1,0]);c=fig.add_subplot(grid[1,1])
    for ctrl,offset in [('original',-.10),('all_window_mpc',.10)]:
        g=summary[(summary.program=='H8G12')&(summary.controller==ctrl)&(summary.fraction==1)].set_index('case').loc[CASES]
        y=g.success_fraction.to_numpy()*100;lo=g.wilson_lower.to_numpy()*100
        a.errorbar(X+offset,y,yerr=[y-lo,np.zeros(5)],fmt='o' if ctrl=='original' else 's',
            color=COLORS[ctrl],ms=5,capsize=3,lw=1,label=NAMES[ctrl])
    a.axhline(95,color=DARK,ls='--',lw=.7);fractions(a)
    a.set_ylabel('Four-call success (%)');a.set_ylim(65,102)
    a.legend(loc='lower left',ncol=2);label(a,'a','Same eight-hour offer, twelve-hour gaps')
    # The lowest development seed rescued by the intervention, never a test-set-picked example.
    failing=windows[(windows.controller=='original')&windows.window_peak_failure].sort_values('event_id')
    assert len(failing)
    w=failing.iloc[0];center=w.baseline_peak_kw;start=w.start_hour
    original=read('illustration_original.csv');fixed=read('illustration_all_window_mpc.csv')
    whole=original[original.hour.between(start,w.recovery_stop_hour-1)]
    peak_hour=int(whole.loc[whole.pcc_power_kw.idxmax(),'hour'])
    left=max(int(start),peak_hour-3);right=min(int(w.recovery_stop_hour)-1,peak_hour+3)
    for f,ctrl in [(original,'original'),(fixed,'all_window_mpc')]:
        z=f[f.hour.between(left,right)]
        b.plot(z.hour-start,z.pcc_power_kw-center,'o-',color=COLORS[ctrl],ms=3,lw=1.2,label=NAMES[ctrl])
    b.axhline(w.allowed_window_peak_kw-center,color=DARK,lw=.8,ls='--',label='Required window ceiling')
    b.set_xlabel('Hours since illustrated call began');b.set_ylabel('PCC power minus window\nbaseline peak (kW)')
    b.legend(loc='lower left',fontsize=6.5);label(b,'b','Recovery peak in a development example')
    c.set_xlim(-.75,1.75);c.set_ylim(-.6,3.9);c.invert_yaxis();c.set_axis_off()
    for j,name in enumerate(['Original','Per-call recovery']):c.text(j,-.45,name,ha='center',fontsize=7.5,fontweight='bold')
    for i,program in enumerate(PROGRAMS):
        c.text(-.7,i+.35,PLABEL[i],ha='right',va='center',fontsize=7)
        for j,ctrl in enumerate(['original','all_window_mpc']):
            s=selected[(selected.case=='f10')&(selected.program==program)&(selected.controller==ctrl)].iloc[0]
            if pd.isna(s.selected_fraction):text='None selected';color=GRAY
            else:
                r=row_for(summary,'f10',program,ctrl,s.selected_fraction)
                text=f'{s.selected_capacity_kw:.2f} kW'+('' if r.qualified else ' ×');color=COLORS[ctrl]
            c.text(j,i+.35,text,ha='center',va='center',fontsize=8,color=color)
    label(c,'c','Selected offers at 10% eligibility')
    fig.subplots_adjust(left=.12,right=.98,top=.9,bottom=.17,hspace=.85,wspace=.72)
    save(fig,out/'AIDRBench_Figure_3',FOOT+'\na: n = 300 new paired scenarios; one-sided 95% Wilson lower bounds. c: duration / gap; × fails confirmation.\nNone selected means no development candidate passed, not zero physical capacity.')

    # Figure 6: preserve original single-event accounts, update repeated selections.
    econ=read('economic_primary.csv',base=True);sensitivity=read('economic_price_sensitivity.csv',base=True)
    repeat=read('economic_primary.csv')
    fig,axs=plt.subplots(2,2,figsize=(7.205,5.8))
    for j,h in enumerate([4,8]):
        ax=axs[0,j]
        for regime,color,offset,name in [('slack',BLUE,-.18,'Existing slack'),('reserved_headroom',TEAL,0,'Reserved headroom'),('displacement_0.25',ORANGE,.18,'Assumed displaced value')]:
            g=econ[(econ.kind=='single')&(econ.duration_h==h)&(econ.regime==regime)].set_index('case').loc[CASES]
            ax.bar(X+offset,g.risk_adjusted_capacity_payment_usd_kw_year,width=.17,color=color,label=name)
        fractions(ax);ax.set_ylabel('Capacity payment\n(US$/kW-year)')
        label(ax,chr(97+j),f'{h} h single events; 50 calls/year');ax.legend(fontsize=6.5,loc='upper right')
    for j,program in enumerate(PROGRAMS):
        color=[BLUE,ORANGE,TEAL,GRAY][j]
        g=repeat[(repeat.program==program)&(repeat.controller=='all_window_mpc')&(repeat.regime=='slack')&repeat.selected_by_development]
        for i,case in enumerate(CASES):
            z=g[g.case==case]
            if not len(z):continue
            assert len(z)==1;r=z.iloc[0]
            axs[1,0].scatter(i+(j-1.5)*.10,r.payment_usd_kw_year,color=color,
                marker=['o','s','^','D'][j] if r.confirmation_qualified else 'x',s=22)
        axs[1,0].scatter([],[],color=color,marker=['o','s','^','D'][j],label=PLABEL[j])
    fractions(axs[1,0]);axs[1,0].set_ylabel('Capacity payment\n(US$/kW-year)')
    axs[1,0].legend(fontsize=6.5,ncol=2,loc='upper right');label(axs[1,0],'c','Selected repeated offers; 12 series/year')
    for h,color in [(4,BLUE),(8,TEAL)]:
        g=sensitivity[(sensitivity.kind=='single')&(sensitivity.case=='f10')&(sensitivity.duration_h==h)&
            (sensitivity.fixed_site_cost==25000)&(sensitivity.effective_displaced_value_usd_gpu_h==0)&(sensitivity.missed_work_price==0)].sort_values('delay_price')
        axs[1,1].plot(g.delay_price,g.risk_adjusted_capacity_payment_usd_kw_year,'o-',color=color,ms=4,label=f'{h} h')
    axs[1,1].set_xlabel('Delay price (US$/GPU-hour/hour)');axs[1,1].set_ylabel('Capacity payment\n(US$/kW-year)');axs[1,1].legend()
    label(axs[1,1],'d','Delay price at 10% eligibility')
    fig.subplots_adjust(left=.12,right=.98,top=.86,bottom=.22,wspace=.45,hspace=.85)
    save(fig,out/'AIDRBench_Figure_6',FOOT+'\n1-MW accounting; US$25,000/year site cost. c: MPC with per-call recovery; legend gives duration / gap.\nSymbols pass independent confirmation; × does not. Costs are conditional accounting thresholds.')

    # Supplementary Figure 3: state trajectories, failure families, full selection map.
    curves=read('ready_hourly_curves.csv');dev=read('development_summary.csv')
    fig=plt.figure(figsize=(7.205,7.6));gs=fig.add_gridspec(3,2,height_ratios=[1,1,1])
    aa=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:]),fig.add_subplot(gs[2,:])]
    for j,metric in enumerate(['excess_backlog_gpu_h','cumulative_missed_gpu_h']):
        for ctrl in ['original','all_window_mpc','all_window_greedy']:
            z=curves[(curves.role=='confirmation')&(curves.case=='f10')&(curves.program=='H8G12')&(curves.controller==ctrl)&(curves.fraction==1)&(curves.metric==metric)].sort_values('hour')
            assert len(z)==216
            aa[j].plot(z.hour,z['mean'],color=COLORS[ctrl],lw=1,label=NAMES[ctrl])
            aa[j].fill_between(z.hour,z.p05,z.p95,color=COLORS[ctrl],alpha=.13,lw=0)
        for start in [63,83,103,123]:aa[j].axvspan(start,start+8,color=GRAY,alpha=.08,lw=0)
        aa[j].set_xlabel('Episode hour');aa[j].set_xlim(48,216)
        aa[j].set_ylabel('Additional queued work (GPU-h)' if j==0 else 'Cumulative missed work (GPU-h)')
        label(aa[j],chr(97+j),'Queue burden, full offer' if j==0 else 'Deadline outcome, full offer')
    aa[0].legend(fontsize=6.5,loc='upper left',bbox_to_anchor=(0,-.33),borderaxespad=0,frameon=False)
    for j,(ctrl,metric,color,name) in enumerate([
        ('original','failures_window_peak_relief',GRAY,'Original: window peak'),
        ('all_window_mpc','failures_window_peak_relief',TEAL,'Per-call: window peak'),
        ('original','failures_deadline_miss',GRAY,'Original: deadline'),
        ('all_window_mpc','failures_deadline_miss',TEAL,'Per-call: deadline')]):
        z=dev[(dev.case=='f10')&(dev.controller==ctrl)&(dev.fraction==1)].set_index('program').loc[PROGRAMS]
        aa[2].bar(np.arange(4)+(j-1.5)*.18,z[metric]/z.trials*100,width=.17,color=color,hatch='//' if j>=2 else None,label=name)
    aa[2].set_xticks(range(4),PLABEL);aa[2].set_xlabel('Call duration / gap');aa[2].set_ylabel('Failed scenarios (%)')
    aa[2].legend(ncol=2,fontsize=6.5,loc='upper right');label(aa[2],'c','Two failure conditions at full offers (development, n = 100)')
    ax=aa[3];ax.set_xlim(-.5,7.5);ax.set_ylim(4.5,-1.2)
    ax.set_yticks(range(5),LABELS);ax.set_ylabel('Eligible work (%)')
    ax.set_xticks(range(8),['Original','Per-call']*4,fontsize=6.5)
    for j,program in enumerate(PROGRAMS):ax.text(j*2+.5,-.85,PLABEL[j],ha='center',fontsize=7)
    for i,case in enumerate(CASES):
        for j,program in enumerate(PROGRAMS):
            for z,ctrl in enumerate(['original','all_window_mpc']):
                s=selected[(selected.case==case)&(selected.program==program)&(selected.controller==ctrl)].iloc[0]
                if pd.isna(s.selected_fraction):text='—';color=GRAY
                else:
                    r=row_for(summary,case,program,ctrl,s.selected_fraction)
                    text=f'{100*s.selected_fraction:.0f}'+(' ✓' if r.qualified else ' ×');color=COLORS[ctrl]
                ax.text(j*2+z,i,text,ha='center',va='center',fontsize=8,color=color)
    for border in [1.5,3.5,5.5]:ax.axvline(border,color='#CCD1D4',lw=.7)
    label(ax,'d','Selected fraction of the original offer (%) and independent confirmation')
    fig.subplots_adjust(left=.12,right=.98,top=.93,bottom=.15,hspace=1.0,wspace=.45)
    save(fig,out/'AIDRBench_Supplementary_Figure_3',FOOT+'\na,b: n = 300 new scenarios; means and 5th–95th scenario percentiles. Shading marks calls.\nc: failure counts can overlap; these diagnostic criteria do not replace joint qualification.\nd: ✓ passes confirmation; × fails; — no development candidate selected, not zero physical capacity.')
    outputs={p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
        for p in out.glob('*.*') if p.suffix in ['.pdf','.svg','.png','.tiff'] and p.name.startswith('AIDRBench_')}
    (out/'extension_source_manifest.json').write_text(json.dumps(dict(inputs=used,outputs=outputs,
        revised_figures=['Figure 3','Figure 6','Supplementary Figure 3'],backend='python',minimum_font_pt=6.5,
        all_primary_cases_retained=True,illustration='lowest rescued development seed, not selected from confirmation'),indent=2)+'\n')


if __name__=='__main__':main()
