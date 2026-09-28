"""Read numeric artists from the actual frozen R7 rendering functions."""
from pathlib import Path
import argparse
import json
import runpy
import sys

import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.collections import PathCollection, LineCollection, PolyCollection
from matplotlib.container import BarContainer, ErrorbarContainer
import numpy as np


def array(value):
    return np.asarray(value, dtype=float).tolist()


def capture(fig):
    result={}
    for ax in fig.axes:
        letters=[t.get_text() for t in ax.texts if t.get_text() in list('abcdefghij')]
        if len(letters)!=1:
            continue
        rows=[]
        for line in ax.lines:
            rows.append(dict(kind='line',xy=array(line.get_xydata()),label=line.get_label(),drawstyle=line.get_drawstyle()))
        for collection in ax.collections:
            if isinstance(collection,PathCollection):
                rows.append(dict(kind='scatter',xy=array(collection.get_offsets()),label=collection.get_label()))
            elif isinstance(collection,LineCollection):
                rows.append(dict(kind='segments',segments=[array(x) for x in collection.get_segments()]))
            elif isinstance(collection,PolyCollection):
                rows.append(dict(kind='polygons',paths=[array(p.vertices) for p in collection.get_paths()]))
        for container in ax.containers:
            if isinstance(container,BarContainer):
                vertical=container.orientation=='vertical'
                xy=[];bottom=[]
                for p in container.patches:
                    xy.append([p.get_x()+p.get_width()/2,p.get_height()] if vertical else [p.get_width(),p.get_y()+p.get_height()/2])
                    bottom.append(p.get_y() if vertical else p.get_x())
                rows.append(dict(kind='bar',orientation=container.orientation,xy=array(xy),bottom=array(bottom)))
            elif isinstance(container,ErrorbarContainer):
                line,caps,collections=container.lines
                if line is not None:
                    rows.append(dict(kind='errorbar',xy=array(line.get_xydata()),segments=[array(s) for c in collections for s in c.get_segments()]))
        for im in ax.images:
            rows.append(dict(kind='matrix',values=array(im.get_array())))
        result[letters[0]]=dict(title=ax.get_title(loc='left'),xlabel=ax.get_xlabel(),ylabel=ax.get_ylabel(),xlim=array(ax.get_xlim()),ylim=array(ax.get_ylim()),
            xticks=array(ax.get_xticks()),xticklabels=[t.get_text() for t in ax.get_xticklabels()],
            yticks=array(ax.get_yticks()),yticklabels=[t.get_text() for t in ax.get_yticklabels()],
            artists=rows,text=[dict(text=t.get_text(),position=array(t.get_position())) for t in ax.texts])
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--capture-dir',type=Path,required=True);p.add_argument('--names',nargs='+',required=True);p.add_argument('--script',type=Path,required=True)
    a,rest=p.parse_known_args();a.capture_dir.mkdir(parents=True,exist_ok=True)
    names=set(a.names);original=Figure.savefig
    def save(fig,path,*args,**kwargs):
        path=Path(path)
        if path.suffix=='.pdf' and path.stem in names:
            record=capture(fig)
            (a.capture_dir/(path.stem+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        return original(fig,path,*args,**kwargs)
    Figure.savefig=save
    sys.path.insert(0,str(a.script.parent));sys.argv=[str(a.script),*rest]
    runpy.run_path(str(a.script),run_name='__main__')


if __name__=='__main__':main()
