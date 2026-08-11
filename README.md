# AIDRBench

**A hardware-calibrated experimental platform for demand-responsive AI data centers**  
**面向电网需求响应的 AI 数据中心控制实验平台**

> 文档状态：实施规范（implementation specification）  
> 版本：v0.1-spec  
> 日期：2026-08-11  
> 目标服务器：Ubuntu 24.04 LTS，4 × NVIDIA RTX PRO 6000（运行前用 `nvidia-smi -L` 核对准确 SKU）

---

## 0. 这份 README 的用途

这份文档定义了一个可直接在四卡服务器上实施的研究平台，包括：

- 数据从哪里取得、如何清洗和切分；
- AI 数据中心需求响应环境如何建模；
- 四张 GPU 如何分工并完成硬件标定；
- Rule-based、MPC、PPO、A2C、DQN 如何在同一环境下运行；
- 如何从快速仿真过渡到 server-in-the-loop（服务器在环）验证；
- 如何保证实验公平、可复现和不过度宣称。

本 README **不是在声称代码已经完成**。其中分为两类命令：

1. **可立即执行的命令**：服务器检查、Docker/vLLM、数据下载、AIPerf、DCGM 等；
2. **目标 CLI**：以 `uv run aidrbench ...` 或 `python -m aidrbench...` 开头，表示仓库需要按本文规范实现的接口。

推荐先把本文件放到服务器仓库根目录并命名为 `README.md`，再按第 34 节的 P0–P6 顺序实施。

---

## 1. 项目定位

AIDRBench 的第一篇论文定位是：

> **创建一个硬件标定、可复现的 AI 数据中心需求响应实验平台，并在相同工作负荷和 DR 事件下，对比无控制、规则控制、MPC 和若干标准强化学习算法，验证 AI 计算负荷能否可靠提供需求响应。**

第一阶段不是提出新的强化学习理论，也不是证明某一种 RL 必然优于 MPC。核心贡献应是：

1. 一个轻量级、算法无关的 Gymnasium 环境；
2. 对在线 LLM 推理与可延迟批处理的联合表示；
3. 基于四张 RTX PRO 6000 实测数据的功率—性能—服务质量模型；
4. Rule-based、MPC 和标准 RL 的统一 benchmark；
5. 仿真与真实服务器使用相同动作和 KPI 接口；
6. 对需求响应能力、SLA、任务期限和事件后 rebound 的系统评价。

### 1.1 第一篇论文明确不做的内容

V0 不建立以下复杂模块：

- OpenDSS、节点电压、无功功率和线路潮流；
- 多栋建筑、EV、储能和数据中心的多智能体博弈；
- 完整冷冻水系统或海水冷却物理模型；
- 动态迁移 tensor-parallel 实例；
- 在线探索式 RL 直接控制真实服务器；
- 安全强化学习的新算法。

这些内容可在平台稳定后作为 V1/V2 扩展。

---

## 2. 核心研究问题

### RQ1：可交付性

当社区或聚合商要求数据中心在 15–120 分钟内降低 10%–30% 功率时，四 GPU 节点或其虚拟集群能够实际降低多少功率、持续多久、跟踪误差多大？

### RQ2：服务代价

需求响应是否导致：

- 在线推理 TTFT、TPOT 或端到端延迟恶化；
- 请求队列过长；
- 批处理任务错过期限；
- 事件结束后的恢复峰值高于原峰值？

### RQ3：控制方法比较

在相同观察量、动作集合、预测信息和评估事件下：

- Rule-based 是否已经足够；
- MPC 在有预测时是否更稳定；
- PPO/A2C/DQN 是否能在随机请求和未知事件中获得更好的长期折中；
- 各方法在仿真排序与真实服务器排序之间是否一致？

### RQ4：泛化与缩放

在不同社区负荷、请求强度、模型规模、DR 持续时间和虚拟节点数下，控制器是否仍能工作？单节点实测规律放大到虚拟数据中心时有哪些误差？

---

## 3. 系统边界：用公共连接点而不是完整配电网

V0 将社区和数据中心看作接在同一个公共连接点（PCC）后的聚合负荷：

\[
P_t^{\mathrm{PCC}}
=
P_t^{\mathrm{community}}
-
P_t^{\mathrm{PV}}
+
P_t^{\mathrm{DC}}.
\]

需求响应可以采用两种等价接口。

### 3.1 动态功率上限

\[
P_t^{\mathrm{PCC}} \le \overline{P}_t^{\mathrm{PCC}}.
\]

数据中心在该时刻的可用预算为：

\[
P_t^{\mathrm{budget}}
=
\overline{P}_t^{\mathrm{PCC}}
-P_t^{\mathrm{community}}
+P_t^{\mathrm{PV}}.
\]

### 3.2 指令型削减

聚合商要求相对基线削减：

\[
\Delta P_t^{\mathrm{delivered}}
=
P_t^{\mathrm{baseline}}-P_t^{\mathrm{PCC}},
\]

并希望：

\[
\Delta P_t^{\mathrm{delivered}}
\ge
\Delta P_t^{\mathrm{requested}}.
\]

V0 默认采用**事件型需求响应**，而不是仅依赖实时电价，因为它有明确的功率目标、持续时间和履约指标，也更适合真实服务器验证。

---

## 4. 平台总体架构

```text
                         ┌───────────────────────────────┐
Community load / PV ───► │  PCC and DR event model       │
                         │  limit, target, notice, timer │
                         └──────────────┬────────────────┘
                                        │
BurstGPT trace ───► Inference queue ────┤
                                        │
Alibaba / synthetic jobs ─► Batch queue ┤
                                        ▼
                          ┌─────────────────────────────┐
                          │ Common controller interface │
                          │ No-control / RBC / MPC      │
                          │ DQN / A2C / PPO             │
                          └──────────────┬──────────────┘
                                         │ discrete action
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
          ┌──────────────────────┐                ┌──────────────────────┐
          │ Emulator backend     │                │ Server-in-loop       │
          │ measured surrogates  │                │ real 4-GPU server    │
          └──────────┬───────────┘                └──────────┬───────────┘
                     │                                       │
                     └─────────────── KPI recorder ──────────┘
                         power, energy, SLA, deadlines,
                         DR tracking, rebound, switching
```

平台必须让 emulator 和 hardware backend 实现同一接口：

```python
backend.reset(scenario)
backend.apply_action(action)
backend.advance(dt_seconds)
backend.get_state()
backend.get_metrics()
backend.close()
```

这样控制器不需要知道自己控制的是代理模型还是真实服务器。

---

## 5. 四张 GPU 的 V0 分工

动态改变 tensor parallel、频繁卸载模型或在 GPU 池之间迁移服务会引入长时间重启、显存碎片和不稳定性。V0 使用固定分区：

| GPU | 角色 | 是否始终保留模型 | 可控变量 |
|---|---|---:|---|
| 0–1 | 在线推理池 | 是 | inference power cap |
| 2–3 | 可延迟批处理池 | 是或预加载 | active batch GPU 数、batch power cap |

### 5.1 在线推理池

- 运行一个 vLLM 服务；
- 正式实验可以采用 2-GPU tensor parallel；
- 在线请求不得静默丢弃；未及时处理的请求进入队列；
- V0 不动态改变 `tensor_parallel_size`；
- 推理 GPU 始终处于可服务状态。

### 5.2 批处理池

第一版建议使用**离线 LLM 批量推理**作为可延迟任务，而不是立即使用大模型训练：

- 可中断或停止新任务派发；
- 任务容易表示为 token/work units；
- 不需要先解决训练 checkpoint 和恢复一致性；
- 可在后续扩展到 LoRA/QLoRA 微调和训练作业。

当 `active_batch_gpus = 0` 时，不向批处理 GPU 派发新任务，但模型可保持加载；因此 GPU 仍有空闲功耗，不能把功率直接设为零。

### 5.3 虚拟数据中心缩放

单台四卡服务器只有 kW 级功率。社区级仿真使用：

\[
P_t^{\mathrm{DC,virtual}}
=
N_{\mathrm{node}} P_t^{\mathrm{node}},
\]

其中 `N_node` 是相同节点的虚拟复制数。建议使基线数据中心负荷占 PCC 峰值的 10%、25% 或 40%，而不是任意指定一个过大的绝对容量。

真实服务器验证固定 `N_node = 1`。论文必须明确：

- 单节点响应是真实测量；
- MW 级结果是同构节点缩放情景；
- 缩放不自动包含网络、冷却和机架间异质性。

---

## 6. 推荐仓库结构

