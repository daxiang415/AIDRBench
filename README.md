# AIDRBench

## From nominal flexibility to firm AI data-centre flexibility in community energy systems

**面向社区能源系统的 AI 数据中心可靠需求响应、接入容量与计算债务评估平台**

> **Project thesis**<br>
> AI workload flexibility is not a fixed fraction of data-centre power. It is a state-, duration-, information- and history-dependent resource constrained by job deadlines, compute debt, recovery requirements and post-event rebound.

> **项目中心命题**<br>
> AI 数据中心的需求响应能力不是固定的“可移位负荷比例”，而是一种由任务队列、剩余期限、未来信息、历史调用和恢复需求共同决定、会被连续事件耗尽的有限资源。

---

## 1. Project objective

AIDRBench connects four layers that are usually studied separately:

1. **AI workload layer** — training and offline inference jobs with release times, GPU demand, runtime and deadlines;
2. **data-centre layer** — workload execution, rigid and flexible power, compute debt and recovery;
3. **community energy layer** — background demand, photovoltaic generation, battery storage and the point of common coupling;
4. **grid-service layer** — hosting capacity, peak shaving, firm demand response and repeated-event reliability.

The platform is designed to answer two related but distinct questions:

### Question A — Hosting-capacity planning

> Given a community load profile, photovoltaic capacity, battery storage and a transformer or PCC limit, how large an AI data centre can be connected without violating community constraints?

### Question B — Firm demand-response certification

> For an already connected AI data centre, how much power can be committed for a specified duration, notice time and reliability while respecting job deadlines, recovery and rebound constraints?

The project does **not** treat reinforcement learning as the scientific question. Rule-based control, model predictive control and reinforcement learning are evaluated as online realizations of a physically and statistically defined flexibility frontier.

---

## 2. Scientific narrative

Electricity-system studies often represent data-centre flexibility as a fixed proportion of demand:

\[
F^{\mathrm{nominal}}=\alpha P_{\mathrm{DC,peak}}.
\]

This representation ignores whether the underlying AI jobs can actually be delayed, for how long, how much deadline slack remains, how much work must be recovered later, and whether repeated dispatch creates a new peak.

AIDRBench therefore derives flexibility from the job queue rather than prescribing it from above:

\[
\text{job arrivals and deadlines}
\rightarrow
\text{feasible execution schedules}
\rightarrow
\text{data-centre power}
\rightarrow
\text{community PCC power}
\rightarrow
\text{firm flexibility certificate}.
\]

The intended paper-level conclusion is not that “AI data centres can respond to the grid.” It is:

> **Nominally shiftable AI load does not directly translate into firm grid flexibility. Deliverability depends on event duration, available information, workload state and prior dispatch, while deferred computation creates recovery obligations that can exhaust future flexibility.**

---

## 3. Main scientific contributions

### Contribution 1 — Job-derived firm-flexibility certificates

AIDRBench replaces an exogenous flexible-load fraction with a job-derived certificate:

\[
F^{\mathrm{firm}}(s,H,N,q),
\]

where:

- \(s\) is the state at commitment or event start;
- \(H\) is event duration;
- \(N\) is notice time;
- \(q\) is the required reliability;
- the state includes backlog, deadline distribution, remaining slack, previous dispatch and recovery status.

A candidate capacity \(R\) is successful only when all frozen protocol conditions are satisfied. Protocol v2 requires both event-average and interval-level delivery:

\[
\eta_e^{\mathrm{mean}}\geq0.95,
\]

\[
P_t^{\mathrm{control}}
\leq
P_t^{\mathrm{baseline}}-0.95R,
\qquad \forall t\in\mathcal E,
\]

along with service and recovery safeguards such as deadline-miss, rebound, window-relief and terminal-backlog limits.

The output is not a single “flexible percentage.” It is a **capacity–duration–notice–reliability–recovery surface**.

### Contribution 2 — Exact flexibility boundaries and nominal-to-deliverable gap decomposition

AIDRBench distinguishes four levels of flexibility:

\[
F^{\mathrm{nominal}}
\rightarrow
F^{\mathrm{PI}}
\rightarrow
F_q^{\mathrm{NA}}
\rightarrow
F_q^{\pi}.
\]

- \(F^{\mathrm{nominal}}\): static planning assumption;
- \(F^{\mathrm{PI}}\): perfect-information global optimum;
- \(F_q^{\mathrm{NA}}\): non-anticipative firm optimum under uncertainty;
- \(F_q^{\pi}\): reliable capacity implemented by online controller \(\pi\).

This creates three interpretable gaps:

\[
\Delta_{\mathrm{physical}}
=
F^{\mathrm{nominal}}-F^{\mathrm{PI}},
\]

\[
\Delta_{\mathrm{information}}
=
F^{\mathrm{PI}}-F_q^{\mathrm{NA}},
\]

