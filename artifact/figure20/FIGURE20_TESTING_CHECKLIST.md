# Figure20 测试脚本补充总结

## 执行的对比分析

对比了 Figure19 和 Figure20 的测试框架，确保 Figure20 的 Coder Agent 能够正确运行。

## 新增的文件

### 1. 端到端测试脚本

#### `run_coder_full.sh` - 单个 Coder Agent 完整测试
**路径**: `/home/mo/Project/parrot/ParrotServe/artifact/figure20/run_coder_full.sh`

**功能**:
- 自动启动/停止 vLLM 后端（复用 Figure19 的 dual-worker 设置）
- 设置环境变量 `VLLM_REQ_TRACK=1`
- 运行 2 轮测试以获得统计显著性
- 自动清理日志和进程
- 解析结果到 `result_coder_vllm.txt`

**类似于**: `artifact/figure19/run_vllm_lat.sh`

**使用方法**:
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20
./run_coder_full.sh
```

#### `run_mixed_full.sh` - 多 Agent 混合负载完整测试
**路径**: `/home/mo/Project/parrot/ParrotServe/artifact/figure20/run_mixed_full.sh`

**功能**:
- 同时运行 4 个 agent（Coder、RAG、Multimodal、Chatbox）
- 2 轮迭代测试
- 自动启动/停止后端
- 解析每个 agent 的结果并计算聚合统计
- 输出到 `result_mixed_agents.txt`

**使用方法**:
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20
./run_mixed_full.sh
```

### 2. 结果解析脚本

#### `parse_coder_results.py` - Agent 结果解析器
**路径**: `/home/mo/Project/parrot/ParrotServe/artifact/figure20/parse_coder_results.py`

**功能**:
- 解析 agent benchmark 的 JSON 输出
- 提取关键指标：
  - 总请求数、成功率
  - 吞吐量（req/s）
  - 平均延迟、P50、P99 延迟
  - TTFT（Time To First Token）
  - TPOT（Time Per Output Token）
- 如果可用，解析 worker 日志获取底层时序信息
- 格式化输出，便于与 Figure19 对比

**类似于**: `artifact/figure19/parse_vllm_time.py`

### 3. 配置文件

#### `configs/workload_config.json` - 混合负载配置
**路径**: `/home/mo/Project/parrot/ParrotServe/artifact/figure20/configs/workload_config.json`

**功能**:
- 定义每个 agent 的默认请求数和速率
- 指定 vLLM 端点和模型路由名称
- 定义异构部署策略（类似 Figure19）
  - Worker 1 (GPU 0): 高吞吐（Coder、Multimodal）
  - Worker 2 (GPU 1): 低延迟（RAG、Chatbox）
- 提供预设的轻/中/重负载配置

**新增的**（原来引用但不存在）

### 4. 文档

#### `TESTING_INFRASTRUCTURE_COMPARISON.md` - 详细对比文档
**路径**: `/home/mo/Project/parrot/ParrotServe/artifact/figure20/TESTING_INFRASTRUCTURE_COMPARISON.md`

**内容**:
- Figure19 vs Figure20 架构对比
- 测试基础设施组件逐项对比
- 关键差异分析
- 缺失组件检查清单
- 测试步骤和验证清单
- 改进建议

---

## 检查清单：确认 Figure20 已就绪

### ✅ 已完成

1. **后端启动脚本**
   - ✅ 复用 `artifact/fastchat_scripts/launch_vllm_7b_dual.sh`
   - ✅ 支持双 worker 部署（GPU 0 高吞吐 + GPU 1 低延迟）

2. **端到端测试脚本**
   - ✅ `run_coder_full.sh` - 单 agent 测试
   - ✅ `run_mixed_full.sh` - 多 agent 测试
   - ✅ 支持多轮迭代
   - ✅ 自动清理和结果记录

3. **Workload 启动器**
   - ✅ `start_benchmark_coder.py` - 单 agent
   - ✅ `start_benchmark_mixed.py` - 混合负载
   - ✅ 使用 multiprocessing.Barrier 同步

4. **Agent Benchmark 实现**
   - ✅ `benchmarks/benchmark_coder.py` - 已存在
   - ✅ `benchmarks/benchmark_rag.py` - 已存在
   - ✅ `benchmarks/benchmark_chatbox.py` - 已存在
   - ✅ `benchmarks/benchmark_multimodal.py` - 已存在
   - ✅ `benchmarks/benchmark_all.py` - 已存在

5. **结果解析**
   - ✅ `parse_coder_results.py` - 新创建
   - ✅ 支持 JSON 和日志解析
   - ✅ 输出格式与 Figure19 对齐