```text
AIDRBench/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
├── CITATION.cff
├── LICENSE
│
├── configs/
│   ├── env/
│   │   ├── v0_discrete.yaml
│   │   └── v1_continuous.yaml
│   ├── data/
│   │   ├── burstgpt.yaml
│   │   ├── alibaba_v2020.yaml
│   │   └── community.yaml
│   ├── controller/
│   │   ├── no_control.yaml
│   │   ├── rule_based.yaml
│   │   ├── mpc.yaml
│   │   ├── dqn.yaml
│   │   ├── a2c.yaml
│   │   └── ppo.yaml
│   ├── hardware/
│   │   └── four_gpu_node.yaml
│   └── experiment/
│       ├── smoke.yaml
│       ├── simulation_main.yaml
│       └── hil_main.yaml
│
├── data/
│   ├── raw/                 # 不提交 Git
│   ├── interim/             # 不提交 Git
│   ├── processed/           # 小型清洗结果可提交或发布
│   └── manifests/           # URL、版本、hash、license、日期
│
├── external/                # 上游仓库，只读
├── models/
│   ├── hardware_surrogates/
│   └── rl_checkpoints/
│
├── src/aidrbench/
│   ├── __init__.py
│   ├── cli.py
│   ├── envs/
│   │   ├── community_dc_env.py
│   │   ├── wrappers.py
│   │   └── registration.py
│   ├── data/
│   │   ├── burstgpt.py
│   │   ├── alibaba.py
│   │   ├── community.py
│   │   └── splits.py
│   ├── workloads/
│   │   ├── inference_queue.py
│   │   ├── deadline_queue.py
│   │   └── request_generator.py
│   ├── datacenter/
│   │   ├── emulator.py
│   │   ├── power_model.py
│   │   └── scaling.py
│   ├── controllers/
│   │   ├── base.py
│   │   ├── no_control.py
│   │   ├── rule_based.py
│   │   ├── mpc.py
│   │   └── sb3_controller.py
│   ├── hil/
│   │   ├── backend.py
│   │   ├── actuator_client.py
│   │   ├── workload_client.py
│   │   └── watchdog.py
│   ├── telemetry/
│   │   ├── dcgm.py
│   │   ├── nvidia_smi.py
│   │   └── pdu.py
│   ├── evaluation/
│   │   ├── metrics.py
│   │   ├── plots.py
│   │   └── statistics.py
│   └── utils/
│       ├── seed.py
│       ├── logging.py
│       └── time.py
│
├── scripts/
│   ├── check_system.sh
│   ├── download_data.sh
│   ├── start_vllm_smoke.sh
│   ├── start_dcgm_exporter.sh
│   ├── restore_gpu_power.sh
│   └── run_hil_safe.sh
│
├── tests/
│   ├── test_env_api.py
│   ├── test_conservation.py
│   ├── test_deadlines.py
│   ├── test_actions.py
│   ├── test_determinism.py
│   └── test_hil_safety.py
│
└── results/
    ├── calibration/
    ├── training/
    ├── evaluation/
    ├── hil/
    └── figures/
```

---

## 7. 服务器预检查

### 7.1 记录系统信息

```bash
mkdir -p ~/projects/AIDRBench
cd ~/projects/AIDRBench

mkdir -p results/system

uname -a | tee results/system/uname.txt
lsb_release -a | tee results/system/os.txt
lscpu | tee results/system/lscpu.txt
free -h | tee results/system/memory.txt
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS | tee results/system/storage.txt

docker --version | tee results/system/docker.txt
nvidia-smi | tee results/system/nvidia-smi.txt
nvidia-smi -L | tee results/system/gpu-list.txt
nvidia-smi topo -m | tee results/system/gpu-topology.txt
nvidia-smi -q -d POWER | tee results/system/gpu-power-defaults.txt
```

不要预设四张卡一定存在 NVLink。后续并行策略以 `nvidia-smi topo -m` 的真实输出为准。

### 7.2 验证 Docker 能访问 GPU

```bash
docker run --rm --gpus all \
  nvidia/cuda:13.3.1-base-ubuntu24.04 \
  nvidia-smi
```

若失败，再安装或修复 NVIDIA Container Toolkit。不要在驱动已经正常的机器上盲目重装 CUDA Toolkit；vLLM 采用容器内 CUDA 运行时。

### 7.3 基础系统包

```bash
sudo apt update
sudo apt install -y \
  git git-lfs curl wget jq unzip tar \
  build-essential pkg-config \
  tmux htop nvme-cli smartmontools

git lfs install
```

### 7.4 Python 项目环境

本仓库在论文服务器上使用独立 Conda 环境运行，避免污染 `base` 或其他项目环境。
`uv` 只用于解析并锁定 Python 依赖；运行和测试都通过 Conda：

```bash
conda env create --file environment.lock.yml
conda activate aidrbench

python --version
python -m pytest -q
ruff check .
mypy
```

`environment.yml` 是便于阅读的环境定义，`environment.lock.yml` 固定 Conda build 和
精确的 pip 版本，`uv.lock`/`requirements.lock.txt` 固定 Python 依赖解析结果。更新依赖时
修改 `pyproject.toml` 后重新生成锁文件，不能手工编辑 `uv.lock`。

AWS CLI 使用独立的数据工具环境，避免它的依赖约束进入主科学环境：

```bash
conda env create --file environment.data-tools.lock.yml
conda run --name aidrbench-data-tools aws --version
```

AIPerf 建议作为独立工具安装，避免与主环境的依赖互相影响：

```bash
conda create --name aidrbench-aiperf --override-channels -c conda-forge python=3.12 pip
conda activate aidrbench-aiperf
python -m pip install aiperf

aiperf --help
```

若 shell 找不到命令，重新加载 shell 或检查 `~/.local/bin` 是否在 `PATH` 中。

---

## 8. 数据源总览

| 数据 | V0 用途 | 推荐来源 | 是否必须 |
|---|---|---|---:|
| 在线推理请求 | 到达时间、输入/输出 token、burstiness | BurstGPT | 是 |
| 可延迟作业 | 到达、持续时间、GPU 请求分布 | Alibaba GPU trace v2020 | 主实验建议使用 |
| 社区负荷 | PCC 背景负荷 | NLR/NREL EULP；可选 CityLearn named dataset | 是 |
| DR 事件 | 削减比例、持续时间、通知时间 | 可控合成事件 | 是 |
| PV | 中午吸纳场景 | 社区数据或合成 | 可选 |
| GPU 功率与性能 | 代理模型标定 | 本机实测 | 是 |
| 节点交流输入功率 | 完整节点功率 | 智能 PDU/功率分析仪 | 强烈建议 |
| 日本价格/区域负荷 | 本地案例扩展 | JEPX、九州电力 | 可选 |

### 8.1 数据使用原则

- 原始数据只读，不覆盖；
- 所有处理结果保存为 Parquet；
- 每个数据集记录 URL、下载日期、版本、文件 hash 和许可证；
- 训练、验证、测试按时间切分，不能随机打散单条请求造成泄漏；
- 原始模型标签（如 GPT-4）只是请求轨迹标签，不代表我们实测了该封闭模型的功耗；
- Alibaba 数据不提供真实任务 deadline，任何 deadline 都必须明确标记为**场景生成参数**。

---

## 9. 下载在线推理轨迹：BurstGPT

### 9.1 快速测试文件

```bash
mkdir -p data/raw/burstgpt data/manifests

curl -L \
  https://raw.githubusercontent.com/HPMLL/BurstGPT/main/data/BurstGPT_1.csv \
  -o data/raw/burstgpt/BurstGPT_1.csv

head -n 3 data/raw/burstgpt/BurstGPT_1.csv
sha256sum data/raw/burstgpt/BurstGPT_1.csv \
  | tee data/manifests/burstgpt_1.sha256
```

### 9.2 正式实验文件

正式实验优先使用 GitHub Release v2.0 中去除失败请求的文件：

- `BurstGPT_without_fails_1.csv`
- `BurstGPT_without_fails_2.csv`
- `BurstGPT_without_fails_3.csv`

可以使用 GitHub CLI：

```bash
mkdir -p external data/raw/burstgpt

git clone --depth 1 https://github.com/HPMLL/BurstGPT.git external/BurstGPT

# 若服务器已安装 gh 并完成认证：
gh release download v2.0 \
  --repo HPMLL/BurstGPT \
  --dir data/raw/burstgpt
```

没有 `gh` 时，从下列 release 页面下载后放入 `data/raw/burstgpt/`：

```text
https://github.com/HPMLL/BurstGPT/releases/tag/v2.0
```

### 9.3 预处理规则

