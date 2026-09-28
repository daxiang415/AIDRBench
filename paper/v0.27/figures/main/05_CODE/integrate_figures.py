"""Preserve supplied slide composition; correct scientific plotting from frozen panel data.
No simulation, filtering, sampling or statistical re-estimation is performed.
"""
from pathlib import Path
from copy import deepcopy
import csv, json, zipfile, re, hashlib, io, sys, os
import xml.etree.ElementTree as E
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(os.environ.get('AIDRBENCH_FIGURE_WORK',str(Path(__file__).resolve().parent)))
WORK.mkdir(parents=True,exist_ok=True)
DATA=Path(os.environ.get('AIDRBENCH_FIGURE_DATA',str(ROOT/'results/exports/AIDRBench_Submission_v0.27_2026-09-13_PanelData/04_Redraw_Ready/01_PANEL_DATA')))
OUT=WORK/'corrected';OUT.mkdir(exist_ok=True)
PAN=OUT/'panels';PAN.mkdir(exist_ok=True)
N={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main','c':'http://schemas.openxmlformats.org/drawingml/2006/chart','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
for k,v in N.items():E.register_namespace(k,v)
for k,v in {'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006','c14':'http://schemas.microsoft.com/office/drawing/2007/8/2/chart','a14':'http://schemas.microsoft.com/office/drawing/2010/main','p14':'http://schemas.microsoft.com/office/powerpoint/2010/main','a16':'http://schemas.microsoft.com/office/drawing/2014/main','asvg':'http://schemas.microsoft.com/office/drawing/2016/SVG/main'}.items():E.register_namespace(k,v)
def tag(n):p,t=n.split(':');return '{'+N[p]+'}'+t
def read(name):
 with (DATA/name[:3]/(name+'.csv')).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def col(rows,key):return np.array([float(r[key]) for r in rows])
plt.rcParams.update({'font.family':'Liberation Serif','font.size':20,'axes.labelsize':20,'xtick.labelsize':19,'ytick.labelsize':19,'legend.fontsize':18,'axes.edgecolor':'#CCCCCC','axes.linewidth':.7,'grid.color':'#E8E8E8','grid.linewidth':.6,'pdf.fonttype':42,'svg.fonttype':'none','savefig.facecolor':'white'})
SOURCE=Path(os.environ.get('AIDRBENCH_SOURCE_PPTX',str(WORK/'received/figure/AIDRBench_Figure_.pptx')))
with zipfile.ZipFile(SOURCE) as z:files={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
slides={i:E.fromstring(files[f'ppt/slides/slide{i}.xml']) for i in range(1,7)}
RELS='{http://schemas.openxmlformats.org/package/2006/relationships}'
rels={i:E.fromstring(files[f'ppt/slides/_rels/slide{i}.xml.rels']) for i in range(1,7)}
# Use original chart-frame coordinates, not inferred positions from a raster.
def chart_frame(i,k):
 if i==3 and k==0:
  return next(g for g in slides[i].find('p:cSld/p:spTree',N) if ''.join(t.text or '' for t in g.findall('.//a:t',N)).startswith('CountsResource-timeWeek'))
 target=f'../charts/chart{k}.xml';rid=next(r.get('Id') for r in rels[i] if r.get('Target')==target)
 return next(g for g in slides[i].find('p:cSld/p:spTree',N) if g.find('.//c:chart',N) is not None and g.find('.//c:chart',N).get(tag('r:id'))==rid)
def bounds(el):
 x=el.find('p:xfrm',N)
 if x is None:x=el.find('p:spPr/a:xfrm',N)
 if x is None:return None
 o=x.find('a:off',N);s=x.find('a:ext',N)
 return tuple(float(v)/12700 for v in [o.get('x'),o.get('y'),s.get('cx'),s.get('cy')])
changes=[];panels=[]
def panel(i,k,name,margins=(.16,.18,.81,.76)):
 rect=bounds(chart_frame(i,k))
 if i==2:rect=(*rect[:3],440.)
 fig=plt.figure(figsize=(rect[2]/72,rect[3]/72));ax=fig.add_axes(margins);ax.grid(True);ax.set_axisbelow(True)
 return fig,ax,rect

def save_panel(i,k,name,fig,rect):
 fig.savefig(PAN/f'{name}.pdf')
 fig.savefig(PAN/f'{name}.svg')
 fig.savefig(PAN/f'{name}.png',dpi=300)
 plt.close(fig)
 panels.append({'slide':i,'chart':k,'name':name,'rect_pt':rect})

# Figure 2a: replace manually rounded/altered values; preserve four series and offsets.
f,a,r=panel(2,2,'F02a',(.14,.17,.83,.77));d=read('F02a');x=np.arange(len(d))
for offset,key,label,color,marker in [(-.15,'relaxed_PI_4h_kw','4 h relaxed PI','#EC8626','_'),(-.05,'confirmed_offer_4h_kw','4 h confirmed offer','#EC8626','o'),(.05,'relaxed_PI_8h_kw','8 h relaxed PI','#24B8AC','_'),(.15,'confirmed_offer_8h_kw','8 h confirmed offer','#24B8AC','s')]:
 a.plot(x+offset,col(d,key),ls='none',marker=marker,ms=10 if marker=='_' else 6,color=color,label=label,mew=1.8,mfc='white' if marker=='s' else color)
a.set(xticks=x,xticklabels=[r['x_label'] for r in d],ylim=(0,38),xlim=(-.5,4.5),xlabel='Work permitted to wait (%)',ylabel='Response (kW)');a.legend(loc='upper left',frameon=False,fontsize=18);save_panel(2,2,'F02a',f,r)
# Figure 2b: genuine categorical positions, with both coincident duration markers.
f,a,r=panel(2,3,'F02b',(.23,.17,.73,.77));d=read('F02b');y=col(d,'offer_peak_pct') if 'offer_peak_pct' in d[0] else None
if y is None:
 print('F02b columns',d[0]); y=col(d,'offer_4h_pct_peak')
a.plot(x,y,'o',ms=7,color='#EC8626',label='4 h');a.plot(x,y,'s',ms=9,mfc='none',mec='#24B8AC',mew=1.5,label='8 h');a.set(xticks=x,xticklabels=['5','10','20','40*','60†'],xlim=(-.5,4.5),ylim=(0,17),xlabel='Eligible work (%)',ylabel='Offer / operating peak (%)');a.legend(frameon=False,loc='upper left',fontsize=18);save_panel(2,3,'F02b',f,r)
# Figure 3b: lines between actual development points, with explicit qualification target.
f,a,r=panel(3,5,'F03b',(.15,.13,.82,.83));d=read('F03b')
for group,color,label in [('job_count','#279FA3','Counts'),('resource_gpu_h','#E7832F','Resource-time')]:
 for suffix,style,mark,sl in [('1pct','-','o','≤1% missed'),('zero','--','s','zero missed')]:
  a.plot(col(d,'request_kw'),col(d,group+'_success_'+suffix+'_lower'),ls=style,marker=mark,color=color,ms=5,mfc='white' if suffix=='zero' else color,lw=1.8,label=f'{label}, {sl}')
a.axhline(.95,color='#777777',ls=':',lw=1.2);a.text(5.85,.92,'95% target',ha='right',va='top',fontsize=16,color='#666666');a.set(xlim=(0,6),ylim=(0,1.02),xlabel='Tested request (kW)',ylabel='Success-probability lower bound');a.legend(frameon=False,loc='lower left',fontsize=16,labelspacing=.3);save_panel(3,5,'F03b',f,r)
# Figure 3d: portable category labels, without relying on WPS-only extensions.
f,a,r=panel(3,7,'F03d',(.37,.15,.60,.81));d=read('F03d');yy=np.arange(4)[::-1]
a.plot(col(d,'successes_zero'),yy,'o',color='#477CD0',ms=7,label='Zero missed work');a.plot(col(d,'successes_1pct'),yy,'s',ms=10,mfc='none',mec='#E7832F',mew=1.5,label='≤1% missed work')
a.set(xlim=(0,87),ylim=(-.5,3.9),yticks=yy,yticklabels=['Counts\nOriginal','Counts\nPermuted','Resource-time\nOriginal','Resource-time\nPermuted'],xticks=[0,20,40,60,80],xlabel='Successes at 2.95 kW (out of 80)');a.tick_params(axis='y',length=0,labelsize=17);a.legend(loc='upper left',frameon=False,fontsize=16);save_panel(3,7,'F03d',f,r)
# Figure 3e: replace clipped table text and truncated manual colour-bar labels.
from matplotlib.colors import LinearSegmentedColormap
r0=bounds(chart_frame(3,0));r=(170.,r0[1],585.,180.)
f=plt.figure(figsize=(r[2]/72,r[3]/72));a=f.add_axes((.18,.22,.72,.74));d=read('F03e');values=np.vstack([col(d,'job_count'),col(d,'resource_gpu_h')]);cmap=LinearSegmentedColormap.from_list('supplied_green',['#ECF2EF','#60B97A']);im=a.imshow(values/10,vmin=0,vmax=1,cmap=cmap,aspect='auto')
a.set(xticks=np.arange(8),xticklabels=[f'Week {i}' for i in range(1,9)],yticks=[0,1],yticklabels=['Counts','Resource-\ntime']);a.tick_params(length=0,labelsize=15);a.set_xticks(np.arange(-.5,8,1),minor=True);a.set_yticks(np.arange(-.5,2,1),minor=True);a.grid(which='minor',color='#555555',lw=.7);a.tick_params(which='minor',length=0)
for row in range(2):
 for j in range(8):a.text(j,row,f'{int(values[row,j])}/10',ha='center',va='center',fontsize=15)
cb=f.colorbar(im,cax=f.add_axes((.915,.22,.025,.74)),ticks=[0,.5,1]);cb.ax.tick_params(labelsize=14,length=0)
save_panel(3,0,'F03e',f,r)
# Figure 4b,c,d: use numerical hours and actual windows, retaining every plotted observation.
def windows(ax,name,number=False,tail=False):
 for q in read(name):
  if int(q['event_id'])<0:continue
  start=float(q['start_hour']);end=float(q['end_hour_exclusive']);ax.axvspan(start,end,color='#D5D5D5',alpha=.5,lw=0,zorder=0)
  if number:ax.text((start+end)/2,.97,str(int(q['event_id'])+1),transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=15)
 if tail:ax.axvspan(168,216,color='#EEEEEE',lw=0,zorder=0);ax.text(192,.8,'Clearance',transform=ax.get_xaxis_transform(),ha='center',fontsize=17)
f,a,r=panel(4,11,'F04b',(.17,.20,.80,.75));d=read('F04b')
for key,color,label in [('job_count_available_kw','#728EBB','Counts'),('resource_gpu_h_available_kw','#D9AD20','Resource-time')]:a.plot(col(d,'hour'),col(d,key),lw=1.3,color=color,label=label)
a.plot(col(d,'hour'),col(d,'required_delivery_kw'),':',color='#A55C6D',lw=2,label='95% delivery requirement');windows(a,'F04b_windows',True);a.set(xlim=(0,168),ylim=(0,21.5),xticks=[0,40,80,120,168],xlabel='Hour in workload test (h)',ylabel='Available reduction (kW)');a.legend(loc='lower left',frameon=True,framealpha=.9,fontsize=14,ncol=1);save_panel(4,11,'F04b',f,r)
f,a,r=panel(4,14,'F04c',(.11,.22,.87,.73));d=read('F04c')
for g,color,label in [('H4P16','#728EBB','4 h'),('H8P16','#39B794','8 h')]:
 a.plot(col(d,'hour'),col(d,g+'_reduction_kw'),color=color,lw=1.5,label=label+' reduction');a.plot(col(d,'hour'),col(d,g+'_request_kw'),color=color,ls=':',lw=2,label=label+' request')
windows(a,'F04c_windows',True,True);a.axhline(0,color='#AAAAAA',lw=.6);a.set(xlim=(0,216),ylim=(-21,10),xticks=[0,24,48,72,96,120,144,168,192,216],xlabel='Hour in reference confirmation sequence (h)',ylabel='Baseline − response\npower (kW)');a.legend(frameon=False,ncol=4,loc='lower left',fontsize=16);save_panel(4,14,'F04c',f,r)
f,a,r=panel(4,13,'F04d',(.11,.22,.87,.73));d=read('F04d')
for g,color,label in [('H4P16','#728EBB','4 h'),('H8P16','#39B794','8 h')]:a.plot(col(d,'hour'),col(d,g+'_backlog_gpu_h'),lw=1.5,color=color,label=label)
windows(a,'F04c_windows',True,True);a.set(xlim=(0,216),ylim=(0,510),xticks=[0,24,48,72,96,120,144,168,192,216],xlabel='Hour in reference confirmation sequence (h)',ylabel='Additional backlog (GPU-h)');a.legend(frameon=False,loc='upper left',ncol=2);save_panel(4,13,'F04d',f,r)
# Figure 6a: exact ECDF, exact data-coordinate means; no kW unit on waiting.
f,a,r=panel(6,20,'F06a',(.14,.19,.83,.77));d=read('F06a');means=read('F06a_means')
for g,color,label in [('H4P16','#D3A600','4 h: 5.60 kW'),('H8P16','#7770C9','8 h: 4.42 kW')]:
 a.step(col(d,g+'_waiting_thousand_gpu_h_h'),col(d,'cumulative_fraction'),where='post',color=color,lw=2,label=label)
 mean=next(float(q['mean_waiting_thousand_gpu_h_h']) for q in means if q['program']==g)
 a.axvline(mean,color=color,ls=':',lw=1.6);a.text(mean+.3,.35 if g=='H8P16' else .58,f'Mean {mean:.2f}',color=color,fontsize=18)
a.set(xlim=(5,35),ylim=(0,1.02),xlabel='Additional waiting (1,000 GPU-h × h / series)',ylabel='Cumulative fraction');a.legend(frameon=False,loc='upper left');save_panel(6,20,'F06a',f,r)
# Figure 6b: signed components and true data-position net thresholds.
f,a,r=panel(6,21,'F06b',(.17,.16,.80,.80));d=read('F06b');x=col(d,'x_position')
for key,color,label in [('waiting','#278F89','Waiting'),('electricity','#E98625','Electricity'),('delivery_credit','#79B63B','Delivery credit')]:a.bar(x,col(d,key),bottom=col(d,key+'_bottom'),width=.42,color=color,label=label)
a.plot(x,col(d,'net_threshold'),'D',ms=7,mfc='white',mec='#3C5B59',label='Net threshold')
for xx,v in zip(x,col(d,'net_threshold')):a.annotate(f'{v:.2f}',(xx,v),xytext=(25,8),textcoords='offset points',fontsize=18)
a.axhline(0,color='#999999',lw=.7);a.set(xlim=(-.6,1.6),ylim=(-35,420),xticks=x,xticklabels=['Four hours','Eight hours'],ylabel='Threshold (USD / offered kW-year)');a.legend(frameon=False,ncol=2,loc='upper left',fontsize=15);save_panel(6,21,'F06b',f,r)
# Figure 6d: retain three-region concept, draw exact frozen boundary and equal-price line.
f,a,r=panel(6,23,'F06d',(.16,.17,.81,.79));d=read('F06d');p4=col(d,'price_4h');bd=col(d,'choice_boundary_price_8h');b4=float(d[0]['four_hour_entry']);b8=float(d[0]['eight_hour_entry'])
a.fill_between(p4,bd,1100,color='#FFF0B7',lw=0);a.fill_between(p4,0,bd,where=p4>=b4,color='#F7D9DE',interpolate=True,lw=0);a.fill_between([0,b4],0,b8,color='#E6E6E6',lw=0);a.plot(p4,bd,color='#AD674C',lw=1.8);a.plot([b4,b4],[0,b8],color='#AD674C',lw=1.8);a.plot([0,750],[0,750],':',color='#777777',lw=1.4,label='Equal prices')
a.text(48,100,'No entry',fontsize=18);a.text(360,250,'Four-hour product',fontsize=18);a.text(100,805,'Eight-hour product',fontsize=18);a.set(xlim=(0,750),ylim=(0,1100),xticks=[0,150,300,450,600,750],xlabel='Four-hour price (USD / kW-year)',ylabel='Eight-hour price (USD / kW-year)');a.legend(frameon=False,loc='upper left',fontsize=16);save_panel(6,23,'F06d',f,r)

# Correct native slide labels; patch native c classification without changing its bars.
for i,root in slides.items():
 for t in root.findall('.//a:t',N):
  if t.text:
   t.text=t.text.replace('60+','60†').replace('P comparison:','PI comparison:').replace('* /t:','* / †:').replace('falilures','failures').replace('4h Mean: 16.49kW','4 h mean: 16.49').replace('8h Mean: 24.51kW','8 h mean: 24.51')
c6=E.fromstring(files['ppt/charts/chart6.xml'])
for v in c6.findall('.//c:tx//c:v',N):
 if v.text=='PI feasible; causal failure':v.text='Other infeasible'
 elif v.text=='Other infeasible':v.text='PI feasible; causal failure'
files['ppt/charts/chart6.xml']=E.tostring(c6,encoding='utf-8',xml_declaration=True)
# The supplied cost dots are correct; six manually placed stems were offset
# from those dots and have no statistical meaning. Retain the measured points.
tree5=slides[5].find('p:cSld/p:spTree',N)
for el in list(tree5):
 if el.tag==tag('p:cxnSp'):tree5.remove(el)
# Correct the success-strip proportions in native Figure 2c.
tree=slides[2].find('p:cSld/p:spTree',N)
for start,oldw,failx,failw,n in [(3777615,4010025,7784465,123825,295),(11043920,3956685,15000605,173990,292)]:
 total=oldw+failw;good=round(total*n/300)
 for el in tree:
  xf=el.find('p:spPr/a:xfrm',N)
  if xf is None:continue
  off=xf.find('a:off',N);ext=xf.find('a:ext',N)
  if off.get('x')==str(start) and ext.get('cx')==str(oldw):ext.set('cx',str(good))
  if off.get('x')==str(failx) and ext.get('cx')==str(failw):off.set('x',str(start+good));ext.set('cx',str(total-good))
# Remove obsolete manual overlays in replaced panels (kept unchanged in received/).
for i in [2,3,4,6]:
 tree=slides[i].find('p:cSld/p:spTree',N)
 for el in list(tree):
  txt=''.join(t.text or '' for t in el.findall('.//a:t',N))
  b=bounds(el)
  remove=False
  if i==2 and txt.strip().startswith('5 ') and '60' in txt:remove=True
  if i==3 and txt in ['1% missed work','Zero missed work']:remove=True
  if i==3 and b and el.tag!=tag('p:graphicFrame'):
   q=next(p['rect_pt'] for p in panels if p['name']=='F03d')
   cx=b[0]+b[2]/2;cy=b[1]+b[3]/2
   if q[0]<=cx<=q[0]+q[2] and q[1]<=cy<=q[1]+q[3]:remove=True
  if i==3 and el.tag==tag('p:graphicFrame') and b and b[1]>1000 and el is not chart_frame(3,0):
   if b[0]<760:remove=True
  # Manual overlays in chart4 lower traces: call strips, call numbers, labels.
  if i==4 and el.tag!=tag('p:graphicFrame') and b:
   cy=b[1]+b[3]/2
   rects=[p['rect_pt'] for p in panels if p['slide']==4]
   for q in rects:
    if b[0]>=q[0]-10 and b[0]+b[2]<=q[0]+q[2]+10 and cy>=q[1] and cy<=q[1]+q[3] and not re.match(r'^[bcd]\s',txt):remove=True
  if i==6 and b:
   # Supplied means, diamonds, hand-drawn fills and labels inside rebuilt a/b/d.
   for q in [p['rect_pt'] for p in panels if p['slide']==6]:
    cx=b[0]+b[2]/2;cy=b[1]+b[3]/2
    if q[0]<=cx<=q[0]+q[2] and q[1]<=cy<=q[1]+q[3] and el.tag!=tag('p:graphicFrame'):remove=True
  if remove:tree.remove(el)
# Replace corrected chart frames with vector SVG pictures; PNG fallback accompanies each.
for p in panels:
 i,k,name=p['slide'],p['chart'],p['name']; tree=slides[i].find('p:cSld/p:spTree',N);old=chart_frame(i,k);idx=list(tree).index(old);q=p['rect_pt']
 rid=f'rIdCorrected{name}';target=f'../media/{name}.svg';E.SubElement(rels[i],RELS+'Relationship',{'Id':rid,'Type':N['r']+'/image','Target':target});files[f'ppt/media/{name}.svg']=(PAN/f'{name}.svg').read_bytes()
 pic=E.Element(tag('p:pic'));nv=E.SubElement(pic,tag('p:nvPicPr'));E.SubElement(nv,tag('p:cNvPr'),{'id':str(800+k),'name':name+' verified vector plot'});E.SubElement(nv,tag('p:cNvPicPr'));E.SubElement(nv,tag('p:nvPr'))
 fill=E.SubElement(pic,tag('p:blipFill'));E.SubElement(fill,tag('a:blip'),{tag('r:embed'):rid});E.SubElement(E.SubElement(fill,tag('a:stretch')),tag('a:fillRect'))
 sp=E.SubElement(pic,tag('p:spPr'));xf=E.SubElement(sp,tag('a:xfrm'));E.SubElement(xf,tag('a:off'),{'x':str(round(q[0]*12700)),'y':str(round(q[1]*12700))});E.SubElement(xf,tag('a:ext'),{'cx':str(round(q[2]*12700)),'cy':str(round(q[3]*12700))});geom=E.SubElement(sp,tag('a:prstGeom'),{'prst':'rect'});E.SubElement(geom,tag('a:avLst'));tree.remove(old);tree.insert(idx,pic)
for i in range(1,7):
 files[f'ppt/slides/slide{i}.xml']=E.tostring(slides[i],encoding='utf-8',xml_declaration=True)
 E.register_namespace('',RELS[1:-1])
 files[f'ppt/slides/_rels/slide{i}.xml.rels']=E.tostring(rels[i],encoding='utf-8',xml_declaration=True)
ct=E.fromstring(files['[Content_Types].xml']);ns='{http://schemas.openxmlformats.org/package/2006/content-types}'
if not any(x.get('Extension')=='svg' for x in ct):E.SubElement(ct,ns+'Default',{'Extension':'svg','ContentType':'image/svg+xml'})
E.register_namespace('',ns[1:-1])
files['[Content_Types].xml']=E.tostring(ct,encoding='utf-8',xml_declaration=True)
# Keep namespace declarations used only inside MC Requires/Ignorable attribute values.
with zipfile.ZipFile(SOURCE) as source_zip:
 for name in ['ppt/charts/chart6.xml']+[f'ppt/slides/slide{i}.xml' for i in range(1,7)]:
  old=source_zip.read(name).decode();new=files[name].decode()
  root_end=new.index('>',new.index('?>')+2)
  declarations=[]
  for prefix,uri in re.findall(r'xmlns:([\w]+)="([^"]+)"',old[:old.index('>',old.index('?>')+2)]):
   if f'xmlns:{prefix}=' not in new[:root_end]:declarations.append(f' xmlns:{prefix}="{uri}"')
  files[name]=(new[:root_end]+''.join(declarations)+new[root_end:]).encode()
with zipfile.ZipFile(OUT/'AIDRBench_Figures_R8_corrected.pptx','w',zipfile.ZIP_DEFLATED) as z:
 for n,b in files.items():z.writestr(n,b)
(OUT/'panel_replacements.json').write_text(json.dumps(panels,indent=2))
print('Created',len(panels),'verified panel plots and corrected PPTX')