6. **配置文件**
   - ✅ `configs/agent_config.json` - 已存在
   - ✅ `configs/benchmark_config.json` - 已存在
   - ✅ `configs/vllm_config.json` - 已存在
   - ✅ `configs/workload_config.json` - 新创建

7. **辅助脚本**
   - ✅ `quick_start.sh` - 交互式测试脚本（已存在）
   - ✅ `run_mixed_workload.sh` - 混合负载脚本（已存在）

### 📋 测试前检查项

在运行测试前，请确认：

1. **环境准备**
   ```bash
   # 检查 GPU 可用性
   nvidia-smi

   # 检查 Python 依赖
   pip list | grep -E "(vllm|fastchat|langchain|transformers)"

   # 检查 kill 脚本存在
   ls ../../scripts/kill_all_fastchat_servers.sh
   ```

2. **数据集准备**
   ```bash
   # 检查 ShareGPT 数据集
   ls ../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json

   # Figure19 的 arxiv 数据集（MR 需要）
   ls ../workloads/arxiv-march-2023/arxiv-sampled/article_0.txt
   ```

3. **目录结构**
   ```bash
   cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

   # 创建结果目录
   mkdir -p ./results
   mkdir -p ./logs
   ```

4. **脚本权限**
   ```bash
   chmod +x run_coder_full.sh
   chmod +x run_mixed_full.sh
   chmod +x parse_coder_results.py
   chmod +x quick_start.sh
   chmod +x run_mixed_workload.sh
   ```

---

## 与 Figure19 的对比

### 相同点

| 组件 | Figure19 | Figure20 |
|------|----------|----------|
| 后端架构 | Dual vLLM workers | ✅ 相同 |
| 启动脚本 | `launch_vllm_7b_dual.sh` | ✅ 复用 |
| 环境变量 | `VLLM_REQ_TRACK=1` | ✅ 相同 |
| API 设置 | `OPENAI_API_BASE/KEY` | ✅ 相同 |
| 清理脚本 | `kill_all_fastchat_servers.sh` | ✅ 复用 |
| 测试轮数 | 2 次迭代 | ✅ 相同 |

### 差异点

| 方面 | Figure19 | Figure20 |
|------|----------|----------|
| **Workload** | Chat + Map-Reduce (2 类) | Coder + RAG + Multimodal + Chatbox (4 类) |
| **并发模式** | 2 进程并行 | 4 进程并行 |
| **实现框架** | LangChain Map-Reduce | Agent 工作流（prompt chain） |
| **指标重点** | JCT、normalized latency | TTFT、TPOT、agent throughput |
| **模型路由** | `map` / `latency` 明确区分 | 通用 `gpt-3.5-turbo` 名称 |

---

## 使用示例

### 1. 快速测试（使用 Mock LLM）
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# 测试单个 Coder agent（不需要后端）
python3 benchmarks/benchmark_coder.py \
    --num-requests 10 \
    --concurrency 2 \
    --use-mock \
    --output ./results/test_mock.json
```

### 2. 单 Coder Agent 完整测试
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# 运行完整测试（自动启动/停止后端）
./run_coder_full.sh

# 查看结果
cat result_coder_vllm.txt
cat ./results/coder_results_run1.json | python3 -m json.tool
```

### 3. 混合 Agent 负载测试
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# 运行所有 4 个 agent
./run_mixed_full.sh

# 查看聚合结果
cat result_mixed_agents.txt

# 查看各 agent 详细结果
for agent in coder rag chatbox multimodal; do
    echo "=== $agent ==="
    cat ./results/${agent}_results.json | jq '.summary'
done
```

### 4. 交互式测试
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# 使用交互式脚本选择测试类型
./quick_start.sh
```

### 5. 对比 Figure19 结果
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# 查看 Figure19 结果
cat ../figure19/result_vllm_dual.txt

# 查看 Figure20 结果
cat result_coder_vllm.txt

# 对比差异
diff -u ../figure19/result_vllm_dual.txt result_coder_vllm.txt
```

---

## 预期输出示例

### run_coder_full.sh 的输出
```
════════════════════════════════════════════════════════════════
Test Coder Agent: vLLM Backend [1 / 2]
════════════════════════════════════════════════════════════════
Starting vLLM workers...
Waiting for services to initialize...
Running Coder Agent benchmark...
Parsing results...
Run 1 results:
  Total requests: 50
  Throughput: 2.34 req/s
  Avg latency: 4567.89 ms
  P99 latency: 8901.23 ms
Run 1 completed