至少保留：

```text
timestamp_s
session_id
elapsed_time_s
original_model_label
request_tokens
response_tokens
total_tokens
log_type
source_file
```

处理时：

1. 排除 `request_tokens <= 0`；
2. 正式主实验排除 `response_tokens <= 0`，失败率作为单独统计；
3. 不保留任何真实用户文本，因为轨迹本身只包含 token 数和时间；
4. 根据目标服务器能力设置 `time_scale`：
   - `time_scale = 1`：保留原到达节奏；
   - `time_scale > 1`：压缩时间、提高请求率；
   - `time_scale < 1`：展开时间、降低请求率；
5. 将一天或连续两天窗口作为一个 episode；
6. 将原始 trace 的时间顺序保留到 train/validation/test 切分中。

建议输出：

```text
data/processed/inference_requests.parquet
```

目标 CLI：

```bash
uv run aidrbench data preprocess-burstgpt \
  --input 'data/raw/burstgpt/BurstGPT_without_fails_*.csv' \
  --output data/processed/inference_requests.parquet \
  --time-scale 1.0
```

---

## 10. 下载可延迟作业轨迹：Alibaba GPU v2020

V0 只需下载 job 和 task 表，不必一开始下载 1 GB 以上的全部传感器数据。

```bash
mkdir -p data/raw/alibaba_v2020
cd data/raw/alibaba_v2020

curl -L -O \
  https://aliopentrace.oss-cn-beijing.aliyuncs.com/v2020GPUTraces/pai_job_table.tar.gz

curl -L -O \
  https://aliopentrace.oss-cn-beijing.aliyuncs.com/v2020GPUTraces/pai_task_table.tar.gz

sha256sum pai_job_table.tar.gz pai_task_table.tar.gz
```

官方公布的压缩文件 SHA-256：

```text
pai_job_table.tar.gz
5aad7f7caac501136d14ed6a48e40546f825d7b0617a3a4f337e2348fe0a6cb0

pai_task_table.tar.gz
cd1d6dc3215d2a8607ccf6b6dd952b5db776df86926c73259fea7c1499ac40e5
```

验证并解压：

```bash
echo '5aad7f7caac501136d14ed6a48e40546f825d7b0617a3a4f337e2348fe0a6cb0  pai_job_table.tar.gz' \
  | sha256sum -c -

echo 'cd1d6dc3215d2a8607ccf6b6dd952b5db776df86926c73259fea7c1499ac40e5  pai_task_table.tar.gz' \
  | sha256sum -c -

tar -xzf pai_job_table.tar.gz
tar -xzf pai_task_table.tar.gz

cd ../../..
```

### 10.1 真实字段与合成字段必须分开

真实字段可以包括：

```text
job_name
status
job_start_time_s
job_end_time_s
task_name
task_start_time_s
task_end_time_s
instance_count
plan_gpu_percent
gpu_type
```

由真实字段计算：

\[
\text{duration}_j
=
\text{end}_j-\text{start}_j,
\]

\[
\text{requested GPU}_j
=
\text{instance count}_j
\times
\frac{\text{plan GPU percent}_j}{100},
\]

\[
\text{work}_{j}^{\mathrm{GPU\text{-}s}}
=
\text{duration}_j
\times
\text{requested GPU}_j.
\]

Alibaba v2020 不提供真实 deadline。推荐使用可配置的 slack factor：

\[
D_j
=
R_j+s_j\,\text{duration}_j,
\]

其中：

```text
s_j ∈ {1.5, 2, 4, 8}
```

或从对数分布采样。论文中应称为：

> empirically parameterized arrivals and sizes with scenario-generated deadlines

不能称为真实生产 deadline。

### 10.2 映射到本地四卡节点

原始集群远大于本地节点，需要：

1. 按时间窗口抽样；
2. 将大于两张 batch GPU 的任务拆分或过滤；
3. 保留 duration 和 GPU-work 分布；
4. 通过 `arrival_scale` 调节每小时作业数量；
5. 将本地离线推理的实测吞吐量映射为 work-unit 完成速度。

建议输出：

```text
data/processed/batch_jobs.parquet
```

建议 schema：

```text
job_id
release_time_s
work_gpu_seconds
gpu_demand_original
duration_original_s
deadline_time_s
deadline_is_synthetic
slack_factor
priority
preemptible
source_file
```

目标 CLI：

```bash
uv run aidrbench data preprocess-alibaba \
  --job-table data/raw/alibaba_v2020/pai_job_table.csv \
  --task-table data/raw/alibaba_v2020/pai_task_table.csv \
  --max-local-batch-gpus 2 \
  --deadline-policy slack-mixture \
  --seed 42 \
  --output data/processed/batch_jobs.parquet
```

### 10.3 无 Alibaba 数据时的 smoke mode

环境初期可以使用合成作业：

- 到达：非齐次 Poisson；
- job size：lognormal；
- slack factor：`{1.5, 2, 4, 8}`；
- priority：`{low, normal, urgent}`；
- 只用于单元测试，不能替代正式主实验。

---

## 11. 社区负荷数据

### 11.1 正式推荐：NLR/NREL End-Use Load Profiles

公开 S3 根目录：

```bash
mkdir -p data/raw/eulp data/manifests

aws s3 ls --no-sign-request \
  s3://oedi-data-lake/nrel-pds-building-stock/ \
  | tee data/manifests/eulp_s3_root_listing.txt
```

数据集入口：

```text
https://registry.opendata.aws/nrel-pds-building-stock/
```

由于完整数据库非常大，不要直接递归下载整个 bucket。建议只选择：

- 一个住宅社区；
- 一个住宅 + 小型商业混合社区；
- 三种气候或季节；
- 15 分钟电负荷；
- 可选 PV 输出。

处理后统一输出：

```text
data/processed/community_load.parquet
```

社区 profile 选择必须由 catalog/config 驱动，不能在代码中固定某个地点或气候区：

```bash
conda run --name aidrbench aidrbench data catalog-community \
  --input 'data/raw/eulp/**/*.csv' \
  --output data/manifests/community_profiles.yaml

conda run --name aidrbench aidrbench data list-community-profiles \
  --catalog data/manifests/community_profiles.yaml

conda run --name aidrbench aidrbench data preprocess-community \
  --catalog data/manifests/community_profiles.yaml \
  --profile <LISTED_PROFILE_ID> \
  --output data/processed/community_selected.parquet

conda run --name aidrbench aidrbench data preprocess \
  --config configs/data/community_eulp.yaml
```

仓库的 3A、3C、5A 是首个论文默认矩阵，不是 benchmark 的硬编码范围。新增官方
profile 后重新生成 catalog，即可从列表用一个或多个 `--profile` 任意选择，也可在配置中的
`profiles` 列表选择。相同气候区和建筑类型的多个地点文件会获得不同 profile ID，不会互相
覆盖；地点级 OOD 切分与每个 profile 内的时间切分必须分别记录。

标准 schema：

```text
timestamp
community_load_kw
pv_generation_kw
net_community_load_kw
profile_id
season
source
```

### 11.2 快速替代：CityLearn named dataset

CityLearn 可以作为**社区数据提取器**，但不作为本项目的控制环境。目标是从一个 named dataset 中导出未控制情况下的社区净负荷，再交给 AIDRBench 使用。

```bash
uv add citylearn
```

实现脚本时使用 `citylearn.data.DataSet` 查看可用数据集，并导出总净电力时间序列。固定 CityLearn 版本并记录 dataset name；不要让自动更新改变论文输入。

### 11.3 最小合成社区

为了让仓库在没有大数据下载时可以立即通过 smoke test，必须提供一个合成 profile：

\[
P_t^{\mathrm{community}}
=
P_0
\left[
0.55
+G_{\mathrm{morning}}(t)
+G_{\mathrm{evening}}(t)
+0.06\sin(2\pi t/24)
+\epsilon_t
\right].
\]

要求：

- 早峰和晚峰明确；
- 每日总能量为正；
- 噪声具有时间相关性；
- profile 可通过 seed 完全复现；
- 合成数据只用于开发和消融实验。

目标 CLI：

```bash
uv run aidrbench data make-synthetic-community \
  --days 30 \
  --resolution-seconds 900 \
  --peak-kw 100 \
  --seed 42 \
  --output data/processed/community_synthetic.parquet
```

### 11.4 可选区域扩展（不作为默认 benchmark）

后续可通过 catalog/config 加入任意区域的：

- 日前价格；
- 区域实际用电或供需数据；
- 对应地点天气。

