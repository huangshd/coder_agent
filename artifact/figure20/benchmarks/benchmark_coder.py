# benchmark_improved_coder.py
# 改进版 Coder 工作流的基准测试程序

import argparse
import asyncio
import json
import random
import time
from typing import AsyncGenerator, List, Optional
from dataclasses import asdict
from pathlib import Path
import sys

import numpy as np

# 导入 improved_coder_agent 模块
sys.path.append(str(Path(__file__).parent.parent))  # 添加项目根目录到路径
from agents.coder_agent import (
    ImprovedCoderAgent,
    ImprovedCoderMetrics
)
from agents.base_agent import AgentConfig


# 全局性能指标收集
WORKFLOW_METRICS: List[ImprovedCoderMetrics] = []


# ==================== 测试数据生成 ====================

def sample_requests(
    num_apps: int,
    prompts_file: Optional[str] = None
) -> List[str]:
    """生成测试请求（用户提示）"""
    
    base_prompts = [
        "创建一个Python程序，用于从API获取天气数据并存储到SQLite数据库",
        "实现一个简单的待办事项(Todo)应用，包含增删改查功能",
        "编写一个Python脚本，用于批量重命名文件夹中的图片文件",
        "创建一个Flask web应用，显示实时股票价格",
        "实现一个简单的机器学习模型，用于手写数字识别",
        "创建一个Python工具，用于监控网站可用性并发送告警",
        "编写一个数据可视化脚本，读取CSV文件并生成图表",
        "实现一个简单的聊天机器人，可以回答常见问题",
        "创建一个Python程序，用于自动化发送电子邮件报告",
        "实现一个简单的游戏，比如猜数字或井字棋",
        "实现一个文件处理工具，统计文本文件的行数、字数、字符数",
        "创建一个命令行工具，用于管理个人密码（加密存储）",
        "编写一个Python脚本，自动化备份指定文件夹到云存储",
        "实现一个简单的HTTP服务器，支持静态文件托管",
        "创建一个日志分析工具，从日志文件中提取关键信息",
        "实现一个markdown转HTML的转换工具",
        "编写一个网络爬虫，抓取指定网站的新闻标题",
        "创建一个系统监控脚本，定期检查CPU、内存使用率",
        "实现一个简单的任务调度器，按时间执行指定任务",
        "编写一个JSON数据验证工具，检查数据格式是否符合schema"
    ]
    
    if prompts_file and Path(prompts_file).exists():
        with open(prompts_file, 'r', encoding='utf-8') as f:
            file_prompts = [line.strip() for line in f if line.strip()]
        prompts = file_prompts[:num_apps] if len(file_prompts) >= num_apps else file_prompts
    else:
        prompts = []
        for i in range(num_apps):
            prompts.append(base_prompts[i % len(base_prompts)])
    
    return prompts


async def get_request(
    input_requests: List[str],
    request_rate: float,
) -> AsyncGenerator[str, None]:
    """生成请求流"""
    input_requests = iter(input_requests)
    for request in input_requests:
        yield request

        if request_rate == float("inf"):
            continue
        await asyncio.sleep(1.0 / request_rate)


# ==================== 基准测试执行 ====================

async def send_request(
    workflow_id: int,
    user_prompt: str,
    agent: ImprovedCoderAgent
) -> None:
    """发送单个工作流请求"""
    global WORKFLOW_METRICS
    
    try:
        input_data = {
            "user_prompt": user_prompt,
            "workflow_id": workflow_id
        }
        
        # 执行工作流
        final_code, base_metrics = await agent.execute(input_data)
        
        # 获取详细的 metrics
        if hasattr(agent, '_current_metrics'):
            metrics = agent._current_metrics
            WORKFLOW_METRICS.append(metrics)
        else:
            # 备用方案：创建基本的 metrics
            metrics = ImprovedCoderMetrics(
                workflow_id=workflow_id,
                total_latency=base_metrics.total_latency_ms,
                success=base_metrics.error is None
            )
            WORKFLOW_METRICS.append(metrics)
        
    except Exception as e:
        print(f"[工作流 {workflow_id}] 执行失败: {e}")
        failed_metrics = ImprovedCoderMetrics(
            workflow_id=workflow_id,
            success=False
        )
        WORKFLOW_METRICS.append(failed_metrics)


async def benchmark(
    input_requests: List[str],
    request_rate: float,
    agent: ImprovedCoderAgent
) -> None:
    """执行基准测试"""
    tasks: List[asyncio.Task] = []
    
    workflow_id = 0
    async for user_prompt in get_request(input_requests, request_rate):
        workflow_id += 1
        
        task = asyncio.create_task(
            send_request(
                workflow_id=workflow_id,
                user_prompt=user_prompt,
                agent=agent
            )
        )
        tasks.append(task)
    
    await asyncio.gather(*tasks)


# ==================== 结果保存和统计 ====================

