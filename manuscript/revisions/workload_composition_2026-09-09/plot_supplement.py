"""Five supplementary figures from ready drawing tables, using Python only."""

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/aidrbench-mix-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from plot_results import BLUE, GRAY, ORANGE, TEAL

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "text.parse_math": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--through", type=int, choices=[2, 3, 4, 5], default=5)
    ap.add_argument(
        "--calibration-only",
        action="store_true",
        help="review schematic and completed calibration inputs",
    )
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    used = {}

    def read(name):
        used[name] = hashlib.sha256((a.data / name).read_bytes()).hexdigest()
        return pd.read_csv(a.data / name)

    def label(ax, letter, title):
        xpos = -0.065 if ax.get_subplotspec().get_gridspec().ncols == 1 else -0.13
        ax.set_title(title, loc="left", pad=12)
        ax.text(xpos, 1.09, letter, transform=ax.transAxes, fontweight="bold", fontsize=11)

    def save(fig, n, foot=""):
        fig.subplots_adjust(left=0.11, right=0.98, bottom=0.22, top=0.84, wspace=0.42, hspace=0.75)
        if n == 1:
            fig.subplots_adjust(bottom=0.14, hspace=0.60)
        if foot:
            fig.text(0.03, 0.025, foot, fontsize=6.5, va="bottom")
        stem = a.output / f"AIDRBench_Supplementary_Figure_{n}"
        fig.savefig(stem.with_suffix(".pdf"))
        fig.savefig(stem.with_suffix(".svg"))
        fig.savefig(stem.with_suffix(".png"), dpi=300)
        fig.savefig(stem.with_suffix(".tiff"), dpi=600)
        plt.close(fig)

    fig, axs = plt.subplots(2, 1, figsize=(7.205, 4.2))
    for ax in axs:
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    def box(ax, x, y, text, w=0.25, h=0.32, color=BLUE):
        from matplotlib.patches import Rectangle

        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc="#F4F7F8", ec=color, lw=1))
        ax.text(x, y, text, ha="center", va="center", fontsize=8)

    def arrow(ax, x1, y1, x2, y2):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1, color=GRAY)
        )

    box(axs[0], 0.14, 0.55, "Source class shares\n+ declared permission")
    box(axs[0], 0.5, 0.55, "Paired job templates\n+ GPU / power model")
    box(axs[0], 0.86, 0.55, "Hourly deadline queue\n+ community PCC")
    arrow(axs[0], 0.27, 0.55, 0.37, 0.55)
    arrow(axs[0], 0.63, 0.55, 0.73, 0.55)
    axs[0].text(
        0.5,
        0.09,
        "5%, 10%, 20%: source mix retained     40%: wider opt-in     60%: changed business mix",
        ha="center",
        fontsize=7,
    )
    label(axs[0], "a", "From workload composition to electrical response")
    box(axs[1], 0.14, 0.6, "100 development seeds\nPI → candidate selection")
    box(axs[1], 0.5, 0.6, "300 confirmation seeds\nSingle + repeated tests")
    box(axs[1], 0.86, 0.6, "Complete paired ledgers\n+ participation costs")
    arrow(axs[1], 0.27, 0.6, 0.37, 0.6)
    arrow(axs[1], 0.63, 0.6, 0.73, 0.6)
    axs[1].text(
        0.5,
        0.08,
        "Separate full-information branch: PV hosting and utilisation, with / without BESS (100 seeds)",
        ha="center",
        fontsize=7,
    )
    label(axs[1], "b", "Evidence flow and independent qualification")
    save(
        fig,
        1,
        "Schematic of the declared study. Online work is rigid. Batteries act only in renewable planning.",
    )

    runs = read("calibration_run_means.csv")
    cal = read("calibration_class_summary.csv")
    fig, axs = plt.subplots(1, 2, figsize=(7.205, 3.8))
    conditions = [
        ("training", 1),
        ("training", 4),
        ("offline_inference", 1),
        ("offline_inference", 4),
    ]
    for x, (mode, ngpu) in enumerate(conditions):
        g = runs[(runs["mode"] == mode) & (runs.gpu_count == ngpu)]
        for r in g.itertuples():
            off = (r.repeat - 2) * 0.13 + (r.gpu_index - (ngpu - 1) / 2) * 0.025
            axs[0].scatter(
                x + off,
                r.mean_power_w,
                s=19,
                facecolors=BLUE if r.calibration_role == "fit" else "white",
                edgecolors=BLUE,
                lw=0.8,
            )
    axs[0].set_xticks(
        range(4), ["Train\n1 GPU", "Train\n4 GPUs", "Offline\n1 GPU", "Offline\n4 GPUs"]
    )
    axs[0].set_ylabel("Board power (W/GPU)")
    axs[0].set_ylim(200, 315)
    label(axs[0], "a", "All board-level run means")
    axs[1].errorbar(
        range(2),
        cal.estimate_w_per_gpu,
        yerr=[
            cal.estimate_w_per_gpu - cal.interval_lower_w_per_gpu,
            cal.interval_upper_w_per_gpu - cal.estimate_w_per_gpu,
        ],
        fmt="o",
        color=TEAL,
        capsize=4,
    )
    axs[1].set_xticks(range(2), ["Training", "Offline inference"])
    axs[1].set_xlim(-0.5, 1.5)
    axs[1].set_ylim(200, 315)
    axs[1].set_ylabel("Active coefficient (W/GPU)")
    label(axs[1], "b", "Calibration uncertainty")
    save(
        fig,
        2,
        "Filled points: fitting runs 1–2; open: held-out run 3. Boards within a run are not independent repeats.\nIntervals: 95% Student t from two independent four-GPU run means. Overall held-out MAE: 3.80 W/GPU.",
    )
    if a.calibration_only or a.through == 2:
        return

    curves = read("ready_hourly_curves.csv")
    fig, axs = plt.subplots(2, 2, figsize=(7.205, 5.9))
    for j, h in enumerate([4, 8]):
        g = curves[
            (curves.case == "f10")
            & (curves.duration_h == h)
            & (curves.tag == "single_offer_repeated")
        ]
        assert len(g), (h, "missing complete repeated trajectories")
        for row, (metric, title, unit) in enumerate(
            [
                ("excess_backlog_gpu_h", "Excess queued work", "GPU-hours"),
                ("incremental_power_kw", "PCC change from no response", "kW"),
            ]
        ):
            d = g[g.metric == metric].sort_values("event_relative_hour")
            ax = axs[row, j]
            ax.fill_between(d.event_relative_hour, d.p05, d.p95, color=BLUE, alpha=0.18)
            ax.plot(d.event_relative_hour, d["mean"], color=BLUE, lw=1.1)
            gap = 8 if h == 4 else 12
            for k in range(4):
                ax.axvspan(k * (h + gap), k * (h + gap) + h, color=ORANGE, alpha=0.16, lw=0)
            ax.axhline(0, color=GRAY, lw=0.6)
            ax.set_xlabel("Hours from first call")
            ax.set_ylabel(unit)
            label(
                ax,
                chr(97 + row * 2 + j),
                f"{h} h calls: {title[0].lower() + title[1:] if metric != 'incremental_power_kw' else title}",
            )
    save(
        fig,
        3,
        "10% eligibility; original single-event offer used for all four calls. All 300 scenarios, including failures.\nLine: mean. Band: descriptive 5th–95th scenario percentiles. Shading: event hours. Entire clearance tail retained.",
    )

    if a.through == 3:
        return

    single = read("single_confirm_summary.csv")
    controls = read("control_causal_summary.csv")
    pv = read("renewable_paired_comparisons.csv")
    obs = pd.concat([single[single.notice_h == 0], controls])
    cset = ["f10", "f10_g20", "f10_g30", "f10_rigid150", "f10_rigid225"]
    labels = ["Primary", "GPUs\n20%", "GPUs\n30%", "Rigid\n150 W", "Rigid\n225 W"]
    x = np.arange(5)
    fig, axs = plt.subplots(1, 2, figsize=(7.205, 4.0))
    for h, color, off in [(4, BLUE, -0.07), (8, TEAL, 0.07)]:
        d = obs[obs.duration_h == h].set_index("case").loc[cset]
        y = d.successes / d.trials * 100
        axs[0].errorbar(
            x + off,
            y,
            yerr=[y - d.wilson_lower * 100, np.zeros(5)],
            fmt="o",
            color=color,
            label=f"{h} h",
            capsize=2,
            ms=4,
        )
    axs[0].axhline(95, color=GRAY, ls="--", lw=0.8)
    axs[0].set_ylim(max(0, min(85, obs.wilson_lower.min() * 100 - 3)), 101)
    axs[0].set_ylabel("Success (%)")
    for bess, color, off in [(False, BLUE, -0.07), (True, TEAL, 0.07)]:
        d = (
            pv[(pv.bess_enabled == bess) & (pv.analysis == "pv_hosting")]
            .set_index("case")
            .loc[cset]
        )
        axs[1].scatter(
            x + off,
            d.difference_of_all_scenario_minima,
            color=color,
            label="With BESS" if bess else "No BESS",
            s=30,
        )
    axs[1].set_ylabel("PV hosting gain (kW)")
    axs[1].axhline(0, color=GRAY, lw=0.6)
    for ax in axs:
        ax.set_xticks(x, labels)
        ax.legend(loc="lower left" if ax is axs[0] else "upper left", fontsize=7)
    label(axs[0], "a", "Transfer of the unchanged single offer")
    label(axs[1], "b", "All-scenario PV hosting gain")
    save(
        fig,
        4,
        "All cases retain 10% eligibility. Left: n = 300; one-sided 95% Wilson limits.\nRight: difference of minima over 100 paired scenarios; not a mean effect or uncertainty interval.",
    )

    if a.through == 4:
        return

    econ = read("economic_price_sensitivity.csv")
    life = read("reserve_life_sensitivity.csv")
    fig, axs = plt.subplots(1, 2, figsize=(7.205, 3.9))
    common = econ[
        (econ.kind == "single")
        & (econ.case == "f10")
        & (econ.duration_h == 4)
        & (econ.effective_displaced_value_usd_gpu_h == 0)
        & (econ.missed_work_price == 0)
    ]
    for fixed, color in [(10000, BLUE), (25000, TEAL), (50000, ORANGE)]:
        d = common[common.fixed_site_cost == fixed].sort_values("delay_price")
        axs[0].plot(
            d.delay_price,
            d.risk_adjusted_capacity_payment_usd_kw_year,
            "o-",
            color=color,
            label=f"Site US${fixed / 1000:.0f},000/year",
            ms=4,
        )
    axs[0].set_xlabel("Delay price (US$/GPU-hour/hour)")
    axs[0].set_ylabel("Capacity payment (US$/kW-year)")
    axs[0].legend(fontsize=7, loc="center left", bbox_to_anchor=(0, 0.58))
    for h, color in [(4, BLUE), (8, TEAL)]:
        d = life[
            (life.kind == "single") & (life.case == "f10") & (life.duration_h == h)
        ].sort_values("economic_life_years")
        axs[1].plot(
            d.economic_life_years,
            d.risk_adjusted_capacity_payment_usd_kw_year,
            "o-",
            color=color,
            label=f"{h} h",
            ms=4,
        )
    axs[1].set_xticks([3, 4, 5, 6])
    axs[1].set_xlabel("Assumed reserve economic life (years)")
    axs[1].set_ylabel("Capacity payment (US$/kW-year)")
    axs[1].legend()
    label(axs[0], "a", "Delay and site-cost assumptions")
    label(axs[1], "b", "Reserve-life assumption")
    save(
        fig,
        5,
        "10% eligibility; 50 independent calls/year, 1-MW accounting. Points are conditional decision thresholds.\nLines join evaluated prices; no confidence intervals. Reserve life is an accounting assumption, not measured GPU ageing.",
    )
    outputs = {
        p.name: dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
        for p in a.output.glob("AIDRBench_Supplementary_Figure_*.*")
    }
    (a.output / "supplement_source_manifest.json").write_text(
        json.dumps(dict(inputs=used, outputs=outputs), indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