区域总负荷不能被表述为真实社区馈线数据。可将其归一化后作为背景形状或外部价格信号，
并在实验清单中记录具体地点、时间范围和来源版本。

---

## 12. DR 事件生成器

V0 采用可控合成事件，以便所有控制器接收完全相同的任务。

每个事件包含：

```text
event_id
start_time
end_time
duration_minutes
notice_minutes
reduction_fraction
pcc_limit_kw
post_event_ramp_minutes
```

主实验因子：

| 因子 | 水平 |
|---|---|
| 削减比例 | 10%、20%、30% |
| 持续时间 | 15、30、60、120 min |
| 提前通知 | 0、5、15、30 min |
| 事件数量 | 1、2、3 次/日 |
| 相邻事件间隔 | 15、30、60、180 min |
| 事件时段 | 中午、晚高峰、随机 |

必须包含连续事件，因为第一次 DR 事件后积累的 backlog 可能使第二次事件无法完成。

### 12.1 基线定义

需求响应基线是敏感项。至少报告两种：

1. **无控制 counterfactual**：同一请求、作业和社区场景下，不应用 DR 的功率；
2. **历史基线**：同类日或事件前窗口推算。

主算法比较优先使用 counterfactual baseline，因为它能严格控制随机因素；历史基线作为现实敏感性分析。

目标 CLI：

```bash
uv run aidrbench data generate-dr-events \
  --community data/processed/community_load.parquet \
  --days 90 \
  --reductions 0.10 0.20 0.30 \
  --durations 15 30 60 120 \
  --notices 0 5 15 30 \
  --seed 42 \
  --output data/processed/dr_events.parquet
```

---

## 13. 标准化数据切分

所有控制器必须使用同一 manifest。

### 13.1 时间切分

建议：

```text
训练：最早 60%
验证：中间 20%
测试：最后 20%
```

不能将单条 BurstGPT 请求随机打散，因为这会破坏 burst 和周期结构。

### 13.2 外部分布测试

至少保留一个 OOD 测试维度：

- 未见过的社区 profile；
- 未见过的 DR 持续时间；
- 请求率增加 25% 或 50%；
- 第二个 LLM 模型；
- 未见过的 power-cap 中间值。

### 13.3 Manifest

```yaml
# data/manifests/split_v1.yaml
seed: 42
inference:
  train: [window_000, window_001, window_002]
  validation: [window_003]
  test: [window_004]
batch:
  train: [week_00, week_01, week_02]
  validation: [week_03]
  test: [week_04]
community:
  train: [community_a, community_b]
  validation: [community_c]
  test: [community_d]
```

---

## 14. 启动 vLLM：先做 smoke test

### 14.1 固定容器版本

本文编写时的固定示例：

```bash
export VLLM_IMAGE=vllm/vllm-openai:v0.27.0-cu129-ubuntu2404

docker pull "$VLLM_IMAGE"
```

论文冻结前应记录：

```bash
docker image inspect "$VLLM_IMAGE" \
  --format '{{json .RepoDigests}}' \
  | tee results/system/vllm_image_digest.txt
```

### 14.2 单 GPU smoke test

```bash
mkdir -p ~/.cache/huggingface ~/.cache/vllm

export MODEL_ID=Qwen/Qwen3-0.6B

# 前台运行便于查看错误；确认成功后再改为 -d。
docker run --rm \
  --name aidr-vllm-smoke \
  --gpus '"device=0"' \
  --ipc=host \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v ~/.cache/vllm:/root/.cache/vllm \
  "$VLLM_IMAGE" \
  --model "$MODEL_ID"
```

另一个终端验证：

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"Qwen/Qwen3-0.6B",
    "messages":[{"role":"user","content":"test"}],
    "max_tokens":8
  }' | jq
```

### 14.3 正式双 GPU 推理池

选择实际研究模型后：

```bash
export MODEL_ID='<YOUR_OPEN_MODEL_ID>'

# 注意：模型结构必须支持 tensor_parallel_size=2。
docker run -d \
  --name aidr-vllm-inference \
  --gpus '"device=0,1"' \
  --ipc=host \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v ~/.cache/vllm:/root/.cache/vllm \
  "$VLLM_IMAGE" \
  --model "$MODEL_ID" \
  --tensor-parallel-size 2
```

批处理池可运行独立 worker 或第二个 vLLM 实例。V0 更推荐由项目自己的 batch worker 将 prompt 文件按作业派发到 GPU 2–3，避免两个服务争用端口和调度逻辑。

---

## 15. 用 AIPerf 回放 BurstGPT

### 15.1 快速 10 请求测试

```bash
mkdir -p results/aiperf/smoke

head -n 11 data/raw/burstgpt/BurstGPT_1.csv \
  > data/raw/burstgpt/BurstGPT_short.csv

aiperf profile \
  --model Qwen/Qwen3-0.6B \
  --endpoint-type chat \
  --streaming \
  --url localhost:8000 \
  --input-file data/raw/burstgpt/BurstGPT_short.csv \
  --custom-dataset-type burst_gpt_trace \
  --fixed-schedule
```

AIPerf 会根据 token 长度合成 prompt，不会恢复或使用真实 prompt 文本。

### 15.2 正式 profiling 原则

- 请求轨迹、power cap、模型、容器 digest 和随机种子写入 run manifest；
- AIPerf 固定 schedule；
- 每个配置先 warm-up；
- 不把服务启动编译时间计入稳态性能；
- 记录失败请求和 timeout，不能静默删除；
- 每个实验至少重复 3 次；
- 实验顺序随机化，降低温度漂移影响。

---

## 16. GPU 与节点遥测

### 16.1 DCGM Exporter

```bash
export DCGM_EXPORTER_TAG=latest

# 论文冻结时必须把 latest 改成具体版本标签。
docker run -d \
  --restart unless-stopped \
  --name dcgm-exporter \
  --gpus all \
  --cap-add SYS_ADMIN \
  -p 9400:9400 \
  nvcr.io/nvidia/k8s/dcgm-exporter:${DCGM_EXPORTER_TAG}

curl -s http://localhost:9400/metrics | head
```

若工作站 GPU/驱动组合无法使用 DCGM profiling 字段，则使用 NVML 或 `nvidia-smi` fallback；不要因为某个 DCGM 字段缺失而丢弃整套实验。

### 16.2 `nvidia-smi` fallback

先查看当前驱动支持的字段：

```bash
nvidia-smi --help-query-gpu > results/system/nvidia-query-fields.txt
```

示例 1 秒日志：

```bash
mkdir -p results/telemetry

nvidia-smi \
  --query-gpu=timestamp,index,name,power.draw,utilization.gpu,utilization.memory,temperature.gpu,clocks.sm,clocks.mem,memory.used,pstate \
  --format=csv \
  --loop-ms=1000 \
  > results/telemetry/nvidia_smi_$(date +%Y%m%d_%H%M%S).csv
```

若某个字段名在当前驱动中不可用，按 `--help-query-gpu` 输出替换。

### 16.3 整机交流侧功率

最优方案：使用支持 1 秒采样和时间戳的智能 PDU/功率分析仪，记录：

```text
timestamp
voltage_v
current_a
active_power_w
energy_wh
power_factor
```

仅使用 GPU power draw 不能代表 CPU、内存、风扇、主板和 PSU 损耗。没有 PDU 时：

- 主结果称为 `GPU-board power`；
- 节点功率只能称为 estimate；
- 不报告“实测完整 PUE”；
- PUE/冷却只能作为外部情景参数。

### 16.4 时间同步

所有进程使用：

- UTC wall-clock timestamp；
- monotonic timestamp；
- 相同 NTP/chrony；
- 运行开始前写入 clock offset 检查。

```bash
timedatectl status | tee results/system/time_status.txt
chronyc tracking 2>/dev/null | tee results/system/chrony_tracking.txt || true
```

---

## 17. Power cap 安全操作

### 17.1 记录默认上下限

```bash
nvidia-smi -q -d POWER \
  | tee results/system/gpu_power_limits_before_experiments.txt
```

设置 power limit 需要 root，且必须位于设备报告的最小和最大范围内：

```bash
# 示例；不要直接照抄瓦数。
sudo nvidia-smi -i 0 -pl <VALID_WATTS>
```

### 17.2 不要让 RL 进程直接执行任意 sudo 命令

硬件在环时采用：

```text
RL/controller process (unprivileged)
             │ action ID
             ▼
allow-listed actuator daemon
             │ validated power limit
             ▼
