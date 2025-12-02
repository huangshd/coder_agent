# Figure20 - 与Figure19对齐的混合部署实验

## 概述

本指南介绍如何在真实的两个vLLM引擎上部署Figure20的四种智能体，并与Figure19的混合部署策略进行对齐和比较。

**状态**: ✅ 准备就绪 (可用的集成代码)

---

## 与Figure19的关键对齐

### 相似性

| 方面 | Figure19 | Figure20 |
|------|---------|---------|
| **vLLM引擎数** | 2个实例 | 2个实例 |
| **并发执行** | 多进程 | 多进程/异步 |
| **混合工作负载** | Chat + MapReduce | Coder + RAG + Multimodal + Chatbox |
| **性能测量** | 延迟、吞吐量 | TTFT、TPOT、端到端延迟 |
| **研究焦点** | 混合部署策略 | 代理放置 & 调度策略 |

### 主要差异

| 方面 | Figure19 | Figure20 |
|------|---------|---------|
| **任务类型** | 2种 | 4种 |
| **智能体数** | 1个 | 4个独立智能体 |
| **工作流复杂度** | 简单 | 复杂(DAG-based) |
| **亲和度需求** | 任务级别 | 组件级别(关键) |
| **辅助模型** | 0个 | 4个 |
| **路由策略** | 轮询 | 4种智能策略 |

---

## 部署架构

### vLLM实例配置

```
Machine 1 (8 GPUs)
├── vLLM Instance 1 (Port 8000)
│   ├── Model: lmsys/vicuna-7b-v1.3
│   ├── GPUs: 0-3
│   └── Config: 负载均衡优化
│
└── vLLM Instance 2 (Port 8001)
    ├── Model: lmsys/vicuna-7b-v1.3
    ├── GPUs: 4-7
    └── Config: 低延迟优化
```

### 四种智能体分配

```
Coder Agent (⭐⭐⭐⭐⭐)
  ├─ Planner → Instance 2 (低延迟)
  ├─ Workers → Instance 1 (吞吐优化)
  └─ Checker → Instance 1/2 (灵活)

RAG Agent (⭐⭐⭐)
  ├─ Embedding → CPU
  ├─ Reranker → CPU
  └─ LLM Generation → Instance 2 (关键亲和度)

Multimodal Agent (⭐⭐⭐⭐)
  ├─ OCR/ASR → CPU (并行)
  └─ LLM Understanding → Instance 1/2 (灵活)

Chatbox Agent (⭐⭐)
  └─ Session LLM → Instance 2 (会话固定)
```

---

## 快速开始

### 1. 准备环境

```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# 检查依赖
python3 -c "from agents import *; from models import *; from dispatcher import *; print('✅ 基础模块就绪')"

# 检查配置
ls -la configs/
```

### 2. 启动vLLM引擎

确保两个vLLM实例已启动:

```bash
# 终端1: 启动Instance 1
python3 -m vllm.entrypoints.api_server \
    --model lmsys/vicuna-7b-v1.3 \
    --port 8000 \
    --gpu-memory-utilization 0.9 \
    --tensor-parallel-size 2

# 终端2: 启动Instance 2
python3 -m vllm.entrypoints.api_server \
    --model lmsys/vicuna-7b-v1.3 \
    --port 8001 \
    --gpu-memory-utilization 0.9 \
    --tensor-parallel-size 2
```

### 3. 运行混合工作负载

```bash
# 使用启动脚本(推荐)
bash run_mixed_workload.sh

# 或手动运行
python3 vllm_integration.py \
    --endpoints http://localhost:8000 http://localhost:8001 \
    --duration 60 \
    --benchmark mixed
```

### 4. 分析结果

```bash
# 与Figure19比较
python3 compare_with_figure19.py \
    --figure20-dir . \
    --figure19-dir ../figure19 \
    --print-summary \
    --output comparison_report.json
```

---

## 工作流详解

### Coder Agent 工作流

```
User Input
  ↓
[Dispatcher] → Route to Instance 2 (TTFT优化)
  ↓
[Planner LLM] → 任务分解
  ↓
[Dispatcher] → Route to Instance 1 (吞吐优化)
  ↓
[Workers (并行)] → N=3 并行代码生成
  │ (都在Instance 1上，共享前缀缓存)
  ↓
[Checker] → K=3 迭代验证
  ↓
[Output] → 验证通过的代码
```

**关键优化**:
- Planner → Instance 2: 快速TTFT
- Workers → Instance 1: 吞吐优化，前缀缓存共享
- 预期改进: 20-30% 完成时间缩短