def save_results_to_file(results_file: str = "improved_coder_benchmark_results.json"):
    """保存基准测试结果到文件"""
    global WORKFLOW_METRICS
    
    results_dict = {
        "workflow_metrics": [asdict(metric) for metric in WORKFLOW_METRICS],
        "summary": {
            "total_workflows": len(WORKFLOW_METRICS),
            "successful_workflows": sum(1 for m in WORKFLOW_METRICS if m.success),
            "success_rate": sum(1 for m in WORKFLOW_METRICS if m.success) / len(WORKFLOW_METRICS) if WORKFLOW_METRICS else 0,
            "avg_total_latency_ms": np.mean([m.total_latency for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_planner_latency_ms": np.mean([m.planner_latency for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_workers_latency_ms": np.mean([m.workers_latency for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_evaluators_latency_ms": np.mean([m.evaluators_latency for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_verifier_latency_ms": np.mean([m.verifier_latency for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_subtasks_per_workflow": np.mean([m.num_subtasks for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_iterations": np.mean([m.num_iterations for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_revisions": np.mean([m.num_revisions for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
            "avg_quality_score": np.mean([m.final_quality_score for m in WORKFLOW_METRICS]) if WORKFLOW_METRICS else 0,
        }
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_dict, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 结果已保存到: {results_file}")


def print_statistics():
    """打印统计信息"""
    global WORKFLOW_METRICS
    
    if not WORKFLOW_METRICS:
        print("⚠️  没有收集到任何指标数据")
        return
    
    print("\n" + "=" * 70)
    print("📈 改进版 Coder Agent 基准测试结果")
    print("=" * 70)
    
    # 成功率统计
    successful = sum(1 for m in WORKFLOW_METRICS if m.success)
    success_rate = successful / len(WORKFLOW_METRICS)
    
    print(f"\n✅ 成功率: {success_rate:.2%} ({successful}/{len(WORKFLOW_METRICS)})")
    
    # 质量分数统计
    quality_scores = [m.final_quality_score for m in WORKFLOW_METRICS]
    print(f"\n🎯 质量分数统计:")
    print(f"  平均: {np.mean(quality_scores):.3f}")
    print(f"  中位数: {np.median(quality_scores):.3f}")
    print(f"  最小值: {np.min(quality_scores):.3f}")
    print(f"  最大值: {np.max(quality_scores):.3f}")
    
    # 迭代和修复统计
    avg_iterations = np.mean([m.num_iterations for m in WORKFLOW_METRICS])
    avg_revisions = np.mean([m.num_revisions for m in WORKFLOW_METRICS])
    revision_workflows = sum(1 for m in WORKFLOW_METRICS if m.num_revisions > 0)
    
    print(f"\n🔄 迭代与修复统计:")
    print(f"  平均迭代次数: {avg_iterations:.2f}")
    print(f"  平均修复次数: {avg_revisions:.2f}")
    print(f"  触发修复的工作流: {revision_workflows}/{len(WORKFLOW_METRICS)} ({revision_workflows/len(WORKFLOW_METRICS):.2%})")
    
    # 延迟统计
    total_latencies = [m.total_latency for m in WORKFLOW_METRICS]
    planner_latencies = [m.planner_latency for m in WORKFLOW_METRICS]
    workers_latencies = [m.workers_latency for m in WORKFLOW_METRICS]
    evaluators_latencies = [m.evaluators_latency for m in WORKFLOW_METRICS]
    verifier_latencies = [m.verifier_latency for m in WORKFLOW_METRICS]
    
    print(f"\n📊 延迟统计 (毫秒):")
    print(f"  总延迟:")
    print(f"    平均: {np.mean(total_latencies):.2f}")
    print(f"    中位数: {np.median(total_latencies):.2f}")
    print(f"    P95: {np.percentile(total_latencies, 95):.2f}")
    print(f"    P99: {np.percentile(total_latencies, 99):.2f}")
    
    print(f"\n  各阶段平均延迟:")
    total_avg = np.mean(total_latencies)
    if total_avg > 0:
        print(f"    Planner:    {np.mean(planner_latencies):>10.2f} ms ({np.mean(planner_latencies)/total_avg*100:>5.1f}%)")
        print(f"    Workers:    {np.mean(workers_latencies):>10.2f} ms ({np.mean(workers_latencies)/total_avg*100:>5.1f}%)")
        print(f"    Evaluators: {np.mean(evaluators_latencies):>10.2f} ms ({np.mean(evaluators_latencies)/total_avg*100:>5.1f}%)")
        print(f"    Verifier:   {np.mean(verifier_latencies):>10.2f} ms ({np.mean(verifier_latencies)/total_avg*100:>5.1f}%)")
    else:
        print(f"    Planner:    {np.mean(planner_latencies):>10.2f} ms")
        print(f"    Workers:    {np.mean(workers_latencies):>10.2f} ms")
        print(f"    Evaluators: {np.mean(evaluators_latencies):>10.2f} ms")
        print(f"    Verifier:   {np.mean(verifier_latencies):>10.2f} ms")
    
    # 子任务统计
    avg_subtasks = np.mean([m.num_subtasks for m in WORKFLOW_METRICS])
    
    print(f"\n📋 子任务统计:")
    print(f"  平均子任务数: {avg_subtasks:.2f}")
    
    # 详细的迭代分布
    iteration_counts = {}
    for m in WORKFLOW_METRICS:
        iteration_counts[m.num_iterations] = iteration_counts.get(m.num_iterations, 0) + 1
    
    print(f"\n📊 迭代次数分布:")
    for iter_num in sorted(iteration_counts.keys()):
        count = iteration_counts[iter_num]
        percentage = count / len(WORKFLOW_METRICS) * 100
        print(f"  {iter_num} 次迭代: {count:>3} 个工作流 ({percentage:>5.1f}%)")


# ==================== 主函数 ====================

def main(args: argparse.Namespace):
    """主函数"""
    print("=" * 70)
    print("🤖 改进版 Coder Agent 基准测试")
    print("   工作流: Planner → Workers → Evaluators → Verifier")
    print("=" * 70)
    print(f"参数: {args}\n")
    
    # 设置随机种子
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    # 创建 Agent configs
    print("🔧 准备智能体配置...")
    planner_config = AgentConfig(
        name="Planner",
        llm_model_name=args.planner_model,
        temperature=0.1,
        max_tokens=args.max_tokens
    )
    
    worker_config = AgentConfig(
        name="Worker",
        llm_model_name=args.worker_model,
        temperature=0.3,
        max_tokens=args.max_tokens
    )
    
    evaluator_config = AgentConfig(
        name="Evaluator",
        llm_model_name=args.evaluator_model,
        temperature=0.0,
        max_tokens=args.max_tokens
    )
    
    verifier_config = AgentConfig(
        name="Verifier",
        llm_model_name=args.verifier_model,
        temperature=0.0,
        max_tokens=args.max_tokens 
    )
    
    # 创建 ImprovedCoderAgent
    print("🔧 创建改进版 Coder Agent...")
    agent = ImprovedCoderAgent(
        planner_config=planner_config,
        worker_config=worker_config,
        evaluator_config=evaluator_config,
        verifier_config=verifier_config,
        max_iterations=args.max_iterations
    )
    
    # 生成测试请求
    print(f"📊 生成 {args.num_apps} 个测试请求...")
    input_requests = sample_requests(args.num_apps, args.prompts_file)
    
    # 运行基准测试
    print(f"\n🚀 开始基准测试...")
    print(f"  工作流数量: {args.num_apps}")
    print(f"  请求速率: {args.request_rate} req/s")
    print(f"  最大迭代次数: {args.max_iterations}")
    print(f"  Planner模型: {args.planner_model}")
    print(f"  Worker模型: {args.worker_model}")
    print(f"  Evaluator模型: {args.evaluator_model}")
    print(f"  Verifier模型: {args.verifier_model}\n")
    
    benchmark_start_time = time.perf_counter_ns()
    
    asyncio.run(
        benchmark(
            input_requests=input_requests,
            request_rate=args.request_rate,
            agent=agent
        )
    )
    
    benchmark_end_time = time.perf_counter_ns()
    benchmark_time_ms = (benchmark_end_time - benchmark_start_time) / 1e6
    
    # 打印全局统计
    print("\n" + "=" * 70)
    print(f"⏱️  总时间: {benchmark_time_ms / 1000:.2f} s")
    print(f"🚀 吞吐量: {args.num_apps * 1000 / benchmark_time_ms:.2f} 工作流/秒")
    
    # 打印详细统计
    print_statistics()
    
    
    # 保存结果
    if args.output_file:
        save_results_to_file(args.output_file)
    
    print("\n" + "=" * 70)
    print("🎉 基准测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="改进版 Coder Agent 基准测试"
    )
    
    # 基准测试参数
    parser.add_argument(
        "--num-apps",
        type=int,
        default=10,
        help="要处理的工作流数量"
    )
    parser.add_argument(
        "--request-rate",
        type=float,
        default=float("inf"),
        help="请求速率 (请求/秒)，inf表示无限速率"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子"
    )
    
    # 模型参数
    parser.add_argument(
        "--planner-model",
        type=str,
        default="gpt-3.5-turbo",
        help="Planner模型名称"
    )
    parser.add_argument(
        "--worker-model",
        type=str,
        default="gpt-3.5-turbo",
        help="Worker模型名称"
    )
    parser.add_argument(
        "--evaluator-model",
        type=str,
        default="gpt-3.5-turbo",
        help="Evaluator模型名称"
    )
    parser.add_argument(
        "--verifier-model",
        type=str,
        default="gpt-3.5-turbo",
        help="Verifier模型名称"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=200,
        help="每个阶段的最大token数"
    )
    
    # 输入/输出参数
    parser.add_argument(
        "--prompts-file",
        type=str,
        default=None,
        help="包含用户提示的文件路径 (每行一个提示)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="improved_coder_benchmark_results.json",
        help="结果输出文件路径"
    )
    
    # 工作流参数
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=2,
        help="最大迭代次数（包括初始执行）"
    )
    
    args = parser.parse_args()
    main(args)