\[
\Delta_{\mathrm{control}}
=
F_q^{\mathrm{NA}}-F_q^{\pi}.
\]

The decomposition reveals whether flexibility is lost because of physical job constraints, uncertainty about the future, or controller suboptimality.

The same framework is used to quantify the **additional community hosting capacity** enabled by AI workload flexibility under different PV and BESS portfolios.

### Contribution 3 — Compute-debt-driven exhaustion, recovery and resource interaction

Demand response does not remove AI work. It delays it:

\[
B_{t+1}=B_t+A_t-X_t-M_t,
\]

where \(B_t\) is backlog, \(A_t\) is newly released work, \(X_t\) is completed work and \(M_t\) is work that misses its deadline.

The energy obligation associated with deferred work is represented as compute debt:

\[
D_t^{\mathrm{comp}}
=
\sum_c e_c B_{c,t},
\]

where \(e_c\) is the class-specific energy required to complete one GPU-hour of workload class \(c\).

The causal chain studied by AIDRBench is:

\[
\text{DR curtailment}
\rightarrow
\text{compute debt}
\rightarrow
\text{reduced deadline slack}
\rightarrow
\text{lower subsequent flexibility}
\rightarrow
\text{recovery rebound}.
\]

The project further examines when AI flexibility, PV and BESS are complementary and when they merely substitute for one another.

---

## 4. Community system boundary

AIDRBench separates the background community from the data centre. A value such as “1 MW community with a 200 kW data centre” is therefore an **illustrative scenario**, not a universal physical fact.

Define:

- \(L_t\): background community gross demand, excluding the data centre;
- \(G_t^{\mathrm{PV}}\): photovoltaic generation used locally;
- \(P_t^{\mathrm{DC}}\): data-centre facility power;
- \(P_t^{\mathrm{ch}}\): battery charging power;
- \(P_t^{\mathrm{dis}}\): battery discharging power;
- \(P_t^{\mathrm{PCC}}\): grid import at the point of common coupling.

The community power balance is:

\[
\boxed{
P_t^{\mathrm{PCC}}
=
L_t
+
P_t^{\mathrm{DC}}
+
P_t^{\mathrm{ch}}
-
P_t^{\mathrm{dis}}
-
G_t^{\mathrm{PV}}
}
\]

subject to the transformer or PCC constraint:

\[
P_t^{\mathrm{PCC}}\leq K^{\mathrm{PCC}}.
\]

Where export is allowed, a lower bound or export limit is added. Where export is not allowed, PV curtailment becomes an explicit variable.

### Battery model

\[
SOC_{t+1}
=
SOC_t
+
\eta_{\mathrm{ch}}P_t^{\mathrm{ch}}\Delta t
-
\frac{P_t^{\mathrm{dis}}\Delta t}{\eta_{\mathrm{dis}}},
\]

\[
0\leq SOC_t\leq E^{\mathrm{BESS}},
\]

\[
0\leq P_t^{\mathrm{ch}},P_t^{\mathrm{dis}}\leq P^{\mathrm{BESS}}.
\]

Charge and discharge exclusivity can be enforced with binary variables in a MILP or approximated with a convex relaxation when simultaneous operation is economically dominated.

---

## 5. Per-unit scenario definition

To avoid tying conclusions to an arbitrary 1 MW example, the main analysis uses the PCC or transformer rating as the per-unit base:

\[
K^{\mathrm{PCC}}=1\ \mathrm{p.u.}
\]

and defines:

\[
\gamma_{\mathrm{DC}}
=
\frac{P_{\mathrm{DC,peak}}}{K^{\mathrm{PCC}}},
\]

\[
\gamma_{\mathrm{PV}}
=
\frac{P_{\mathrm{PV,rated}}}{K^{\mathrm{PCC}}},
\]

\[
\gamma_{\mathrm{B,P}}
=
\frac{P_{\mathrm{BESS}}}{K^{\mathrm{PCC}}},
\]

\[
h_{\mathrm{BESS}}
=
\frac{E_{\mathrm{BESS}}}{P_{\mathrm{BESS}}}.
\]

For a 1 MW transformer:

- \(\gamma_{\mathrm{DC}}=0.20\) corresponds to a 200 kW data centre;
- \(\gamma_{\mathrm{PV}}=0.50\) corresponds to 500 kW PV;
- \(\gamma_{\mathrm{B,P}}=0.10\) and \(h_{\mathrm{BESS}}=2\) h correspond to a 100 kW / 200 kWh battery.

The 200 kW data centre is retained only as a reference point. The principal planning problem treats data-centre capacity as an optimization variable.

### Stable denominators

Data-centre penetration must be defined relative to either:

1. the background-community gross peak; or
2. the PCC or transformer capacity.