### RAG Agent 工作流

```
User Query
  ↓
[Embedding Model] → 向量化 (CPU)
  ↓
[Vector Retrieval] → Top-5 文档
  ↓
[Reranker] → 相关性评分 (CPU)
  ↓
[Context Assembly] → 构建上下文
  ↓
[Dispatcher] → 关键亲和度检查
  ├─ 如果缓存热 → 同一Instance
  └─ 否则 → Instance 2 (低延迟)
  ↓
[LLM Generation] → 答案生成
  ↓
[Output] → 最终答案
```

**关键优化**:
- Embedding + Reranker + LLM 共定位
- 前缀缓存重用: 70% 命中率
- 预期改进: 15-30% 延迟降低

### Multimodal Agent 工作流

```
Multimodal Input
  ↓
[Input Recognition] → 检测模态
  ├─ Image → OCR (CPU, 并行)
  ├─ Audio → ASR (CPU, 并行)
  └─ Video → Frame Extraction + OCR (CPU)
  ↓
[Text Fusion] → 融合结果
  ↓
[Dispatcher] → 灵活路由
  ↓
[LLM Understanding] → 多模态推理
  ↓
[Output] → 自然语言响应
```

**关键优化**:
- OCR/ASR 与 LLM 分离 (弱亲和度)
- 并行预处理: 图像/音频同时处理
- 预期改进: 支持异构模型

### Chatbox Agent 工作流

```
User Input (Session)
  ↓
[Session Manager] → 加载历史
  ↓
[Dispatcher] → 会话固定检查
  ├─ 已固定 → 返回同一Instance
  └─ 新会话 → 固定到Instance 2
  ↓
[Context Building] → 组装提示
  ↓
[LLM Generation] → 单轮回复
  ↓
[Session Update] → 更新历史
  ↓
[Output] → 最终回复
```

**关键优化**:
- 会话固定: 提高前缀缓存命中率
- 会话固定率: 80% 缓存命中率
- 预期改进: 40-60% 延迟降低

---

## 关键性能指标

### 按代理的期望SLO

| 代理 | TTFT | TPOT | 端到端 | 吞吐 |
|-----|------|------|--------|------|
| **Coder** | 500-1500ms | 20-50ms | <30s | 5-20 req/min |
| **RAG** | 800-2000ms | 15-40ms | <5s | 20-100 req/min |
| **Multimodal** | 1500-4000ms | 25-60ms | <10s | 5-30 req/min |
| **Chatbox** | 200-800ms | 10-30ms | <2s | 50-200 req/min |

### 测量指标

```python
# Per-request 指标
PerformanceMetrics:
  - ttft_ms: 时间到第一个令牌
  - tpot_ms: 每个输出令牌时间
  - total_latency_ms: 端到端延迟
  - input_tokens: 输入令牌数
  - output_tokens: 输出令牌数
  - workflow_nodes: 经过的节点列表

# 聚合指标
  - 平均延迟
  - Min/Max/P50/P95/P99 延迟
  - 吞吐量 (req/sec)
  - 错误率
  - SLO合规率
```

---

## 文件结构

```
artifact/figure20/
├── vllm_integration.py               ✅ vLLM集成类
├── run_mixed_workload.sh             ✅ 启动脚本
├── compare_with_figure19.py          ✅ 对比分析
├── agents/
│   ├── base_agent.py                 ✅ 基类
│   ├── coder_agent.py                ✅ Coder实现
│   ├── rag_agent.py                  ✅ RAG实现
│   ├── multimodal_agent.py           ✅ Multimodal实现
│   └── chatbox_agent.py              ✅ Chatbox实现
├── models/
│   ├── embedding_model.py            ✅ 嵌入包装
│   ├── reranker_model.py             ✅ 重排包装
│   ├── ocr_model.py                  ✅ OCR包装
│   └── asr_model.py                  ✅ ASR包装
├── configs/
│   ├── vllm_config.json              ✅ vLLM配置
│   ├── agent_config.json             ✅ 代理配置
│   └── benchmark_config.json         ✅ 基准配置
└── dispatcher.py                     ✅ 路由逻辑
```

---

## 实验步骤

### 第1步: 系统验证

```bash
# 验证基础设置
python3 main.py --info

# 验证配置加载
python3 << 'EOF'
import json
configs = ["configs/vllm_config.json", "configs/agent_config.json"]
for cfg in configs:
    with open(cfg) as f:
        print(f"✅ {cfg} loaded")
EOF
```