nvidia-smi / NVML
```

actuator 只能接受预定义动作：

```text
infer_cap_idx ∈ {0,1,2}
batch_gpu_count ∈ {0,1,2}
batch_cap_idx ∈ {0,1,2}
```

并执行：

- 范围检查；
- GPU ID 白名单；
- 温度和通信 watchdog；
- 超时恢复默认 power limit；
- 记录每次动作、调用者和结果。

### 17.3 恢复默认值

实验开始前从 `nvidia-smi -q -d POWER` 解析每张 GPU 的 default limit，并生成：

```bash
scripts/restore_gpu_power.sh
```

任何退出路径都必须调用它：

- 正常结束；
- `SIGINT`；
- `SIGTERM`；
- controller 崩溃；
- watchdog 超时；
- GPU 温度越限。

---

## 18. 硬件标定实验

### 18.1 标定目标

需要得到：

\[
(\text{arrival rate},\text{token mix},\text{power cap},
\text{active batch GPUs},\text{batch load})
\rightarrow
\]

\[
(P_{\mathrm{node}},P_{\mathrm{GPU}},
\mu_{\mathrm{inf}},\mathrm{TTFT}_{p99},
\mathrm{TPOT}_{p99},\mu_{\mathrm{batch}},T_{\mathrm{GPU}}).
\]

### 18.2 两阶段设计

#### 阶段 A：粗网格

| 因子 | 建议水平 |
|---|---|
| inference cap ratio | 0.70、0.85、1.00 |
| batch active GPUs | 0、1、2 |
| batch cap ratio | 0.60、0.80、1.00 |
| 请求率 | p25、p50、p75、p90 |
| token mix | short、medium、long |

power cap 的绝对瓦数按：

\[
P_{\mathrm{cap}}(r)
=
\mathrm{clip}(rP_{\mathrm{default}},P_{\min},P_{\mathrm{default}}).
\]

不使用高于 default limit 的设置。

#### 阶段 B：补点

对延迟边界、功率非线性和代理模型误差大的区域增加 30–100 个随机配置。

### 18.3 每个 run

建议：

```text
模型加载/编译：不计入
warm-up：5 min
measurement：10 min
cool-down/idle：2 min
重复：3 次
```

每个 run 保存：

```text
run_id
start/end timestamp
model ID and revision
vLLM image digest
GPU IDs and topology
power limits
arrival trace window
request/token statistics
AIPerf output
DCGM/NVML telemetry
PDU telemetry
ambient/inlet temperature if available
failure and timeout counts
```

### 18.4 输出文件

```text
results/calibration/<run_id>/manifest.yaml
results/calibration/<run_id>/requests.parquet
results/calibration/<run_id>/gpu_telemetry.parquet
results/calibration/<run_id>/node_power.parquet
results/calibration/<run_id>/summary.json
```

目标 CLI：

```bash
uv run aidrbench calibrate make-plan \
  --config configs/hardware/four_gpu_node.yaml \
  --output results/calibration/plan.csv

uv run aidrbench calibrate run \
  --plan results/calibration/plan.csv \
  --run-id <RUN_ID>

uv run aidrbench calibrate summarize \
  --input results/calibration \
  --output data/processed/hardware_runs.parquet
```

---

## 19. 功率—性能代理模型

V0 不需要先用深度神经网络。优先使用透明、稳定且可校验的模型。

推荐分别拟合：

1. `node_power_model`；
2. `inference_throughput_model`；
3. `ttft_p99_model`；
4. `tpot_p99_model`；
5. `batch_service_model`；
6. `gpu_temperature_model`（可选）。

### 19.1 特征

```text
inference_power_cap_w
batch_power_cap_w
active_batch_gpus
request_rate_rps
input_token_mean / quantiles
output_token_mean / quantiles
inference_queue_work
batch_queue_work
previous_power_w
previous_temperature_c
```

### 19.2 模型选择顺序

1. 分箱 + 多维线性插值；
2. 分段线性模型；
3. Gradient Boosting / Random Forest；
4. 只有在显著提高 OOD 表现时再使用小型神经网络。

### 19.3 训练与测试

不能只随机切分采样点。至少进行：

- random-run split；
- held-out power-cap level；
- held-out request-rate level；
- held-out token mix；
- held-out model（若有第二个模型）。

报告：

```text
MAE
RMSE
MAPE（仅在分母远离 0 时）
R²
p95 absolute error
constraint classification error
```

尤其关注：

- 是否错误预测满足 DR，但实机实际超限；
- 是否低估 p99 延迟；
- 是否出现物理上反常的 cap 降低、功率反而持续增加。

目标 CLI：

```bash
uv run aidrbench surrogate fit \
  --input data/processed/hardware_runs.parquet \
  --config configs/hardware/four_gpu_node.yaml \
  --output models/hardware_surrogates/v0

uv run aidrbench surrogate evaluate \
  --model-dir models/hardware_surrogates/v0 \
  --split held-out-configs \
  --output results/calibration/surrogate_evaluation.json
```

---

## 20. 环境内部动态

### 20.1 时间尺度

推荐：

```text
原始 GPU telemetry：1 s
环境内部服务更新：1–10 s
agent/control step：60 s
社区负荷输入：15 min，step 内保持或插值
episode：24 h；连续事件实验使用 48 h
```

Gym 环境每次 `step()` 可以在内部执行 6 × 10 秒或 60 × 1 秒的子步，再返回一个 agent observation。

### 20.2 在线推理队列

可用 token-work 近似：

\[
Q_{t+1}^{\mathrm{inf}}
=
\max\left(
0,
Q_t^{\mathrm{inf}}+A_t^{\mathrm{inf}}-S_t^{\mathrm{inf}}
\right).
\]

其中：

- `A_inf`：本步到达的总 token-work；
- `S_inf`：由代理模型和动作决定的已完成 work；
- 请求级延迟可以由事件模拟器精确计算，快速训练时使用队列/代理近似。

V0 应提供两种模式：

```text
aggregate：快速 RL 训练
request_level：慢速、高保真评估
```

### 20.3 Deadline bucket

将可延迟作业按剩余期限划分为 K 个桶：

```text
0–15 min
15–30 min
30–60 min
1–2 h
2–4 h
>4 h
```

采用 earliest-deadline-first 完成 work。每一步后：

1. 执行最紧迫 bucket；
2. 剩余工作向更近的期限桶移动；
3. 已到期但未完成的 work 计入 `deadline_missed_work`；
4. 不允许 backlog 静默消失。

### 20.4 数据中心功率

有 PDU 时：

\[
P_t^{\mathrm{node}}
=f_{\theta}^{\mathrm{AC}}
(s_t,a_t).
\]

只有 GPU 测量时：

\[
\widehat{P}_t^{\mathrm{node}}
=P_{\mathrm{host,idle}}
+
\sum_g P_{g,t}
+
\widehat{P}_{\mathrm{nonGPU,var},t}.
\]

设施级扩展可选：

\[
P_t^{\mathrm{facility}}
=\mathrm{pPUE}_t P_t^{\mathrm{node/fleet}}.
\]

V0 默认：

```text
overhead_mode: none
```

主实验可增加 `pPUE = 1.10, 1.20, 1.30` 敏感性，但必须称为情景参数，不称为实测冷却系统。

### 20.5 Rebound

定义 DR 结束后的观察窗口，例如 60 min：

\[
P^{\mathrm{rebound}}_{\max}
=
\max_{t\in \mathcal{W}_{post}}
\left(P_t^{\mathrm{PCC}}-P_t^{\mathrm{baseline}}\right)_+.
\]

还应报告：

```text
rebound energy
backlog recovery time
second-event available flexibility
```

---

## 21. Gymnasium 环境规范

环境 ID：

```text
AIDRBench-v0
```

类：

```python
class CommunityAIDemandResponseEnv(gymnasium.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 1}

    def __init__(self, config, backend="emulator", render_mode=None): ...
    def reset(self, *, seed=None, options=None): ...
    def step(self, action): ...
    def render(self): ...
    def close(self): ...
