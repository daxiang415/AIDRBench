"""Draw six review figures directly from the complete exported study tables.

Python only. No statistical recomputation, fitted curves, or mock observations.
Run with --data PATH --output PATH; all editable files are exported together.
"""

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

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "text.parse_math": False,
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.7,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
    }
)
BLUE = "#235A78"
TEAL = "#269383"
ORANGE = "#B27640"
GRAY = "#7C8790"
CASES = ["f05", "f10", "f20", "f40", "f60"]
X = np.arange(5)
LABELS = ["5", "10", "20", "40*", "60†"]
FOOT = (
    "* Nearly all batch work opts in.  † Online work is replaced "
    "by offline work; online jobs are never deferred."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--first-only",
        action="store_true",
        help="review the completed source-composition figure while simulations run",
    )
    ap.add_argument(
        "--through",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        default=6,
        help="render completed leading figures only; no complete manifest until all six",
    )
    args = ap.parse_args()
    data = args.data
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    used = {
        name: hashlib.sha256((data / name).read_bytes()).hexdigest()
        for name in ["source_audit.json", "case_definitions.json"]
    }

    def read(name):
        used[name] = hashlib.sha256((data / name).read_bytes()).hexdigest()
        return pd.read_csv(data / name)

    def label(ax, letter, title):
        ax.set_title(title, loc="left", pad=13)
        ax.text(-0.14, 1.09, letter, transform=ax.transAxes, fontweight="bold", fontsize=11)

    def fractions(ax):
        ax.set_xticks(X, LABELS)
        ax.set_xlabel("Work eligible for deferral (%)")
        ax.axvline(2.5, color="#B9BDC0", lw=0.7, ls=":")

    def save(fig, n, foot=FOOT):
        fig.subplots_adjust(left=0.11, right=0.98, bottom=0.23, top=0.84, wspace=0.40, hspace=0.75)
        if n == 1:
            fig.subplots_adjust(left=0.19, wspace=0.64)
        if foot:
            fig.text(0.03, 0.035, foot, fontsize=6.5, ha="left", va="bottom", wrap=True)
        stem = out / f"AIDRBench_Figure_{n}"
        fig.savefig(stem.with_suffix(".pdf"))
        fig.savefig(stem.with_suffix(".svg"))
        fig.savefig(stem.with_suffix(".png"), dpi=300)
        fig.savefig(stem.with_suffix(".tiff"), dpi=600)
        plt.close(fig)

    audit = json.loads((data / "source_audit.json").read_text())
    definitions = json.loads((data / "case_definitions.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(7.205, 3.6))
    names = ["online_inference", "offline_inference", "training", "dev", "other", "unknown"]
    display = [
        "Online inference",
        "Offline inference",
        "Training",
        "Development",
        "Other",
        "Unknown",
    ]
    values = [100 * audit["shares"][c] for c in names]
    axs[0].barh(display[::-1], values[::-1], color=[ORANGE, TEAL, BLUE, GRAY, GRAY, GRAY][::-1])
    for y, v in enumerate(values[::-1]):
        axs[0].text(v + 0.5, y, f"{v:.2f}", va="center", fontsize=7)
    axs[0].set_xlim(0, 67)
    axs[0].set_xlabel("Share of requested GPU-hours (%)")
    label(axs[0], "a", "Observed resource-time composition")
    train = np.array([c["eligible_shares"]["training"] * 100 for c in definitions])
    offline = np.array([c["eligible_shares"]["offline_inference"] * 100 for c in definitions])
    axs[1].bar(X, train, color=BLUE, label="Training")
    axs[1].bar(X, offline, bottom=train, color=TEAL, label="Offline inference")
    fractions(axs[1])
    axs[1].set_ylabel("Eligible share of total work (%)")
    axs[1].set_ylim(0, 68)
    axs[1].legend(loc="upper left")
    label(axs[1], "b", "Declared eligibility scenarios")
    save(fig, 1)
    if args.first_only or args.through == 1:
        return

    pi = read("pi_boundaries.csv")
    ss = read("single_confirm_summary.csv")
    fig, axs = plt.subplots(1, 2, figsize=(7.205, 3.9))
    for j, (h, color) in enumerate([(4, BLUE), (8, TEAL)]):
        bounds = pi[(pi.role == "confirmation") & (pi.duration_h == h)].set_index("case").loc[CASES]
        offers = ss[(ss.duration_h == h) & (ss.notice_h == 0)].set_index("case").loc[CASES]
        x = X + (j - 0.5) * 0.18
        axs[0].scatter(
            x,
            bounds.perfect_information_firm_capacity_kw,
            marker="_",
            s=110,
            c=color,
            label=f"{h} h relaxed PI",
        )
        for k, row in enumerate(offers.itertuples()):
            axs[0].scatter(
                x[k], row.capacity_kw, marker="o" if row.qualified else "x", s=26, c=color
            )
        for ni, notice in enumerate([0, 2, 6]):
            g = ss[(ss.duration_h == h) & (ss.notice_h == notice)].set_index("case").loc[CASES]
            y = 100 * g.successes / g.trials
            lower = g.wilson_lower * 100
            axs[1].errorbar(
                X + (j * 3 + ni - 2.5) * 0.105,
                y,
                yerr=[y - lower, np.zeros(5)],
                fmt=["o", "s", "^"][ni],
                markersize=3,
                color=color,
                lw=0.7,
                capsize=1.5,
                label=f"{h} h; notice {notice} h",
            )
    label(axs[0], "a", "Planning and tested offers")
    axs[0].set_ylabel("Response (kW)")
    axs[0].set_ylim(bottom=0)
    fractions(axs[0])
    axs[0].legend(loc="upper left")
    label(axs[1], "b", "Success across notice periods")
    axs[1].axhline(95, color=GRAY, ls="--", lw=0.8)
    axs[1].set_ylabel("Success (%)")
    axs[1].set_ylim(max(0, min(85, np.floor(ss.wilson_lower.min() * 100) - 2)), 101)
    fractions(axs[1])
    axs[1].legend(ncol=2, loc="lower left")
    save(
        fig,
        2,
        FOOT
        + (
            "\nDots: tested offers (crosses if unqualified). Success bars:"
            " one-sided 95% Wilson lower bounds; n = 300 per condition."
        ),
    )
    if args.through == 2:
        return

    rep = read("repeat_paired_comparisons.csv")
    rd = read("repeat_dev_summary.csv")
    fig, axs = plt.subplots(2, 2, figsize=(7.205, 5.8))
    for j, h in enumerate([4, 8]):
        g = rep[rep.duration_h == h].set_index("case").loc[CASES]
        a = axs[0, j]
        a.bar(
            X - 0.16,
            g.fresh_joint_successes / 3,
            width=0.30,
            color=GRAY,
            label="Four isolated calls, all pass",
        )
        a.bar(
            X + 0.16,
            g.repeated_successes / 3,
            width=0.30,
            color=BLUE,
            label="Four repeated calls, all pass",
        )
        for offset, success, lower in [
            (-0.16, g.fresh_joint_successes / 3, g.fresh_joint_lower * 100),
            (0.16, g.repeated_successes / 3, g.repeated_lower * 100),
        ]:
            a.errorbar(
                X + offset,
                success,
                yerr=[success - lower, np.zeros(5)],
                fmt="none",
                ecolor="#182B36",
                capsize=2,
                lw=0.7,
            )
        fractions(a)
        a.set_ylabel("Programme success (%)")
        a.set_ylim(0, 112)
        a.axhline(95, color=GRAY, ls="--", lw=0.7)
        label(a, chr(97 + j), f"{h} h calls; {8 if h == 4 else 12} h recovery gaps")
        if j == 0:
            programme_legend = a.get_legend_handles_labels()
        b = axs[1, j]
        for k, (fraction, marker, color) in enumerate(
            [(0.25, "o", GRAY), (0.5, "s", TEAL), (0.75, "^", ORANGE), (1.0, "D", BLUE)]
        ):
            trial = (
                rd[(rd.duration_h == h) & (rd.tag == f"fraction{fraction}")]
                .set_index("case")
                .loc[CASES]
            )
            b.scatter(
                X + (k - 1.5) * 0.13,
                trial.wilson_lower * 100,
                s=20,
                marker=marker,
                color=color,
                label=f"{int(100 * fraction)}% of single offer",
            )
        b.axhline(95, color=GRAY, ls="--", lw=0.7)
        b.legend(loc="lower left", ncol=2, fontsize=6.5)
        fractions(b)
        b.set_ylabel("95% probability lower bound (%)")
        b.set_ylim(50, 101)
        label(b, chr(99 + j), "Development search; 100 scenarios")
    fig.legend(
        *programme_legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.105),
        ncol=2,
        fontsize=7,
        frameon=False,
    )
    save(
        fig,
        3,
        FOOT
        + (
            "\nOne-sided 95% Wilson limits; dashed line: 95% target. No ca"
            "ndidate passed the separate development selection rule."
        ),
    )
    if args.through == 3:
        return

    pv = read("renewable_paired_comparisons.csv")
    fig, axs = plt.subplots(1, 2, figsize=(7.205, 3.8))
    for bess, color, offset in [(False, BLUE, -0.06), (True, TEAL, 0.06)]:
        name = "With storage" if bess else "Without storage"
        hosting = (
            pv[(pv.analysis == "pv_hosting") & (pv.bess_enabled == bess)]
            .set_index("case")
            .loc[CASES]
        )
        op = (
            pv[(pv.analysis == "fixed_pv_operation") & (pv.bess_enabled == bess)]
            .set_index("case")
            .loc[CASES]
        )
        axs[0].scatter(
            X + offset, hosting.difference_of_all_scenario_minima, color=color, label=name, s=30
        )
        axs[1].errorbar(
            X + offset,
            op.mean_paired_gain,
            yerr=[op.mean_paired_gain - op.gain_ci_low, op.gain_ci_high - op.mean_paired_gain],
            fmt="o",
            color=color,
            label=name,
            markersize=4,
            capsize=2,
        )
    for a in axs:
        fractions(a)
        a.axhline(0, color=GRAY, lw=0.7)
        a.legend(loc="upper left")
    label(axs[0], "a", "Additional PV hosting")
    axs[0].set_ylabel("PV hosting gain (kW)")
    label(axs[1], "b", "Use of a fixed 500-kW PV system")
    axs[1].set_ylabel("Utilisation gain (percentage points)")
    save(
        fig,
        4,
        FOOT
        + (
            "\nZero missed work; n = 100. Intervals cover sampling only; t"
            "iny storage effects are limited by solver precision."
        ),
    )
    if args.through == 4:
        return

    cp = read("control_pi_boundaries.csv")
    econ = read("economic_primary.csv")
    fig, axs = plt.subplots(2, 2, figsize=(7.205, 5.8))
    for j, (cset, title, xlabels) in enumerate(
        [
            (
                ["f10", "f10_g20", "f10_g30"],
                "GPU allocation at 10% eligibility",
                ["10", "20", "30"],
            ),
            (
                ["f10_rigid150", "f10_rigid225", "f10"],
                "Rigid power at 10% eligibility",
                ["150", "225", "300"],
            ),
        ]
    ):
        bound = pd.concat([pi[pi.role == "confirmation"], cp])
        for h, color in [(4, BLUE), (8, TEAL)]:
            g = bound[bound.duration_h == h].set_index("case").loc[cset]
            axs[0, j].plot(
                np.arange(3),
                g.perfect_information_firm_capacity_kw,
                "o-",
                color=color,
                label=f"{h} h relaxed PI",
                ms=4,
            )
        axs[0, j].set_xticks(range(3), xlabels)
        axs[0, j].set_ylabel("Response (kW)")
        axs[0, j].set_ylim(0, 6.5)
        axs[0, j].set_xlabel(
            "Flexible GPUs (%)" if j == 0 else "Unmeasured rigid active power proxy (W/GPU)"
        )
        axs[0, j].legend(loc="lower left")
        label(axs[0, j], chr(97 + j), title)
        g = (
            econ[
                (econ.duration_h == 4)
                & (econ.regime == "slack")
                & econ.kind.str.startswith("single")
            ]
            .set_index("case")
            .loc[cset]
        )
        axs[1, j].bar(
            range(3), g.risk_adjusted_capacity_payment_usd_kw_year, color=BLUE, width=0.55
        )
        for i, row in enumerate(g.itertuples()):
            if not row.qualified:
                axs[1, j].text(
                    i,
                    row.risk_adjusted_capacity_payment_usd_kw_year,
                    "×",
                    ha="center",
                    va="bottom",
                    fontsize=12,
                )
        axs[1, j].set_xticks(range(3), xlabels)
        axs[1, j].set_ylabel("Capacity payment\n(US$/kW-year)")
        axs[1, j].set_xlabel("Flexible GPUs (%)" if j == 0 else "Rigid active power proxy (W/GPU)")
        label(axs[1, j], chr(99 + j), "Cost of the same four-hour request")
    save(
        fig,
        5,
        (
            "All controls retain 10% eligibility, jobs and event times. C"
            "ost uses 50 independent calls/year and 1-MW accounting.\nThe "
            "rigid-load coefficients are engineering sensitivities, not o"
            "nline-inference power measurements."
        ),
    )
    if args.through == 5:
        return

    fig, axs = plt.subplots(2, 2, figsize=(7.205, 5.8))
    for j, h in enumerate([4, 8]):
        a = axs[0, j]
        for r, color, offset, disp in [
            ("slack", BLUE, -0.18, "Existing slack"),
            ("reserved_headroom", TEAL, 0, "Reserved headroom"),
            ("displacement_0.25", ORANGE, 0.18, "Assumed displaced value"),
        ]:
            g = (
                econ[(econ.kind == "single") & (econ.duration_h == h) & (econ.regime == r)]
                .set_index("case")
                .loc[CASES]
            )
            bars = a.bar(
                X + offset,
                g.risk_adjusted_capacity_payment_usd_kw_year,
                width=0.17,
                color=color,
                label=disp,
            )
            for bar, row in zip(bars, g.itertuples(), strict=True):
                if not row.qualified:
                    bar.set_hatch("xx")
                    bar.set_alpha(0.45)
        fractions(a)
        a.set_ylabel("Capacity payment\n(US$/kW-year)")
        label(a, chr(97 + j), f"{h} h single events; 50 calls/year")
        a.legend(fontsize=6.5, loc="upper right")
    for h, color, offset in [(4, BLUE, -0.07), (8, TEAL, 0.07)]:
        original = econ[
            (econ.kind == "repeated_original") & (econ.duration_h == h) & (econ.regime == "slack")
        ].set_index("case")
        for i, c in enumerate(CASES):
            row = original.loc[c]
            axs[1, 0].scatter(
                i + offset,
                row.risk_adjusted_capacity_payment_usd_kw_year,
                s=28,
                color=color,
                marker="o" if row.qualified else "x",
            )
        g = econ[
            (econ.kind == "repeated") & (econ.duration_h == h) & (econ.regime == "slack")
        ].set_index("case")
        for i, c in enumerate(CASES):
            if c in g.index:
                row = g.loc[c]
                if abs(row.offered_kw - original.loc[c].offered_kw) > 1e-12:
                    axs[1, 0].scatter(
                        i + offset,
                        row.risk_adjusted_capacity_payment_usd_kw_year,
                        s=35,
                        color=color,
                        marker="D" if row.qualified else "x",
                    )
        axs[1, 0].scatter([], [], color=color, marker="o" if h == 4 else "x", label=f"{h} h calls")
    fractions(axs[1, 0])
    axs[1, 0].set_ylabel("Capacity payment\n(US$/kW-year)")
    axs[1, 0].legend(loc="upper right")
    label(axs[1, 0], "c", "Repeated programmes; 12 series/year")
    sens = read("economic_price_sensitivity.csv")
    for h, color in [(4, BLUE), (8, TEAL)]:
        g = sens[
            (sens.kind == "single")
            & (sens.case == "f10")
            & (sens.duration_h == h)
            & (sens.fixed_site_cost == 25000)
            & (sens.effective_displaced_value_usd_gpu_h == 0)
            & (sens.missed_work_price == 0)
        ].sort_values("delay_price")
        axs[1, 1].plot(
            g.delay_price,
            g.risk_adjusted_capacity_payment_usd_kw_year,
            "o-",
            color=color,
            label=f"{h} h",
            ms=4,
        )
    axs[1, 1].set_xlabel("Delay price (US$/GPU-hour/hour)")
    axs[1, 1].set_ylabel("Capacity payment\n(US$/kW-year)")
    axs[1, 1].legend()
    label(axs[1, 1], "d", "Delay price at 10% eligibility")
    save(
        fig,
        6,
        FOOT
        + (
            "\n1-MW accounting; US$25,000/year site cost. Circles pass the"
            " confirmation criterion; crosses do not."
        ),
    )
    outputs = {
        p.name: dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
        for p in out.glob("AIDRBench_Figure_*.*")
    }
    (out / "source_manifest.json").write_text(
        json.dumps(
            dict(
                status="local_data_driven_review_figures",
                inputs=used,
                figures=[f"AIDRBench_Figure_{n}" for n in range(1, 7)],
                outputs=outputs,
                all_five_primary_cases_shown=True,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