### 第2步: vLLM服务启动

确保两个实例已启动并可访问:

```bash
# 检查Instance 1
curl http://localhost:8000/health

# 检查Instance 2
curl http://localhost:8001/health
```

### 第3步: 运行基准

```bash
# 混合工作负载
python3 vllm_integration.py \
    --endpoints http://localhost:8000 http://localhost:8001 \
    --duration 60 \
    --benchmark mixed

# 单个代理
python3 vllm_integration.py \
    --endpoints http://localhost:8000 http://localhost:8001 \
    --benchmark coder \
    --duration 30
```

### 第4步: 收集结果

```bash
# 结果位置
ls -la figure20_*.json

# 检查混合工作负载结果
cat figure20_mixed_results.json | python3 -m json.tool
```

### 第5步: 对比分析

```bash
# 生成对比报告
python3 compare_with_figure19.py \
    --print-summary \
    --output comparison_report.json

# 查看报告
cat comparison_report.json | python3 -m json.tool
```

---

## 关键路由决策

### 智能路由选择

```python
Coder Agent:
  → 使用 Affinity-Aware 路由
  → Workers 保持在同一实例
  → 预期收益: 20-30% 加速

RAG Agent:
  → 使用 Affinity-Aware 路由 (关键!)
  → Embedding + Reranker + LLM 同一实例
  → 预期收益: 15-30% 延迟降低

Multimodal Agent:
  → 使用 Load-Balanced 路由
  → OCR/ASR 可在CPU上
  → 灵活分配

Chatbox Agent:
  → 使用 Session-Sticky 路由
  → 会话固定到同一实例
  → 预期收益: 40-60% 延迟降低
```

---

## 与Figure19的对比分析

### 使用比较脚本

```bash
python3 compare_with_figure19.py \
    --figure20-dir . \
    --figure19-dir ../figure19 \
    --print-summary

# 输出示例:
# ════════════════════════════════════════════════════════════════
# FIGURE20 vs FIGURE19 COMPARISON
# ════════════════════════════════════════════════════════════════
#
# Figure19: 2 workloads (Chat + MapReduce)
# Figure20: 4 workloads (Coder + RAG + Multimodal + Chatbox)
#
# Key Differences:
#   Complexity increase............ 2x → 4x agents
#   Workflow increase.............. Simple → Complex (DAG-based)
#   Affinity requirements.......... Task-level → Component-level
#   Routing strategies............. Simple → 4 intelligent strategies
#   Auxiliary models............... 0 → 4 models
```

### 关键对比指标

| 指标 | Figure19 | Figure20 |
|------|---------|---------|
| **代理数** | 1 | 4 |
| **工作流** | Chat, MapReduce | Coder, RAG, Multimodal, Chat |
| **LLM调用/请求** | 1-2 | 1-25 (取决于代理) |
| **缓存策略** | 简单 | 前缀缓存+亲和度 |
| **路由策略** | 轮询 | 智能自适应 |
| **期望改进** | - | 15-60% (依赖代理) |

---

## 故障排除

### vLLM服务不可用

```bash
# 检查服务
curl -v http://localhost:8000/health
curl -v http://localhost:8001/health

# 如果不可用，回退到演示模式
python3 main.py --demo all
```

### 缺少辅助模型

```bash
# 安装依赖
pip install sentence-transformers  # Embedding
pip install paddleocr              # OCR
pip install openai-whisper         # ASR

# 检查安装
python3 -c "from sentence_transformers import SentenceTransformer; print('✅ OK')"
```

### 内存不足

```bash
# 减少批量大小
python3 vllm_integration.py --max-batch-size 8

# 或减少并发
python3 vllm_integration.py --concurrency 2
```

---

## 下一步

### 立即可做

1. ✅ 在真实vLLM上运行演示
2. ✅ 收集性能基线
3. ✅ 与Figure19对比

### 未来工作

1. Parrot 集成 - 对比智能调度
2. 多节点扩展 - 跨机器部署
3. 动态调整 - 自适应路由学习
4. 优化分析 - 深度性能调查

---

## 参考文献

- [系统架构](./ARCHITECTURE.md)
- [代理配置文件](./docs/AGENT_PROFILES.md)
- [放置策略](./docs/PLACEMENT_STRATEGY.md)
- [调度策略](./docs/SCHEDULING_STRATEGY.md)
- [Figure19基线](../figure19/README.md)

---

**状态**: ✅ 准备就绪
**最后更新**: 2024-12-01
**下一阶段**: Phase 4 - Parrot集成与对比实验