It must **not** be defined relative to a net peak after PV and BESS optimization, because that denominator changes with the control policy.

---

## 6. Community portfolio matrix

The core causal comparison uses three binary dimensions:

- rigid or workload-flexible data centre;
- without or with PV;
- without or with BESS.

| Scenario | PV | BESS | Data-centre operation |
|---|---:|---:|---|
| A1 | No | No | Rigid |
| A2 | No | No | Workload-flexible |
| B1 | Yes | No | Rigid |
| B2 | Yes | No | Workload-flexible |
| C1 | No | Yes | Rigid |
| C2 | No | Yes | Workload-flexible |
| D1 | Yes | Yes | Rigid |
| D2 | Yes | Yes | Workload-flexible |

Each pair isolates the incremental value of AI workload flexibility under the same community assets.

For example:

\[
\Delta C_{\mathrm{AI}\mid\mathrm{PV+BESS}}
=
C_{\mathrm{flexDC}}^{\mathrm{PV+BESS}}
-
C_{\mathrm{rigidDC}}^{\mathrm{PV+BESS}}.
\]

---

## 7. Optimization problem A — Community hosting capacity

For each community portfolio, the planning problem is:

\[
\boxed{
C_{\mathrm{DC,max}}
=
\max P_{\mathrm{DC,peak}}
}
\]

subject to:

- PCC or transformer capacity;
- community power balance;
- PV availability and curtailment rules;
- BESS power, energy, efficiency and terminal-SOC conditions;
- AI workload capacity and conservation;
- release times and deadlines;
- allowed deadline-miss threshold;
- terminal backlog and recovery requirements.

The platform computes:

\[
C_{\mathrm{DC,max}}^{\mathrm{rigid}}
\]

and:

\[
C_{\mathrm{DC,max}}^{\mathrm{flex}}.
\]

The hosting-capacity gain is reported as both an absolute and relative value:

\[
\Delta C_{\mathrm{hosting}}
=
C_{\mathrm{DC,max}}^{\mathrm{flex}}
-
C_{\mathrm{DC,max}}^{\mathrm{rigid}},
\]

\[
M_{\mathrm{hosting}}
=
\frac{C_{\mathrm{DC,max}}^{\mathrm{flex}}}
{C_{\mathrm{DC,max}}^{\mathrm{rigid}}}.
\]

This problem avoids demand-response baseline ambiguity because it uses an absolute PCC constraint.

---

## 8. Optimization problem B — Firm demand-response capacity

For a fixed community portfolio and connected data-centre size, the DR problem is:

\[
\boxed{
F^{\mathrm{firm}}
=
\max R
}
\]

subject to the protocol-defined event, service and recovery constraints.

### Baseline integrity

PV and BESS introduce a serious baseline-gaming risk. A battery must not be allowed to charge artificially before or during the baseline and then claim the resulting reduction as DR.

The no-DR baseline and DR evaluation must therefore use:

- the same background load, PV and AI job realization;
- the same initial battery SOC;
- the same terminal-SOC requirement;
- the same terminal-backlog and service requirements;
- the same data-centre power model;
- a baseline schedule frozen before the locked evaluation;
- no re-optimization of the baseline after observing the DR outcome.

For capacity-limit studies, an absolute PCC limit is preferred. For event-delivery studies, the counterfactual baseline must be explicit, versioned and auditable.

---

## 9. Perfect-information, non-anticipative and controller frontiers

### 9.1 Perfect-information frontier

The perfect-information optimizer sees the full future trajectory:

- workload arrivals and deadlines;
- community demand and PV;
- event timing and duration;
- recovery horizon.

It returns:

\[
F_s^{\mathrm{PI}}(H),
\]

which is a model-internal global optimum and a clairvoyant upper bound.

### 9.2 Non-anticipative firm frontier

A realistic commitment must be made before all future uncertainty is known. Scenario-tree or two-stage formulations impose non-anticipativity:

\[
x_{c,t,s}=x_{c,t,s'}
\]

for workload class \(c\) and scenarios that are indistinguishable at time
\(t\). PI, non-anticipative and hosting models all use the same calibrated
class-specific power coefficients as the online environment:

\[
P_t^{\mathrm{DC}}
=
P_{\mathrm{fixed}}
+
\sum_c e_c x_{c,t}.
\]

A chance-constrained formulation may introduce failure variables \(z_s\):

\[
\sum_s z_s\leq(1-q)|\mathcal S|.
\]

The resulting capacity is:

\[
F_q^{\mathrm{NA}}(H,N).
\]

### 9.3 Controller-achieved capacity

For rule-based, MPC or RL controller \(\pi\), the held-out certified capacity is:

\[
F_q^{\pi}(H,N).
\]

Controllers are compared by their ability to realize the non-anticipative frontier:

\[
\eta_{\pi}
=
\frac{F_q^{\pi}}{F_q^{\mathrm{NA}}}.
\]

Reward is a training mechanism, not a paper-level performance metric.

---

## 10. AI flexibility, PV and BESS: complementarity or substitution

PV, BESS and AI workload flexibility do not always provide independent value.

### PV and AI workload flexibility

During PV-rich hours, flexible AI jobs can be advanced:

\[
\text{PV surplus}
\rightarrow
\text{early computation}
\rightarrow
\text{more deadline slack at evening peak}.
\]

This may simultaneously reduce PV curtailment and increase evening firm flexibility.

### BESS and AI workload flexibility

During short peak events, BESS discharge and workload deferral may substitute for one another. During long events, they can become complementary because they have different limitations:

- BESS is limited by stored energy;
- AI flexibility is limited by deadline slack and compute debt.

BESS can also suppress the recovery rebound caused by deferred computation.

### Interaction metric

For a generic outcome \(Y\), such as hosting capacity, define:

\[
S_{\mathrm{AI,BESS}}
=
Y_{\mathrm{AI+BESS}}
-
Y_{\mathrm{AI}}
-
Y_{\mathrm{BESS}}
+
Y_0.
\]

- \(S>0\): complementarity;
- \(S<0\): substitution;
- \(S\approx0\): approximately additive value.

The same definition is used for AI–PV, PV–BESS and higher-order interactions.

---

## 11. Workload and power models

### 11.1 Main fluid model

The main large-scale analysis uses a preemptive fluid workload model:

- work is measured in GPU-hours;
- jobs can be fractionally served over time;
- EDF-compatible deadline conservation is enforced;
- the resulting optimization is an LP when the power and storage models remain linear.

This model supports large scenario ensembles and exact global optimization.

### 11.2 Job-level MILP sensitivity

A job-level MILP is used to quantify how much the fluid model overestimates flexibility when adding:

- integer GPU allocation;
- indivisible execution blocks;
- non-preemptive jobs;
- checkpoint and restart overhead;
- tensor-parallel group constraints;
- migration restrictions;
- binary BESS charge/discharge decisions.

The relaxation gap is:

\[
\Delta F_{\mathrm{granularity}}
=
F^{\mathrm{fluid\ LP}}
-
F^{\mathrm{job\ MILP}}.
\]

### 11.3 Class-aware execution

To connect measured workload power to the queue, the production model should retain workload class by deadline:

```text
remaining_gpu_h[class_name, deadline_index]
```

and return:

```text
executed_gpu_h_by_class
```

for training and offline inference separately. A single aggregate queue is acceptable only when the paper explicitly uses one effective flexible-workload class.

---

## 12. Repeated-event exhaustion

The main repeated-event quantity is the largest common capacity that can be sustained across all events:

\[
F_{\mathrm{sustainable}}(N,H,g)
=
\max R,
\]

where:

- \(N\) is the number of dispatches;
- \(H\) is event duration;
- \(g\) is the inter-event recovery gap.

The exhaustion ratio is:

\[
E(N,H,g)
=
1-
\frac{F_{\mathrm{sustainable}}(N,H,g)}
{F_{\mathrm{fresh}}(H)}.
\]

Repeated-event studies use prefix experiments:

```text
run event 1 and evaluate event 1
run events 1–2 and evaluate event 2
run events 1–3 and evaluate event 3
run events 1–4 and evaluate event 4
```

This preserves the influence of past events without allowing future events to contaminate earlier event labels.

---

## 13. Frozen matched scenarios

Duration comparisons must be performed on identical exogenous trajectories.

A frozen scenario contains:

```text
background community demand
PV generation
AI job arrivals and deadlines
event start and notice
initial battery SOC
no-DR baseline
power-model identifier and hash
scenario identifier and hash
```

Only event duration is changed when constructing the power–endurance frontier.

Required invariants include:

\[
F_s^{\mathrm{PI}}(H+1)
\leq
F_s^{\mathrm{PI}}(H),
\]

for nested event windows, and:

\[
F_s^{\mathrm{PI}}(H)
\leq
\Delta P_{\mathrm{flex,max}}.
\]

Random streams for community demand, workload and events must be separated so that changing event duration cannot alter the underlying scenario.

---

## 14. Statistical certification protocol

### Main firm-capacity certificate

The primary certificate fixes a repeated-event program keyed by duration,
notice, event anchors and the declared timing-jitter distribution. Each episode
is one independent Bernoulli trial and passes only when **every event in that
episode** satisfies delivery, minimum-interval delivery, deadline, rebound,
window-relief and terminal-backlog criteria. Event rows remain auditable, but
they are never counted as independent statistical trials.

### Validation stage

Validation data may be used to:

- select candidate capacity;
- select model checkpoint;
- tune controller parameters;
- choose a preregistered reward or constraint variant.

### Locked test stage

After freezing all choices, the locked OOD set evaluates one fixed capacity. The test set must not be used for further binary search or model selection.

A one-sided lower confidence bound is reported:

\[
\underline p_{0.95}(R)\geq0.95.
\]

An isolated-event certificate remains available only as an explicitly labelled
diagnostic. Exhaustion products use the same episode-level joint-success rule,
because events within one episode are dependent.

---

## 15. Community-level metrics

AIDRBench reports more than event-period peak reduction.

### Grid and transformer metrics

\[
O_{\max}
=
\max_t(P_t^{\mathrm{PCC}}-K^{\mathrm{PCC}})_+,
\]

\[
O_E
=
\sum_t(P_t^{\mathrm{PCC}}-K^{\mathrm{PCC}})_+\Delta t,
\]

\[
N_{\mathrm{overload}}
=
\sum_t\mathbf 1[P_t^{\mathrm{PCC}}>K^{\mathrm{PCC}}].
\]

### DR metrics

- requested capacity;
- event-average delivery ratio;
- minimum interval delivery ratio;
- interval-delivery failure count;
- event-period peak relief;
- event-plus-recovery-window peak relief;
- rebound peak and rebound ratio;
- recovery time.

### AI service metrics

- completed GPU-hours;
- deadline-miss GPU-hours and rate;
- terminal backlog;
- compute debt;
- workload-class completion;
- action switching or scheduling volatility.

### DER metrics

- PV self-consumption;
- PV curtailment;
- BESS energy throughput;
- equivalent cycles;
- terminal SOC deviation;
- BESS contribution to event delivery and rebound suppression.

### Planning metrics

- rigid and flexible data-centre hosting capacity;
- absolute hosting-capacity gain;
- hosting-capacity multiplier;
- capacity-deficit coverage ratio;
- proportion of constrained community scenarios fully rescued by flexibility.

---

## 16. Experimental design

### 16.1 Core reference portfolio

The initial explanatory case uses normalized values rather than treating them as universal:

```yaml
community:
  pcc_capacity_pu: 1.0

datacenter:
  peak_capacity_pu: 0.20

pv:
  enabled: true
  rated_capacity_pu: 0.50

battery:
  enabled: true
  power_capacity_pu: 0.10
  duration_hours: 2
```

For a 1 MW PCC, this example corresponds to 200 kW DC, 500 kW PV and 100 kW / 200 kWh BESS.

### 16.2 Core 2 × 2 × 2 causal matrix

The eight portfolio combinations are evaluated first to identify the incremental value of AI flexibility.

### 16.3 Response-surface analysis

Recommended normalized ranges are:

\[
\gamma_{\mathrm{DC}}\in\{0.05,0.10,0.20,0.30,0.40\},
\]

\[
\gamma_{\mathrm{PV}}\in[0,1.0],
\]

\[
\gamma_{\mathrm{B,P}}\in[0,0.20],
\]

\[
h_{\mathrm{BESS}}\in\{1,2,4\}\ \mathrm{h}.
\]

A sparse design or Latin-hypercube sample is preferred over a full Cartesian product.

### 16.4 Flexibility variables

- event duration: 1, 2, 3, 4, 6 and 8 h;
- notice: 0, 2 and 6 h;
- reliability: 90%, 95% and 99%;
- workload utilization: low, reference and high;
- deadline policy: loose, reference and tight;
- event count and recovery gap;
- community headroom or capacity deficit.

---

## 17. Controller benchmark

Controllers are evaluated after the physical and statistical frontiers are stable.

Recommended order:

1. no control;
2. threshold rule;
3. EDF / valley filling;
4. perfect-information LP oracle;
5. deterministic rolling MPC;
6. stochastic or robust MPC;
7. DQN, PPO and SAC as learning-based online policies.

RL is justified as an online approximation or model-free controller, not because the current hourly fluid problem is intrinsically intractable.

The principal controller outputs are:

```text
certified capacity
fraction of non-anticipative frontier achieved
deadline and rebound failures
solve or inference time
robustness to model mismatch
```

---

## 18. Hardware grounding

The four-GPU server is an empirical anchor, not a physical representation of an entire MW-scale data centre.

Hardware experiments should measure:

- wall- or PDU-level idle power;
- workload-class active and incremental power;
- runtime and completed GPU-hours;
- energy per completed GPU-hour;
- mixed-workload interference;
- checkpoint, pause and restart overhead;
- power response under selected execution levels.

The calibration workflow is:

```text
screening measurements
→ fitted node power model
→ held-out validation
→ uncertainty distribution
→ evidence-labelled virtual-fleet scaling
→ community and DR optimization
```

A formal calibration artifact should contain:

```text
schema version
hardware and topology identifier
measurement method
workload classes
parameter estimates and confidence intervals
held-out prediction error
evidence class
artifact SHA-256
```

Formal configurations must fail when the requested calibration artifact is unavailable. Fallback parameters are permitted only in explicitly labelled smoke or sensitivity scenarios.

Hardware uncertainty is propagated through the flexibility and hosting-capacity results rather than hidden behind one deterministic parameter set.

The executable artifact interface is:

```yaml
hardware:
  calibration_artifact: data/calibration/rtx6000pro_4gpu_v1.yaml
  require_calibration_artifact: true  # mandatory for a formal run
  calibration_power_case: nominal     # lower_ci | nominal | upper_ci
```

`aidrbench calibrate validate-artifact --artifact <path>` verifies the strict
schema and its self-contained SHA-256 before the environment consumes it.
For each calibrated power case, freeze fresh scenarios before running the PI,
non-anticipative, certification or hosting-capacity workflows: a frozen
artifact stores both the resulting power-model fingerprint and calibration
artifact SHA-256.

---

## 19. Proposed package structure

```text
src/aidrbench/
├── community/
│   ├── scenario.py
│   ├── site_balance.py
│   ├── pv.py
│   ├── battery.py
│   ├── portfolio.py
│   └── hosting_capacity.py
├── workloads/
│   ├── deadline_buckets.py
│   └── class_aware_queue.py
├── datacenter/
│   ├── hardware.py
│   ├── power_model.py
│   ├── calibration_artifact.py
│   └── scaling.py
├── optimization/
│   ├── frozen_scenario.py
│   ├── perfect_information_lp.py
│   ├── job_level_milp.py
│   ├── nonanticipative_firm.py
│   ├── hosting_capacity.py
│   └── gap_decomposition.py
├── controllers/
│   ├── rules.py
│   ├── mpc.py
│   └── sb3.py
├── evaluation/
│   ├── firm_flexibility.py
│   ├── certification.py
│   ├── repeated_events.py
│   ├── community_metrics.py
│   └── statistics.py
└── hil/
    ├── actuator_client.py
    ├── workload_client.py
    └── watchdog.py
```

---

## 20. Planned CLI workflow

The following command names describe the intended workflow; they should be implemented or mapped to existing commands before public release.

```bash
# Validate data, configs and the frozen protocol
aidrbench protocol-check \
  --manifest data/manifests/hourly_experiment_protocol_v2.yaml

# Freeze matched exogenous scenarios
aidrbench scenario freeze \
  --config configs/scenarios/reference_portfolio.yaml \
  --seeds 20000 20001 20002 \
  --output data/frozen/reference_validation/

# Compute perfect-information power–duration frontiers
aidrbench optimize pi-frontier \
  --scenarios data/frozen/reference_validation/ \
  --durations 1 2 3 4 6 8 \
  --output results/pi_frontier/

# Compute a chance-constrained causal lower bound. The default is a declared
# coarse observation-partition tree: current net load, a six-hour forecast,
# current arrivals, and a DR event only after notice. Rare cells are merged.
# It remains a restricted lower bound, not the unrestricted scenario-tree optimum.
aidrbench optimize non-anticipative-firm \
  --scenarios data/frozen/reference_validation/ \
  --durations 1 2 3 4 6 8 \
  --reliability-target 0.95 \
  --output results/non_anticipative_frontier/

# Optional stricter sensitivity: one common execution schedule across all
# successful frozen scenarios at every hour.
aidrbench optimize non-anticipative-firm \
  --scenarios data/frozen/reference_validation/ \
  --durations 1 2 3 4 6 8 \
  --reliability-target 0.95 \
  --information-structure common_open_loop \
  --output results/non_anticipative_open_loop/

# Compute portfolio-specific hosting capacity
aidrbench optimize hosting-capacity \
  --scenarios data/frozen/reference_validation/ \
  --portfolio configs/community/pv_bess.yaml \
  --dc-operation matrix \
  --output results/hosting_capacity/

# Select capacity on validation data, then freeze it
aidrbench certify select \
  --controller mpc \
  --durations 1 2 3 4 6 8 \
  --notices 0 2 4 6 \
  --protocol-manifest data/manifests/hourly_experiment_protocol_v2.yaml \
  --output results/selected_capacity/

# Evaluate the fixed capacity on locked OOD episodes
aidrbench certify locked-test \
  --selection results/selected_capacity/selection.json \
  --protocol-manifest data/manifests/hourly_experiment_protocol_v2.yaml \
  --output results/locked_certificate/

# Evaluate repeated-event exhaustion
aidrbench stress-test sustainable-capacity \
  --events 1 2 3 4 \
  --durations 1 2 4 6 \
  --gaps 2 4 8 12 24 \
  --output results/repeated_events/
```

---

## 21. Current status and interpretation

The current local development status is:

- both mean-event and minimum-interval delivery criteria are implemented;
- the formal base case now distinguishes a **800 kW background-community peak**, **1 MW PCC rating**, and **200 kW target DC peak**;
- exact discrete sizing selects 111 four-GPU nodes, giving a 200.287 kW realised full-pool facility peak;
- PCC capacity is enforced at every hourly interval and is present in observations, planning snapshots, oracle constraints and result metadata;
- `aidrbench scenario freeze` writes hash-verified community, PV, arrivals, event anchors, baseline and power-model artifacts;
- `aidrbench optimize pi-frontier` evaluates a single-event, frozen-scenario perfect-information duration frontier and checks physical and monotonicity invariants;
- `aidrbench optimize non-anticipative-firm` implements two declared causal lower-bound policy classes over frozen scenarios: a strict common open-loop schedule and, by default, a coarse observation-partition tree using only current net load, limited forecast, released work and notified DR events. The latter merges rare observation cells, deliberately omits endogenous queue state, and is therefore not the unrestricted scenario-tree frontier;
- `aidrbench optimize hosting-capacity` implements an absolute-PCC, perfect-information planning bound for the eight rigid/flexible × PV × BESS portfolios. It enforces PV use/curtailment, BESS SOC, power and terminal-SOC constraints, and scales workload release/deadline constraints with the candidate DC size; BESS is not yet part of the online DR environment;
- the hourly EDF queue now retains training and offline-inference work classes and rollout Parquet files report their arrival, execution, expiry and backlog separately;
- planning snapshots retain workload class, and PI, non-anticipative and hosting-capacity optimizers use class-indexed execution and calibrated class-specific power rather than an average affine slope;
- class-aware PCC power and compute debt use a versioned, SHA-256-verified calibration artifact when configured. `lower_ci`, `nominal` and `upper_ci` power cases are explicit scenario settings. No measured four-GPU calibration artifact has yet been collected, so formal runs must set `hardware.require_calibration_artifact: true` and will correctly fail until one is supplied;
- formal train, validation and locked-test configs now require `data/calibration/rtx6000pro_4gpu_v1.yaml`; unknown or ambiguous hardware keys are rejected, and the hourly environment rejects non-one-hour timesteps until queue aging is generalized;
- controller certification uses repeated-event joint episode success and keys each selected capacity by duration, notice and event sequence. Validation searches all configured notice choices, while locked test only evaluates the frozen capacities;
- deterministic MPC now obeys release-time causality for estimated future arrivals; a robust-MPC baseline uses an explicit historical-arrival uncertainty envelope. Benchmark outputs label every controller's information structure and action-time distribution, while the full-horizon oracle remains explicitly separate as a perfect-information bound;
- GitHub Actions runs `pytest`, `ruff check .` and `mypy src`; a clean-install smoke test verifies HiGHS/CVXPY and Parquet availability;
- the locked test set has not been used after this scenario-semantics revision.

The earlier 63.52 kW and 68.86 kW diagnostics used the previous 153.37 kW virtual-DC sizing and non-frozen duration comparisons. They are therefore retained only as historical development observations and must not be used as a current flexibility, community-DR or certificate result. Similarly, policies trained against the earlier `firm_v4` observation interface are incompatible with the current `firm_v5` PCC-normalized environment and are diagnostic only.

---

## 22. Immediate implementation priorities

### Priority 1 — Correct scenario semantics and sizing

- distinguish background-community demand from total PCC demand;
- define DC, PV and BESS sizes relative to stable per-unit bases;
- replace approximate automatic node sizing with a search using the final power model;
- record target and actual data-centre peaks;
- retain hourly resolution until all time-indexed components support sub-hourly steps.

### Priority 2 — Freeze matched scenarios

- separate random streams for community, workload and event generation;
- store immutable scenario artifacts and hashes;
- vary only event duration in duration experiments;
- add monotonicity and physical-upper-bound tests.

### Priority 3 — Separate the three capacity layers

- rename oracle output as `perfect_information_capacity_kw`;
- implement the non-anticipative firm optimization;
- reserve `certified_capacity_kw` for locked, causal controller evaluation.

### Priority 4 — Add community portfolios

- implement battery SOC and charge/discharge decisions;
- make PV availability and curtailment explicit;
- add hosting-capacity optimization;
- compare the eight rigid/flexible × PV × BESS portfolios.

### Priority 5 — Repair statistical certification

- [x] count independent episodes, not event rows, as Bernoulli trials;
- [x] require all events in a repeated-event episode to succeed jointly;
- [x] key capacities by duration, notice and event sequence;
- [x] select capacity on validation data only and evaluate only the frozen value on locked test;
- [x] report one-sided lower confidence bounds;
- [ ] run the formal certificate only after measured calibration and scenario re-freezing.

### Priority 6 — Connect workload class to measured power

- [x] retain training and offline-inference classes in the deadline queue;
- [x] output execution by class;
- [x] consume a versioned, SHA-256-verified hardware-calibration artifact when configured;
- [x] select `lower_ci`, `nominal` or `upper_ci` power cases from that artifact and record the selected case with every rollout;
- [x] use class-indexed execution and class-specific power in PI, non-anticipative and hosting optimizers;
- [ ] collect the real four-GPU measurements, fit and validate the first `measured` artifact, then re-freeze all formal scenarios for the three power cases.

### Priority 7 — Benchmark online controllers

- [x] validate deterministic causal MPC and a robust arrival-envelope MPC;
- [x] use shared physical rollouts and matched seeds; record each controller's declared information structure and action time, rather than silently comparing a perfect-information oracle with causal controllers;
- [ ] make the online controller observation interface strictly identical across rule, MPC and RL policies (the current causal MPC consumes the auditable `control_state`, while SB3 policies consume the normalized observation);
- [ ] retrain RL only after the environment, reward, protocol and measured calibration artifact are frozen.

---

## 23. Intended main results

The paper-facing result sequence is:

### Result 1 — Job-derived power–duration frontier

Show how \(F^{\mathrm{PI}}(H)\) transitions from a dynamic-power-limited region to a deadline- and compute-debt-limited region.

### Result 2 — Nominal-to-firm gap decomposition

Quantify physical, information and controller gaps between static planning assumptions and realized causal flexibility.

### Result 3 — Community hosting-capacity gain

Compare rigid and flexible data-centre hosting capacity under no-DER, PV, BESS and PV+BESS portfolios.

### Result 4 — Compute-debt-driven exhaustion

Show how repeated dispatch reduces sustainable capacity and increases recovery requirements.

### Result 5 — PV/BESS interaction

Identify where AI flexibility complements PV and storage and where it is largely substitutable.

### Result 6 — Online realization and hardware uncertainty

Measure how closely MPC and RL approach the non-anticipative frontier and how hardware-model uncertainty affects the conclusions.

---

## 24. Proposed main figures

1. **Measurement-to-community framework** — AI jobs, calibrated node power, virtual fleet, PV/BESS community and PCC certificate.
2. **Power–duration frontier** — dynamic power ceiling, perfect-information frontier and job-level MILP sensitivity.
3. **Nominal-to-firm decomposition** — physical, information and controller gaps.
4. **Community hosting-capacity map** — DC penetration versus network headroom for the eight portfolios.
5. **Compute debt and repeated-event exhaustion** — backlog, low-percentile slack, sustainable capacity and rebound.
6. **PV/BESS interaction and controller realization** — complementarity metrics, locked-test reliability and uncertainty intervals.

---

## 25. Scope and exclusions

The main version studies:

- hourly temporal workload shifting;
- training and offline-inference flexibility;
- community PCC or transformer capacity;
- PV and battery interaction;
- job deadlines, compute debt and recovery;
- perfect-information, non-anticipative and online control frontiers;
- repeated-event exhaustion;
- node-measurement-grounded virtual-fleet scaling.

The main version does not claim to model:

- second-level frequency regulation;
- voltage, reactive power or full distribution power flow in the core model;
- complete cooling-plant dynamics;
- UPS transients;
- arbitrary cross-region workload migration;
- an experimentally demonstrated MW-scale data centre;
- a new reinforcement-learning theory.

A standard radial feeder may be added as an external validation case after the PCC-level conclusions are stable.

---

## 26. Reproducibility requirements

Every formal result must record:

```text
git commit
scenario hash
community and workload data hashes
power-model or calibration-artifact hash
protocol version
observation and reward versions
controller and checkpoint identifier
training seed
evaluation seeds
candidate capacity
event duration and notice
PV and BESS portfolio
success definition and failure reasons
```

Raw external data remain read-only and outside Git. Processed artifacts, split manifests and hashes are versioned. Historical models that use incompatible observation or reward versions are diagnostics only.

---

## 27. Working paper title and contribution statement

### Working title

**Job-derived flexibility envelopes reveal compute-debt limits and community hosting value of AI data centres**

### Three-sentence contribution statement

> First, we replace exogenous flexible-load fractions with a job-derived firm-flexibility certificate that jointly accounts for interval delivery, workload deadlines, recovery and rebound.

> Second, we establish perfect-information and non-anticipative frontiers to decompose nominal flexibility into physical, information and control gaps, and translate these frontiers into community data-centre hosting capacity under PV and battery portfolios.

> Third, we show how demand-response dispatch accumulates compute debt, making AI flexibility exhaustible and recovery-dependent under repeated events.

---

## 28. Citation and licence

The repository is under active research development. A formal software licence, author list, archived release and citation file must be added before public benchmark release.

Absolute priority or “first-of-its-kind” claims are not used without a completed systematic literature review.