```

### 21.1 动作空间：V0 离散 27 动作

三个控制量：

```text
inference power cap ratio ∈ {0.70, 0.85, 1.00}
batch active GPU count    ∈ {0, 1, 2}
batch power cap ratio     ∈ {0.60, 0.80, 1.00}
```

组合后：

```python
action_space = gymnasium.spaces.Discrete(27)
```

编码：

```python
infer_idx = action // 9
remainder = action % 9
batch_gpu_count = remainder // 3
batch_cap_idx = remainder % 3
```

这样 DQN、A2C 和 PPO 可以使用完全相同的动作集合。

V1 再增加连续动作环境：

```text
AIDRBenchContinuous-v0
```

用于 SAC/TD3，不要在第一阶段同时维护两套复杂环境。

### 21.2 Observation

建议使用一维 `Box`，避免早期 Dict observation 增加算法差异：

```text
sin(time_of_day)
cos(time_of_day)
day_of_week normalized
current community load
community load forecast: +15, +30, +60 min
current PV
current PCC limit
requested DR reduction
DR active flag
notice remaining
DR remaining time
current PCC power
current DC power
current inference arrival rate
input/output token statistics
inference queue work
estimated TTFT p99
estimated TPOT p99
batch backlog by deadline bucket
missed deadline work in current episode
current inference cap index
current batch GPU count
current batch cap index
post-event flag
previous action-switch indicator
optional GPU temperature summaries
```

原则：

- 所有连续变量按训练集统计量归一化；
- 预测量必须来自统一 forecast module；
- 不能把真实未来请求或真实未来社区负荷直接泄露给 RL；
- MPC 和 RL 获得相同预测；
- `info` 中保留未经归一化的原始量。

### 21.3 `step()` 返回

```python
observation, reward, terminated, truncated, info
```

- `terminated=True`：硬件安全停止、不可恢复错误；
- `truncated=True`：episode 达到时间上限；
- 普通 SLA 违约不终止 episode，而是记录并惩罚；
- HIL watchdog 触发时立即 terminated。

### 21.4 `info` 必须包含的原始 KPI

```text
pcc_power_kw
pcc_limit_kw
dr_exceedance_kw
dr_tracking_error_kw
dc_power_kw
gpu_power_w_by_id
inference_arrivals
inference_completed
inference_queue_work
ttft_p50_ms / p95 / p99
tpot_p50_ms / p95 / p99
slo_violation_count
batch_arrived_work
batch_completed_work
batch_backlog_work
deadline_missed_work
rebound_power_kw
action_components
action_changed
backend_name
scenario_id
```

### 21.5 环境校验

```bash
uv run python - <<'PY'
from stable_baselines3.common.env_checker import check_env
from aidrbench.envs import CommunityAIDemandResponseEnv

env = CommunityAIDemandResponseEnv(config="configs/env/v0_discrete.yaml")
check_env(env, warn=True)
print("Environment API check passed")
PY
```

---

## 22. Reward 与 KPI 分离

Reward 只服务于训练，论文结论必须使用原始 KPI。

建议初始形式：

\[
r_t=-\left[
 w_{DR}\tilde e_{DR,t}^{2}
+w_{SLA}e_{SLA,t}
+w_{D}e_{deadline,t}
+w_{B}\tilde B_t
+w_{E}\tilde P_t^{DC}
+w_{S}I(a_t\ne a_{t-1})
+w_{R}\tilde e_{rebound,t}^{2}
\right].
\]

其中所有带 `~` 的量必须除以固定 reference scale，避免单位导致某项支配 reward。

建议起始权重，不是论文最终值：

```yaml
reward:
  dr_exceedance: 20.0
  sla_violation: 20.0
  deadline_miss: 20.0
  backlog: 1.0
  energy: 0.1
  action_switch: 0.05
  rebound: 5.0
```

权重选择流程：

1. 先让无控制和 rule-based 的各项 reward magnitude 大致同阶；
2. 在 validation set 调整；
3. 固定后再跑 test；
4. 报告 reward-weight 敏感性；
5. 不以 test set 调权重。

### 22.1 主 KPI

#### 电网/DR

```text
DR success rate
mean / p95 / max exceedance
tracking RMSE
energy not delivered
PCC peak
post-event rebound peak and energy
```

#### 在线服务

```text
request goodput
failure/timeout rate
TTFT p50/p95/p99
TPOT p50/p95/p99
end-to-end latency
SLO violation rate
```

#### 批处理

```text
completed work
deadline miss rate
maximum backlog
mean waiting time
p95 completion delay
recovery time after DR
```

#### 运行代价

```text
node/fleet energy
action switches
power-cap changes
batch start/stop count
GPU temperature and throttling time
```

---

## 23. 控制器基线

所有控制器必须继承：

```python
class BaseController:
    def reset(self, scenario_metadata): ...
    def act(self, observation, deterministic=True) -> int: ...
    def close(self): ...
```

### 23.1 No-control

固定：

```text
inference cap = 1.00
batch active GPUs = 2
batch cap = 1.00
```

它是 counterfactual baseline，也是 DR delivered power 的参考。

### 23.2 Rule-based controller

建议顺序：

1. 无 DR：根据 backlog 运行 1–2 张 batch GPU；
2. 收到 advance notice：在不破坏推理 SLA 的情况下预先清理紧迫 backlog；
3. DR 开始：先减少 batch GPU 数；
4. 仍超限：降低 batch cap；
5. 仍超限且推理 SLA 有 margin：降低 inference cap；
6. DR 结束：每 5–15 min 只恢复一个动作等级，抑制 rebound；
7. deadline bucket 即将过期时覆盖普通节能规则。

规则中的所有阈值只在 validation set 调整。

### 23.3 MPC benchmark

MPC 是 benchmark，不是论文的核心新方法。推荐控制一个连续的目标：

```text
target inference power budget
target batch execution work
target total DC power
```

使用测得的简化线性/分段线性代理模型，预测 horizon 为 30–60 min：

\[
\min \sum_{k=0}^{H-1}
\left[
\alpha e_{DR,k}^2
+\beta e_{SLA,k}
+\gamma B_k
+\eta \Delta u_k^2
\right].
\]

求得连续目标后，由 action mapper 选择最近的 27 个可执行动作之一。

优点：

- 使用 CVXPY + OSQP 即可；
- 不需要先解决混合整数 MPC；
- 与 RL 使用相同 surrogate 和 forecast；
- 可另设 perfect-forecast oracle，作为上界但不参与公平主比较。

### 23.4 DQN

适合离散动作，作为主要 off-policy baseline。

初始配置：

```yaml
algorithm: dqn
learning_rate: 0.0001
buffer_size: 500000
learning_starts: 20000
batch_size: 256
gamma: 0.995
train_freq: 4
gradient_steps: 1
target_update_interval: 10000
exploration_fraction: 0.20
exploration_final_eps: 0.02
```

### 23.5 A2C

作为简单 on-policy baseline：

```yaml
algorithm: a2c
learning_rate: 0.0007
n_steps: 20
gamma: 0.995
gae_lambda: 0.95
ent_coef: 0.01
```

### 23.6 PPO

作为主要 on-policy baseline：

```yaml
algorithm: ppo
learning_rate: 0.0003
n_steps: 512
batch_size: 256
n_epochs: 10
gamma: 0.995
gae_lambda: 0.95
clip_range: 0.20
ent_coef: 0.01
```

这些仅是起始值。最终参数在 validation set 或 RL Zoo 风格 sweep 中选择，并固定到 YAML。

### 23.7 后续安全 RL

等平台和基线完成后，再新增：

- constrained PPO；
- Lagrangian methods；
- action shielding；
- CVaR/risk-sensitive RL；
- sim-to-real adaptation。

安全 RL 不能阻塞 V0 论文完成。

---

## 24. 目标 CLI

实现完成后，仓库应支持以下一致命令。

### 24.1 数据

```bash
uv run aidrbench data download --all-public
uv run aidrbench data preprocess --config configs/data/burstgpt.yaml
uv run aidrbench data preprocess --config configs/data/alibaba_v2020.yaml
uv run aidrbench data preprocess --config configs/data/community.yaml
uv run aidrbench data validate --manifest data/manifests/split_v1.yaml
```

### 24.2 环境

```bash
uv run aidrbench env check --config configs/env/v0_discrete.yaml
uv run aidrbench env rollout-random --episodes 2
uv run aidrbench env rollout-rule --episodes 2
```

### 24.3 训练

```bash
uv run aidrbench train \
  --algo dqn \
  --config configs/experiment/simulation_main.yaml \
  --seed 1

uv run aidrbench train \
  --algo a2c \
  --config configs/experiment/simulation_main.yaml \
  --seed 1

uv run aidrbench train \
  --algo ppo \
  --config configs/experiment/simulation_main.yaml \
  --seed 1
```

### 24.4 评价

```bash
uv run aidrbench evaluate \
  --controllers no_control rule_based mpc dqn a2c ppo \
  --split test \
  --seeds 1 2 3 4 5 \
  --output results/evaluation/main

uv run aidrbench report \
  --input results/evaluation/main \
  --output results/figures
```

### 24.5 HIL

```bash
uv run aidrbench hil preflight \
  --config configs/hardware/four_gpu_node.yaml

uv run aidrbench hil run \
  --controller rule_based \
  --scenario smoke_20min \
  --deterministic

