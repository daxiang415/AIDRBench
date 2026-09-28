"""Render S1--S10 directly from the CSVs next to each supplied reference figure.

No simulation, aggregation, fitting, resampling, or hidden source tables.
Edit STYLE / plotting calls to change appearance; edit the CSVs to change inputs.
The supplied reference PDFs remain untouched. See README_中文_给合作者.md.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
COLORS = ['#286277', '#299C8F', '#B07935', '#84919B']
STYLE = {'font.family': 'DejaVu Sans', 'font.size': 7,
         'axes.labelsize': 7, 'axes.titlesize': 8, 'xtick.labelsize': 6.5,
         'ytick.labelsize': 6.5, 'legend.fontsize': 6, 'axes.spines.top': False,
         'axes.spines.right': False, 'axes.linewidth': .6,
         'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
         'lines.linewidth': 1, 'lines.markersize': 3.5}

LABELS = {'success_1pct': 'At most 1% missed', 'success_zero': 'Zero missed',
          'no_BESS': 'Without BESS', 'with_BESS': 'With BESS',
          'rigid': 'Rigid', 'flexible': 'Flexible',
          'job_count success_1pct': 'Counts; 1%',
          'job_count success_zero': 'Counts; zero',
          'resource_gpu_h success_1pct': 'Resource time; 1%',
          'resource_gpu_h success_zero': 'Resource time; zero',
          'rigid_no_BESS_kwh': 'Rigid, no BESS',
          'flexible_no_BESS_kwh': 'Flexible, no BESS',
          'rigid_with_BESS_kwh': 'Rigid, BESS',
          'flexible_with_BESS_kwh': 'Flexible, BESS',
          'rigid_no_BESS_mwh': 'Rigid, no BESS',
          'flexible_no_BESS_mwh': 'Flexible, no BESS',
          'rigid_with_BESS_mwh': 'Rigid, BESS',
          'flexible_with_BESS_mwh': 'Flexible, BESS'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', nargs='+', choices=[f'S{i}' for i in range(1, 11)])
    parser.add_argument('--output', type=Path, default=ROOT/'MY_REDRAW')
    parser.add_argument('--tiff', action='store_true', help='Also export 600-dpi TIFFs.')
    parser.add_argument('--audit', action='store_true', help='Save actual Matplotlib coordinates for verification.')
    args = parser.parse_args()
    out = args.output.absolute()
    # Do not overwrite the reference folders or the data/code package root.
    if out == ROOT or any(out == ROOT/f'S{i:02}' or ROOT/f'S{i:02}' in out.parents for i in range(1, 11)):
        parser.error('Choose a separate output directory; reference folders are protected.')
    out.mkdir(parents=True, exist_ok=True)
    tables = json.loads((ROOT/'PANEL_INDEX.json').read_text(encoding='utf-8'))
    assignments = json.loads((ROOT/'PLOT_ASSIGNMENTS.json').read_text(encoding='utf-8'))
    used = {}
    records = []
    plt.rcParams.update(STYLE)

    def read(t):
        p = ROOT/t['file']
        used[t['file']] = hashlib.sha256(p.read_bytes()).hexdigest()
        return pd.read_csv(p, encoding='utf-8-sig', float_precision='round_trip')

    for number in [int(x[1:]) for x in (args.figures or [f'S{i}' for i in range(1, 11)])]:
        key = f'S{number:02}'
        metadata = json.loads((ROOT/key/'axes_reference.json').read_text(encoding='utf-8'))
        letters = list(metadata)
        if number == 1:
            fig, array = plt.subplots(2, 1, figsize=(180/25.4, 110/25.4))
            axes = dict(zip(letters, array))
        elif number == 2:
            fig, array = plt.subplots(1, 2, figsize=(180/25.4, 88/25.4))
            axes = dict(zip(letters, array))
        elif number == 9:
            fig = plt.figure(figsize=(180/25.4, 150/25.4))
            grid = fig.add_gridspec(2, 2)
            axes = {'a': fig.add_subplot(grid[0, 0]), 'b': fig.add_subplot(grid[0, 1]),
                    'c': fig.add_subplot(grid[1, :])}
        else:
            fig, array = plt.subplots(2, 2, figsize=(180/25.4, (165 if number == 6 else 150)/25.4))
            axes = dict(zip(letters, array.flat))
        for panel, ax in axes.items():
            meta = metadata[panel]
            ts = [t for t in tables if t['figure'] == key and t['panel'] == panel]
            local = {t['id']: read(t) for t in ts}
            bs = [b for b in assignments if b['table'] in local]
            title = '\n'.join(textwrap.wrap(meta['title'], width=90 if number == 1 else 41))
            ax.set_title(title, loc='left', pad=10)
            ax.text(-.11 if number != 1 else -.035, 1.085, panel,
                    transform=ax.transAxes, fontsize=10, fontweight='bold')
            ax.set_xlabel(meta['xlabel']); ax.set_ylabel(meta['ylabel'])
            if number == 1:
                # All wording and box centres are supplied in S01a/b.csv.
                d = next(iter(local.values()))
                for i, row in d.iterrows():
                    x, y = row.x_canvas, row.y_canvas
                    if i < 3:
                        ax.add_patch(Rectangle((x-.125, y-.16), .25, .32,
                                              fc='#F4F7F8', ec=COLORS[0], lw=1))
                    ax.text(x, y, row.text, ha='center', va='center', fontsize=7 if i < 3 else 6)
                for left, right in [(0, 1), (1, 2)]:
                    a, b = d.iloc[left], d.iloc[right]
                    ax.annotate('', xy=(b.x_canvas-.13, b.y_canvas),
                                xytext=(a.x_canvas+.13, a.y_canvas),
                                arrowprops={'arrowstyle': '->', 'color': COLORS[3], 'lw': .8})
                ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis('off')
                continue
            for j, bind in enumerate(bs):
                d = local[bind['table']]
                label = LABELS.get(bind['series'], bind['series'])
                color = COLORS[j % len(COLORS)]
                kind = bind['kind']
                if kind == 'matrix':
                    matrix = d[bind['columns']].to_numpy()
                    if bind.get('transpose'): matrix = matrix.T
                    im = ax.imshow(matrix, aspect='auto', vmin=0, vmax=300,
                                   cmap='Blues' if panel in 'ab' else 'YlOrBr')
                    for (row, col), value in np.ndenumerate(matrix):
                        ax.text(col, row, f'{value:.0f}', ha='center', va='center',
                                color='white' if value > 180 else '#34424C', fontsize=6.5)
                    fig.colorbar(im, ax=ax, fraction=.038, pad=.04, ticks=[0, 100, 200, 300], label='Cases / 300')
                    continue
                x, y = d[bind['x']].to_numpy(), d[bind['y']].to_numpy()
                if kind == 'bar':
                    bottom = d[bind['bottom']].to_numpy() if 'bottom' in bind else 0
                    ax.bar(x, y, bottom=bottom, width=.72 if number == 3 and panel == 'd' else .34,
                           color=color, label=label)
                elif kind == 'barh':
                    ax.barh(y, x, height=.55, color=[COLORS[3], '#BEC7CB', COLORS[0], COLORS[1]])
                    for xx, yy in zip(x, y): ax.annotate(f'{xx:.2f}', (xx, yy), xytext=(3, 0), textcoords='offset points', va='center', fontsize=6)
                elif kind == 'errorbar':
                    lo, hi = d[bind['lower']].to_numpy(), d[bind['upper']].to_numpy()
                    ax.errorbar(x, y, yerr=[y-lo, hi-y], fmt='o' if j == 0 else 's',
                                color=color, capsize=2, elinewidth=.8, label=label)
                elif number == 2 and panel == 'a':
                    seen = set()
                    for _, row in d.iterrows():
                        role = row.calibration_role
                        if role not in {'fit', 'held_out'}:
                            raise ValueError(f'Unknown calibration role: {role}')
                        filled = role == 'fit'
                        ax.scatter([row[bind['x']]], [row[bind['y']]], s=16,
                                   facecolors=color if filled else 'none', edgecolors=color,
                                   linewidths=.7,
                                   label=('Fit' if filled else 'Held out') if role not in seen else '_nolegend_')
                        seen.add(role)
                elif number == 10 and panel in 'cd':
                    ax.scatter(x, y, s=9, color=color, alpha=.8)
                elif number == 3 and panel == 'd':
                    ax.plot(x, y, 'D', color=COLORS[1], label=label)
                else:
                    line, marker = '-', 'o'
                    if number == 4: line = 'none'
                    if number == 5: marker = None
                    if number == 3 and panel in 'ab' and 'zero' in bind['series']:
                        line, marker = '--', 's'
                    if number == 7 and panel in 'ab':
                        color = COLORS[3] if bind['series'] == 'rigid' else COLORS[1]
                        line = '--' if bind['series'] == 'rigid' else '-'
                    if number == 7 and panel in 'cd':
                        line = '--' if bind['series'].startswith('rigid') else '-'
                        color = COLORS[0] if 'no_BESS' in bind['series'] else COLORS[1]
                    if number == 9 and panel == 'b':
                        line = '--' if 'zero' in bind['series'] else '-'
                        marker = 's' if 'zero' in bind['series'] else 'o'
                        color = COLORS[0] if 'job_count' in bind['series'] else COLORS[2]
                    ax.plot(x, y, linestyle=line, marker=marker, color=color, label=label)
            # Explicit axis units/ticks and viewing ranges from the frozen figures.
            for axis in ['x', 'y']:
                ticks, labels = meta[axis+'ticks'], meta[axis+'ticklabels']
                if all(re.fullmatch(r'[−\-+\d.,]*', label) for label in labels) and not (number == 3 and panel == 'd' and axis == 'x'):
                    # Numeric ticks must retain their real magnitude. Reference
                    # tick strings can rely on a separate scientific exponent.
                    getattr(ax, 'set_'+axis+'ticks')(ticks)
                    ax.ticklabel_format(axis=axis, style='sci', scilimits=(-3, 4), useOffset=False)
                else:
                    getattr(ax, 'set_'+axis+'ticks')(ticks, labels)
                getattr(ax, 'set_'+axis+'lim')(meta[axis+'lim'])
            if number == 3 and panel in 'ab' or number == 9:
                ax.axhline(.95, color='#9D9D9D', ls=':', lw=.7, zorder=0)
            if number == 4 and panel == 'c': ax.axhline(95, color='#9D9D9D', ls=':', lw=.7)
            if number == 5 and panel in 'ac': ax.axhline(0, color='#999999', lw=.7)
            if number == 10 and panel in 'cd':
                low = max(meta['xlim'][0], meta['ylim'][0]); high = min(meta['xlim'][1], meta['ylim'][1])
                ax.plot([low, high], [low, high], '--', color='#AAAAAA', lw=.7, zorder=0)
            if number == 9 and panel == 'a':
                d = next(iter(local.values()))
                for _, row in d.iterrows(): ax.text(row.x_position, 1.005, f'{row.capacity_kw:.2f} kW', ha='center', fontsize=6.5)
            if number == 10 and panel == 'b':
                d = next(iter(local.values()))
                for _, row in d.iterrows(): ax.annotate(f'{row.operating_peak_kw:.2f} kW', (row.node_overhead_w, row.single_offer_pct_peak), xytext=(0, 6), textcoords='offset points', ha='center', fontsize=6)
            if number == 6:
                ax.tick_params(length=0)
                for spine in ax.spines.values(): spine.set_visible(False)
            else:
                handles, labels = ax.get_legend_handles_labels()
                if handles and not (len(handles) == 1 and number in [5, 10]):
                    ax.legend(handles, labels, frameon=False, loc='best', handlelength=1.4,
                              ncol=2 if number == 7 and panel in 'cd' else 1)
        fig.tight_layout(pad=1.6, h_pad=3.2, w_pad=2)
        fig.subplots_adjust(bottom=max(fig.subplotpars.bottom, .10))
        fig.text(.02, .015, f'Supplementary Figure {number} | Direct-CSV redraw template. See accompanying full caption.', fontsize=6, color='#626B70')
        stem = out/f'AIDRBench_Supplementary_Figure_{number}'
        if args.audit:
            from audit.capture_artists import capture
            target = out/'captured'; target.mkdir(exist_ok=True)
            (target/(stem.name+'.json')).write_text(json.dumps(capture(fig), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        for ext in ['pdf', 'svg', 'png'] + (['tiff'] if args.tiff else []):
            fig.savefig(stem.with_suffix('.'+ext), dpi=600 if ext == 'tiff' else 300)
        plt.close(fig)
        records.append({'figure': key, 'panels': len(axes), 'tables': [t['id'] for t in tables if t['figure'] == key]})
        print(f'{key}: exported PDF, SVG, PNG' + (', TIFF' if args.tiff else ''), flush=True)
    (out/'render_log.json').write_text(json.dumps({'figures': records, 'csv_sha256': used,
        'input_mode': 'direct_panel_csv_only', 'new_simulations': 0}, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