════════════════════════════════════════════════════════════════
ALL TESTS COMPLETE
════════════════════════════════════════════════════════════════
Results saved to: result_coder_vllm.txt
```

### result_coder_vllm.txt 的内容
```
Run 1 results:
  Total requests: 50
  Throughput: 2.34 req/s
  Avg latency: 4567.89 ms
  P99 latency: 8901.23 ms

Run 2 results:
  Total requests: 50
  Throughput: 2.41 req/s
  Avg latency: 4321.56 ms
  P99 latency: 8654.32 ms
```

---

## 潜在问题及解决方案

### 问题 1: vLLM 启动失败
**症状**: `ERROR: vLLM service not responding`

**解决**:
```bash
# 检查 GPU 内存
nvidia-smi

# 手动启动 vLLM 测试
bash ../fastchat_scripts/launch_vllm_7b_dual.sh

# 查看错误日志
cat fschat_controller_stdout.log
cat worker_vllm_throughput_stdout.log
```

### 问题 2: 找不到数据集
**症状**: `Warning: Failed to load dataset`

**解决**:
```bash
# 检查数据集路径
ls ../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json

# 如果不存在，使用合成数据
python3 benchmarks/benchmark_coder.py --num-requests 10 # 不指定 --dataset
```

### 问题 3: Agent benchmark 文件不存在
**症状**: `benchmarks/benchmark_rag.py not found`

**解决**:
```bash
# 检查所有 benchmark 文件
ls -la benchmarks/benchmark_*.py

# 如果缺失，先测试 Coder agent
./run_coder_full.sh
```

### 问题 4: 端口被占用
**症状**: `Address already in use: 8000`

**解决**:
```bash
# 杀死所有 FastChat 进程
bash ../../scripts/kill_all_fastchat_servers.sh

# 或手动杀死
pkill -f fastchat
pkill -f vllm
```

---

## 总结

### ✅ 已完成的工作

1. **创建了 3 个新文件**:
   - `run_coder_full.sh` - 单 agent 端到端测试
   - `run_mixed_full.sh` - 多 agent 端到端测试
   - `parse_coder_results.py` - 结果解析器

2. **补充了 1 个配置文件**:
   - `configs/workload_config.json` - 混合负载配置

3. **编写了 2 个文档**:
   - `TESTING_INFRASTRUCTURE_COMPARISON.md` - 详细技术对比
   - `FIGURE20_TESTING_CHECKLIST.md` - 本文档（测试清单）

4. **验证了所有依赖**:
   - ✅ 所有 4 个 agent benchmark 文件已存在
   - ✅ 所有必需的配置文件已存在
   - ✅ 后端启动脚本可以复用

### 🎯 Figure20 现在具备的能力

- ✅ 与 Figure19 **功能对等** 的测试框架
- ✅ 自动化的端到端测试流程
- ✅ 统一的结果解析和报告
- ✅ 支持单 agent 和混合负载测试
- ✅ 完整的配置管理
- ✅ 详细的文档和使用说明

### 🚀 下一步建议

1. **运行基础测试**:
   ```bash
   # 使用 Mock LLM 验证流程
   python3 benchmarks/benchmark_coder.py --use-mock --num-requests 5
   ```

2. **运行单 agent 测试**:
   ```bash
   ./run_coder_full.sh
   ```

3. **分析结果并对比 Figure19**:
   ```bash
   cat result_coder_vllm.txt
   cat ../figure19/result_vllm_dual.txt
   ```

4. **运行完整混合负载测试**:
   ```bash
   ./run_mixed_full.sh
   ```

5. **性能分析和优化**:
   - 对比不同 agent 的延迟特性
   - 调整模型路由策略
   - 优化并发和请求速率

---

## 参考文件清单

### Figure19 参考文件
- `artifact/figure19/run_vllm_lat.sh` - 端到端测试脚本
- `artifact/figure19/start_benchmark_vllm.py` - Workload 启动器
- `artifact/figure19/benchmark_mr_serving_vllm.py` - MR 实现
- `artifact/figure19/parse_vllm_time.py` - 结果解析器
- `artifact/fastchat_scripts/launch_vllm_7b_dual.sh` - 后端启动

### Figure20 新文件
- `artifact/figure20/run_coder_full.sh` - 单 agent 测试
- `artifact/figure20/run_mixed_full.sh` - 混合测试
- `artifact/figure20/parse_coder_results.py` - 结果解析
- `artifact/figure20/configs/workload_config.json` - 负载配置

### Figure20 已存在文件
- `artifact/figure20/start_benchmark_coder.py`
- `artifact/figure20/start_benchmark_mixed.py`
- `artifact/figure20/benchmarks/benchmark_*.py` (所有 4 个 agent)
- `artifact/figure20/configs/*.json` (所有配置文件)