uv run aidrbench hil run \
  --controller ppo \
  --checkpoint models/rl_checkpoints/ppo/best_model.zip \
  --scenario dr_30pct_60min \
  --deterministic
```

---

## 25. 训练流程

### 25.1 训练只在 emulator 中进行

第一篇论文禁止带探索噪声的策略直接在真实服务器训练。流程：

```text
实测标定 → surrogate → emulator training → frozen policy → HIL evaluation
```

### 25.2 CPU/GPU 使用

小型 MLP RL 通常不需要占用四张 GPU。建议：

```text
RL training: CPU，8–16 parallel envs
GPU 0–3: 留给标定或空闲
```

只有网络规模或批量足够大时才使用一张 GPU 训练策略。不得同时进行硬件标定与占用相同 GPU 的 RL 训练。

### 25.3 多随机种子

主实验至少：

```text
5 seeds
```

若方差较大，增加到 10。每个 seed 保存：

```text
config snapshot
git commit
uv.lock hash
environment seed
algorithm seed
training curve
best validation checkpoint
VecNormalize statistics
```

### 25.4 运行示例

```bash
tmux new -s aidr-ppo

uv run aidrbench train \
  --algo ppo \
  --config configs/experiment/simulation_main.yaml \
  --seed 1 \
  2>&1 | tee results/training/ppo_seed1.log
```

TensorBoard：

```bash
uv run tensorboard \
  --logdir results/training \
  --host 0.0.0.0 \
  --port 6006
```

只在可信局域网开放；不要把 TensorBoard 无认证暴露到公网。

---

## 26. 公平比较协议

### 26.1 所有控制器共享

- 相同 test episode；
- 相同请求和作业到达；
- 相同社区负荷；
- 相同 DR 事件；
- 相同预测信息；
- 相同动作边界；
- 相同 surrogate；
- 相同初始 backlog；
- 相同随机数流。

### 26.2 不能做的事情

- MPC 使用完美未来，而 RL 只使用当前信息，然后把二者当公平主比较；
- 为每个 RL seed 选择最有利 test episode；
- 仅报告 reward；
- 超时请求从分母删除；
- deadline miss 后把 job 从 backlog 移除而不计惩罚；
- 将 GPU power 当成整机或设施总功率；
- 用 test set 调 reward 或 rule thresholds。

### 26.3 统计方法

由于所有控制器在相同 episode 上运行，优先使用配对统计：

- paired bootstrap 95% CI；
- paired difference of means/medians；
- 必要时 Wilcoxon signed-rank；
- 多重比较时校正 p-value；
- 同时报告 effect size，不只报告显著性。

---

## 27. 主实验矩阵

为了避免组合爆炸，分三个层级。

### 27.1 Development

```text
community: synthetic
inference: one BurstGPT day
batch: synthetic
DR: 20%, 30 min, 15 min notice
backend: emulator
controllers: no-control, RBC, PPO
```

### 27.2 Main simulation

```text
community profiles: 3
seasons: winter / summer / shoulder
DR reduction: 10 / 20 / 30%
duration: 15 / 60 / 120 min
notice: 0 / 15 / 30 min
workload scale: 0.75 / 1.00 / 1.25
controllers: no-control / RBC / MPC / DQN / A2C / PPO
seeds: 5
```

使用分层抽样选择约 100–300 个 test episodes，不必跑完整笛卡尔积。

### 27.3 Hardware-in-loop

选择最有代表性的 6–12 个场景：

1. 中等削减、短事件；
2. 强削减、长事件；
3. 无通知事件；
4. 两次连续事件；
5. 高推理负荷；
6. 高紧迫 batch backlog。

每个 controller × scenario 至少重复 3 次，随机化运行顺序。

---

## 28. Server-in-the-loop 运行协议

### 28.1 启动顺序

```text
1. 检查 GPU、温度、空闲进程和 power defaults
2. 启动 telemetry
3. 启动 inference server
4. 加载 batch worker
5. warm-up
6. 启动 community/DR scenario clock
7. 启动 frozen controller
8. 每步记录 observation、action、execution result
9. 正常或异常结束后恢复 defaults
10. 汇总并校验时间戳
```

### 28.2 冻结策略

HIL 中：

```text
deterministic=True
exploration noise=False
parameter update=False
```

### 28.3 安全阈值

配置文件中至少包含：

```yaml
safety:
  max_gpu_temperature_c: <DEVICE_APPROPRIATE_VALUE>
  max_consecutive_actuator_failures: 2
  controller_heartbeat_timeout_s: 10
  telemetry_timeout_s: 5
  restore_defaults_on_exit: true
  stop_batch_on_fault: true
```

温度阈值应依据设备和实验室规范确定，README 不硬编码一个看似通用的数值。

### 28.4 HIL 动作执行延迟

记录：

```text
controller decision timestamp
actuator receive timestamp
nvidia-smi/NVML completion timestamp
observed power response timestamp
```

这样才能评估 DR response time，而不是只比较稳态功率。

### 28.5 Sim-to-real 指标

```text
power prediction MAE
DR success classification mismatch
TTFT p99 prediction error
batch throughput error
policy return drop
constraint violation increase
controller ranking change
```

---

## 29. 单元测试和验收标准

### 29.1 环境 API

- `check_env` 无错误；
- action/observation 始终在空间内；
- `reset(seed=x)` 可复现；
- `terminated` 和 `truncated` 语义正确。

### 29.2 守恒

对每个 episode：

\[
\text{arrived inference work}
=
\text{completed}
+
\text{remaining queue}
+
\text{explicitly failed/dropped}.
\]

\[
\text{arrived batch work}
=
\text{completed}
+
\text{remaining backlog}
+
\text{deadline-missed but accounted work}.
\]

模拟误差应在浮点容差内，例如相对误差 `< 1e-6`。

### 29.3 物理 sanity checks

- `active_batch_gpus=0` 时 batch throughput 为 0；
- 降低 power cap 不应稳定地产生更高最大功率；
- 请求率提高时队列/延迟不应系统性下降；
- 所有 GPU 功率非负且不高于执行上限；
- PCC 功率与分项之和一致；
- DR 结束后 backlog 不会自动清零。

### 29.4 基线 sanity checks

- 无 DR 时 no-control 完成量最高或接近最高；
- 极低 PCC limit 下所有方法都可能不可行，环境应报告 infeasible 而不是伪造成功；
- 使用完美未来的 oracle 不应差于同模型的普通 MPC；
- Rule-based 在最简单事件上必须比 no-control 更少超限。

### 29.5 HIL 安全

- 断开 controller 后 10 秒内恢复安全状态；
- actuator 拒绝越界功率；
- 非白名单 GPU 不能被控制；
- 恢复脚本在进程崩溃后仍可独立执行；
- 原始 telemetry 不被覆盖。

运行：

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src/aidrbench
```

---

## 30. 配置示例

```yaml
# configs/env/v0_discrete.yaml
seed: 42
backend: emulator

time:
  control_step_seconds: 60
  internal_step_seconds: 10
  episode_hours: 24

community:
  source: data/processed/community_load.parquet
  pv_enabled: false
  virtual_dc_share_of_peak: 0.25

workload:
  inference_source: data/processed/inference_requests.parquet
  batch_source: data/processed/batch_jobs.parquet
  inference_time_scale: 1.0
  batch_arrival_scale: 1.0

fleet:
  virtual_nodes: auto
  inference_gpus_per_node: [0, 1]
  batch_gpus_per_node: [2, 3]
  facility_overhead_mode: none

surrogate:
  model_dir: models/hardware_surrogates/v0
  stochastic_residuals: true

observation:
  community_forecast_minutes: [15, 30, 60]
  deadline_buckets_minutes: [15, 30, 60, 120, 240]
  include_temperature: true

action:
  inference_cap_ratios: [0.70, 0.85, 1.00]
  batch_gpu_counts: [0, 1, 2]
  batch_cap_ratios: [0.60, 0.80, 1.00]

reward:
  dr_exceedance: 20.0
  sla_violation: 20.0
  deadline_miss: 20.0
  backlog: 1.0
  energy: 0.1
  action_switch: 0.05
  rebound: 5.0

slo:
  ttft_p99_ms: 2000
  tpot_p99_ms: 100

rebound:
  observation_minutes: 60

logging:
  save_step_records: true
  output_format: parquet
```

SLO 数值必须根据所选模型和硬件基线重新设定；上面的数值只是配置格式示例，不是设备通用标准。

---

## 31. 结果目录与不可变性

每次实验目录：

