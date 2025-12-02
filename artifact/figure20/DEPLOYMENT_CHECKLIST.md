# Figure20 部署清单与Figure19对齐

## 📋 部署前准备

### 环境检查
- [ ] Python 3.7+ 已安装
- [ ] pip 已安装
- [ ] 8个GPU可用
- [ ] CUDA已配置

### 依赖安装
```bash
pip install vllm langchain asyncio
pip install sentence-transformers transformers torch
pip install paddleocr openai-whisper
pip install faiss-cpu  # 或 pinecone-client
```

### 代码检查
- [x] 所有5个代理类已实现 (base, coder, rag, multimodal, chatbox)
- [x] 所有4个模型包装已实现 (embedding, reranker, ocr, asr)
- [x] dispatcher.py - 4种路由策略已实现
- [x] vllm_integration.py - 真实vLLM集成已实现

### 配置检查
- [x] configs/vllm_config.json - 4个异构实例定义
- [x] configs/agent_config.json - 4个代理配置
- [x] configs/benchmark_config.json - 基准参数

---

## 🚀 vLLM启动 (Figure19对齐)

### Instance 1 (低延迟) - Port 8000
```bash
python3 -m vllm.entrypoints.api_server \
    --model lmsys/vicuna-7b-v1.3 \
    --port 8000 \
    --gpu-memory-utilization 0.9 \
    --max-batch-size 16 \
    --tensor-parallel-size 1
```

验证: `curl http://localhost:8000/health`

- [ ] Instance 1 已启动

### Instance 2 (吞吐优化) - Port 8001
```bash
python3 -m vllm.entrypoints.api_server \
    --model lmsys/vicuna-7b-v1.3 \
    --port 8001 \
    --gpu-memory-utilization 0.9 \
    --max-batch-size 32 \
    --tensor-parallel-size 2
```

验证: `curl http://localhost:8001/health`

- [ ] Instance 2 已启动

---

## 🧪 系统验证

### 基础验证 (无需vLLM)
```bash
cd /home/mo/Project/parrot/ParrotServe/artifact/figure20

# 验证模块导入
python3 main.py --info

# 演示模式
python3 main.py --demo all
```

- [ ] 系统初始化成功
- [ ] 所有代理加载成功

### vLLM集成验证
```bash
# 与真实vLLM集成
python3 vllm_integration.py \
    --endpoints http://localhost:8000 http://localhost:8001 \
    --duration 30 \
    --benchmark mixed
```

- [ ] vLLM 集成正常

---

## 📊 基准测试

### 混合工作负载基准 (推荐)
```bash
bash run_mixed_workload.sh

# 或手动运行
python3 vllm_integration.py \
    --endpoints http://localhost:8000 http://localhost:8001 \
    --duration 60 \
    --benchmark mixed
```

- [ ] 混合工作负载完成

### 结果收集
```bash
# 验证结果文件
ls -la figure20_*.json

# 检查混合结果
cat figure20_mixed_results.json | python3 -m json.tool
```

- [ ] 结果文件已生成

---

## 📈 对比分析

### 与Figure19对比
```bash
python3 compare_with_figure19.py \
    --figure20-dir . \
    --figure19-dir ../figure19 \
    --print-summary \
    --output comparison_report.json
```

- [ ] 对比报告已生成

---

## ✅ 最终检查

- [x] 所有代理实现完毕
- [x] 所有模型包装完毕
- [x] dispatcher.py 完整
- [x] vllm_integration.py 可用
- [x] 配置文件完整
- [ ] vLLM 服务已启动
- [ ] 系统验证通过
- [ ] 基准测试完成
- [ ] 对比分析完成

---

## 📝 关键指标

### 期望性能 (基线)
| 代理 | TTFT | 延迟 | 吞吐 |
|-----|------|------|------|
| Coder | 500-1500ms | <30s | 5-20 req/min |
| RAG | 800-2000ms | <5s | 20-100 req/min |
| Multimodal | 1500-4000ms | <10s | 5-30 req/min |
| Chatbox | 200-800ms | <2s | 50-200 req/min |

### 实际性能 (待测试)
| 代理 | 实际TTFT | 实际延迟 | 实际吞吐 |
|-----|---------|---------|--------|
| Coder | _________ | _________ | _________ |
| RAG | _________ | _________ | _________ |
| Multimodal | _________ | _________ | _________ |
| Chatbox | _________ | _________ | _________ |

---

## 📚 文档索引

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统设计
- [GETTING_STARTED.md](./GETTING_STARTED.md) - 快速开始
- [FIGURE19_ALIGNMENT.md](./FIGURE19_ALIGNMENT.md) - 对齐指南
- [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) - 代理特性
- [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md) - 路由策略

---

**状态**: ✅ 准备就绪
**最后更新**: 2024-12-01
