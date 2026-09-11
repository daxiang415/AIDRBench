"""Portable exact copy of the frozen fixed-request feasibility solver."""

import time
import warnings

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp


def solve_snapshot(s, request, miss_rate, *, time_limit=90.0):
    """No job may execute outside its own release/deadline interval.

    Binary selectors express the evaluator's *actual* event-peak denominator.
    An infeasible MILP is never inferred from a timeout or absent incumbent.
    """
    groups = (
        pd.DataFrame(s.work_groups, columns=["release", "deadline", "job_class", "work"])
        .groupby(["release", "deadline", "job_class"], as_index=False)
        .work.sum()
    )
    T = s.total_hours
    G = len(groups)
    edges = []
    for i, g in enumerate(groups.itertuples(index=False)):
        edges.extend((i, t, g.job_class) for t in range(g.release, min(g.deadline + 1, T)))
    ei = np.array([x[0] for x in edges])
    et = np.array([x[1] for x in edges])
    ec = [x[2] for x in edges]
    E = len(edges)
    events = list(s.events)
    nh = sum(e.stop_hour - e.start_hour for e in events)
    # Execution edges, per-group missed work and terminal backlog,
    # event peaks, and peak selectors.
    mo = E
    bo = E + G
    zo = E + 2 * G
    yo = zo + len(events)
    N = yo + nh
    lower = np.zeros(N)
    upper = np.full(N, np.inf)
    integrality = np.zeros(N, dtype=int)
    upper[mo:bo] = groups.work.to_numpy()
    upper[bo:zo] = np.where(groups.deadline >= T, groups.work, 0.0)
    for i, g in enumerate(groups.itertuples(index=False)):
        if g.deadline >= T:
            upper[mo + i] = 0.0
    upper[yo:] = 1.0
    integrality[yo:] = 1
    coeff = dict(s.dynamic_kw_per_gpu_h_by_class)
    edgepower = np.array([coeff[x] for x in ec])
    B = np.array(s.baseline_pcc_power_kw)
    rigid = np.array(s.community_power_kw) + s.fixed_dc_power_kw
    dynamicmax = max(coeff.values()) * s.capacity_gpu_h
    bigM = max(2 * dynamicmax, 1.0)
    upper[zo:yo] = dynamicmax
    rows = []
    cols = []
    values = []
    lbs = []
    ubs = []

    def add(indices, weights, lo=-np.inf, hi=np.inf):
        row = len(lbs)
        indices = np.asarray(indices, dtype=int)
        weights = np.broadcast_to(weights, indices.shape)
        rows.extend([row] * len(indices))
        cols.extend(indices.tolist())
        values.extend(weights.tolist())
        lbs.append(lo)
        ubs.append(hi)

    group_edges = [np.flatnonzero(ei == i) for i in range(G)]
    hour_edges = [np.flatnonzero(et == t) for t in range(T)]
    for i, g in enumerate(groups.itertuples(index=False)):
        add(np.r_[group_edges[i], mo + i, bo + i], 1.0, g.work, g.work)
    add(np.arange(mo, bo), 1.0, hi=miss_rate * s.total_arrival_gpu_h)
    add(np.arange(bo, zo), 1.0, hi=s.baseline_terminal_backlog_gpu_h + 0.02 * s.total_arrival_gpu_h)
    for t, ix in enumerate(hour_edges):
        add(ix, 1.0, hi=s.capacity_gpu_h)
        add(ix, edgepower[ix], hi=s.pcc_capacity_kw - rigid[t])
    y = yo
    for j, e in enumerate(events):
        z = zo + j
        active = list(range(e.start_hour, e.stop_hour))
        window = list(range(e.start_hour, e.recovery_stop_hour))
        # Every interval >= 95% implies the same capped-mean >= 95% criterion.
        for k, t in enumerate(active):
            ix = hour_edges[t]
            pw = edgepower[ix]
            d = B[t] - rigid[t]
            add(ix, pw, hi=d - 0.95 * request)
            add(np.r_[ix, z], np.r_[pw, 1.0], lo=d)  # peak >= B - P
            add(np.r_[ix, z, y + k], np.r_[pw, 1.0, bigM], hi=d + bigM)
        add(np.arange(y, y + len(active)), 1.0, 1.0, 1.0)
        y += len(active)
        for t in window:
            ix = hour_edges[t]
            add(ix, edgepower[ix], hi=B[window].max() - 0.5 * request - rigid[t])
        for t in range(e.stop_hour, e.recovery_stop_hour):
            ix = hour_edges[t]
            add(np.r_[ix, z], np.r_[edgepower[ix], -0.25], hi=B[t] - rigid[t])
    A = sparse.coo_matrix((values, (rows, cols)), shape=(len(lbs), N)).tocsc()
    lb = np.array(lbs)
    ub = np.array(ubs)
    objective = np.zeros(N)
    objective[mo:bo] = 1.0
    objective[bo:zo] = 1.0
    objective[:E] = et * 1e-8
    start = time.monotonic()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Unrecognized options detected")
        sol = milp(
            objective,
            integrality=integrality,
            bounds=Bounds(lower, upper),
            constraints=LinearConstraint(A, lb, ub),
            options=dict(time_limit=time_limit, mip_rel_gap=1e-7, threads=1),
        )
    report = dict(
        solver_status=int(sol.status),
        solver_message=str(sol.message),
        seconds=time.monotonic() - start,
        variables=N,
        execution_edges=E,
        work_groups=G,
        rows=len(lbs),
        request_kw=request,
        miss_rate=miss_rate,
    )
    if sol.x is None:
        report["classification"] = "model_infeasible" if sol.status == 2 else "unresolved"
        return report, None, None
    x = sol.x
    ax = A @ x
    violation = max(
        float(np.maximum(lb - ax, 0).max()),
        float(np.maximum(ax - ub, 0).max()),
        float(np.maximum(lower - x, 0).max()),
        float(np.maximum(x - upper, 0).max()),
    )
    hour = pd.DataFrame(
        {"hour": range(T), "baseline_pcc_power_kw": B, "rigid_and_community_kw": rigid}
    )
    for cls in s.workload_classes:
        hour["execution_" + cls] = np.bincount(
            et, weights=x[:E] * (np.array(ec) == cls), minlength=T
        )
    hour["executed_gpu_h"] = np.bincount(et, weights=x[:E], minlength=T)
    hour["pcc_power_kw"] = rigid + np.bincount(et, weights=x[:E] * edgepower, minlength=T)
    metrics = []
    for e in events:
        active = slice(e.start_hour, e.stop_hour)
        rec = slice(e.stop_hour, e.recovery_stop_hour)
        window = slice(e.start_hour, e.recovery_stop_hour)
        reduction = np.maximum(B[active] - hour.pcc_power_kw.to_numpy()[active], 0.0)
        rebound = (
            np.maximum(hour.pcc_power_kw.to_numpy()[rec] - B[rec], 0.0).max() / reduction.max()
        )
        metrics.append(
            dict(
                event_id=e.event_id,
                mean_delivery=float(np.minimum(reduction, request).mean() / request),
                minimum_delivery=float(reduction.min() / request),
                rebound=float(rebound),
                window_relief=float(
                    (B[window].max() - hour.pcc_power_kw.to_numpy()[window].max()) / request
                ),
            )
        )
    missed = float(x[mo:bo].sum())
    terminal = float(x[bo:zo].sum())
    verified = (
        violation <= 1e-6
        and missed <= miss_rate * s.total_arrival_gpu_h + 1e-7
        and all(
            v["mean_delivery"] >= 0.95 - 1e-8
            and v["minimum_delivery"] >= 0.95 - 1e-8
            and v["rebound"] <= 0.25 + 1e-8
            and v["window_relief"] >= 0.5 - 1e-8
            for v in metrics
        )
    )
    report.update(
        classification="feasible_witness" if verified else "unresolved_residual",
        max_constraint_violation=violation,
        missed_gpu_h=missed,
        terminal_backlog_gpu_h=terminal,
        event_metrics=metrics,
    )
    witness = pd.DataFrame(
        {"group_index": ei, "hour": et, "job_class": ec, "execution_gpu_h": x[:E]}
    )
    groups["missed_gpu_h"] = x[mo:bo]
    groups["terminal_backlog_gpu_h"] = x[bo:zo]
    return report, hour, (witness, groups)