```text
results/evaluation/<experiment_id>/
├── manifest.yaml
├── git_commit.txt
├── uv_lock.sha256
├── data_manifest.yaml
├── controller_config.yaml
├── environment_config.yaml
├── episode_metrics.parquet
├── step_metrics.parquet
├── summary.json
└── logs/
```

`experiment_id` 建议：

```text
YYYYMMDD_HHMMSS_<controller>_<split>_<seed>_<short_hash>
```

一旦结果用于论文，不再覆盖；新运行生成新目录。

---

## 32. 论文最低结果集

### Figure 1：平台架构

- 社区/PCC；
- inference queue；
- batch queue；
- emulator 与 HIL；
- common controller interface。

### Figure 2：四卡节点实测表面

- power cap—node power；
- power cap—throughput；
- request rate—p99 TTFT；
- mixed workload 对功率和性能的影响。

### Figure 3：一个典型 DR 事件

同图展示：

- PCC limit；
- no-control、RBC、MPC、最佳 RL 的功率；
- inference latency；
- batch backlog；
- 事件后 rebound。

### Figure 4：综合 Pareto

横轴：DR 未履约或超限；  
纵轴：SLA/deadline 代价；  
点大小或颜色：能耗/切换次数。

### Figure 5：泛化

- 未见社区；
- 未见 DR；
- 高请求率；
- 第二个模型。

### Figure 6：Sim-to-real

- 预测与实测功率；
- 预测与实测 TTFT；
- controller ranking；
- 约束违约变化。

### Table 1：平台和数据

### Table 2：主算法结果

### Table 3：HIL 结果

### Table 4：消融和敏感性

---

## 33. 建议论文标题

平台型：

> **AIDRBench: A Hardware-Calibrated Benchmark for Demand-Responsive AI Data Centers**

强调服务器在环：

> **Benchmarking Rule-Based, Model-Predictive and Reinforcement Learning Control for AI Data Center Demand Response with Server-in-the-Loop Validation**

强调混合工作负荷：

> **Demand-Responsive AI Computing under Mixed Online and Delay-Tolerant Workloads: A Hardware-Calibrated Control Benchmark**

第一篇不要把标题写成“Safe Reinforcement Learning…”，除非确实完成并验证了新的安全算法。

---

## 34. 实施路线与完成定义

### P0：仓库和系统检查

完成：

- README 入库；
- 独立 Conda 环境从锁文件同步成功；
- Docker GPU 测试成功；
- 系统信息和 power defaults 已保存；
- `pytest` 可以运行空测试。

### P1：数据管道

完成：

- BurstGPT 转为 Parquet；
- Alibaba job/task 转为标准 batch schema；
- 一个真实或合成社区 profile；
- DR event manifest；
- 时间切分和 hash 可复现。

### P2：硬件标定

完成：

- vLLM smoke；
- AIPerf BurstGPT replay；
- 1 秒 GPU telemetry；
- 最好有 PDU；
- 至少 30 个 calibration configurations；
- surrogate 在 held-out configs 上通过阈值。

### P3：环境

完成：

- `AIDRBench-v0` 注册；
- request/backlog 守恒；
- 27 动作；
- reward 与 raw KPI；
- no-control 和 RBC 可连续运行 30 天模拟；
- 所有环境测试通过。

### P4：控制器 benchmark

完成：

- MPC、DQN、A2C、PPO；
- 5 seeds；
- 固定 validation/test；
- 主 simulation figures；
- 统计分析。

### P5：Server-in-the-loop

完成：

- allow-listed actuator；
- watchdog；
- frozen policies；
- 至少 6 个场景 × 3 repetitions；
- sim-to-real gap 分析。

### P6：论文

完成：

- code release；
- data manifest 和引用；
- reproducibility script；
- paper figures 自动生成；
- 所有 claim 与测量边界一致。

---

## 35. 常见问题

### 35.1 为什么不直接使用 OpenG2G？

本项目的第一问题是数据中心能否响应功率目标，而不是节点电压控制。完整配电网会增加潮流、调压器和拓扑复杂性，却不能替代对 inference SLA、batch deadline、power cap 和 rebound 的精确建模。后续可以把策略接到 OpenDSS 做附加验证，但不是 V0 核心。

### 35.2 为什么需要 MPC？

MPC 是重要的非学习基线，可以判断 RL 提升是否真正来自处理随机性和长期 backlog，而不是因为 rule-based 太弱。MPC 不必成为新贡献。

### 35.3 为什么 V0 用离线推理而不是训练？

离线推理能保留可延迟计算的核心性质，同时降低 checkpoint、通信和恢复状态的复杂性。平台稳定后再加入 LoRA/训练作业。

### 35.4 为什么不能只用 `nvidia-smi` 功率？

它主要反映 GPU 板卡，不完整包含整机其他部件。需求响应论文最好测公共电源输入；没有 PDU 时必须缩小 claim。

### 35.5 为什么 RL 不直接在真实服务器训练？

探索动作会造成大量 SLA 违约、功率切换和不可控实验时间。先在实测代理模型中训练，再以冻结策略进行 HIL，既安全也便于公平比较。

### 35.6 RL 一定会优于 MPC 吗？

不一定。平台论文的可信结论可以是：在某些可预测场景中 MPC 更好，而 RL 在随机到达或连续 DR 中更稳健。不能预设赢家。

### 35.7 可以发表什么，即使 RL 没赢？

仍可发表：

- 新 benchmark；
- 四卡 AI 工作负荷实测数据；
- demand-response flexibility envelope；
- sim-to-real ranking；
- DR、SLA、deadline 和 rebound 的权衡；
- 现有控制器失效条件。

---

## 36. 必须避免的过度宣称

除非相应模块已真实测量，否则不要写：

- “完整数据中心 PUE/WUE 已实测”；
- “证明可以推迟配电网扩容”；
- “解决节点电压问题”；
- “真实 MW 级数据中心现场实验”；
- “真实生产 job deadlines”；
- “GPT-4 的实测能耗”；
- “RL 保证所有约束永不违反”。

可以准确写：

- 四 GPU 节点硬件标定；
- server-in-the-loop validation；
- virtual homogeneous fleet scaling；
- aggregate PCC demand response；
- scenario-generated deadlines；
- measured open-model serving power and performance；
- empirical constraint violation rate。

---

## 37. 参考资源

### 环境与 RL

- Gymnasium custom environments:  
  https://gymnasium.farama.org/introduction/create_custom_env/
- Stable-Baselines3 custom environments:  
  https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html
- Stable-Baselines3 RL tips:  
  https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html
- CVXPY solvers:  
  https://www.cvxpy.org/tutorial/solvers/index.html

### LLM 服务和 benchmark

- vLLM Docker:  
  https://docs.vllm.ai/en/latest/deployment/docker/
- NVIDIA AIPerf BurstGPT tutorial:  
  https://docs.nvidia.com/aiperf/tutorials/datasets-inputs/profile-with-burst-gpt-traces

### 数据

- BurstGPT:  
  https://github.com/HPMLL/BurstGPT
- Alibaba clusterdata:  
  https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020
- End-Use Load Profiles on AWS:  
  https://registry.opendata.aws/nrel-pds-building-stock/
- CityLearn:  
  https://www.citylearn.net/

### GPU 容器与遥测

- NVIDIA Container Toolkit:  
  https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- NVIDIA DCGM Exporter:  
  https://docs.nvidia.com/datacenter/dcgm/latest/installation/install-dcgm-exporter.html
- NVIDIA System Management Interface:  
  https://docs.nvidia.com/deploy/nvidia-smi/index.html
- uv:  
  https://docs.astral.sh/uv/

---

## 38. 最先执行的 10 条命令

当本 README 放到服务器后，先执行：

```bash
cd ~/projects/AIDRBench

nvidia-smi
nvidia-smi -L
nvidia-smi topo -m
nvidia-smi -q -d POWER > results_system_gpu_power.txt

docker run --rm --gpus all \
  nvidia/cuda:13.3.1-base-ubuntu24.04 nvidia-smi

curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv python install 3.12

mkdir -p data/raw/burstgpt
curl -L \
  https://raw.githubusercontent.com/HPMLL/BurstGPT/main/data/BurstGPT_1.csv \
  -o data/raw/burstgpt/BurstGPT_1.csv

export VLLM_IMAGE=vllm/vllm-openai:v0.27.0-cu129-ubuntu2404
docker pull "$VLLM_IMAGE"
```

然后按顺序完成：

```text
vLLM smoke → AIPerf 10-request replay → telemetry → calibration → surrogate → Gym env → RBC → MPC/RL → HIL
```
