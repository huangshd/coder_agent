# improved_coder_agent.py - 改进版 Coder Agent
# 工作流: User → Planner → Workers → Evaluators → Verifier → Final Output
# 主要改进：
# 1. Planner 生成详细的 API 规范（系统 API + 新实现的 API）
# 2. 每个 Worker 有对应的 Evaluator 生成代码审查报告
# 3. Verifier 汇总报告、跨模块检查、决定是否需要迭代修复

import time
import random
import asyncio
import re
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field

# LangChain imports
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# 导入 base_agent
import sys
from pathlib import Path
base_agent_path = Path(__file__).parent
sys.path.insert(0, str(base_agent_path))

from base_agent import BaseAgent, AgentConfig, PerformanceMetrics

# ==================== 工具函数 ====================
def sanitize_short_text(s: str, max_chars: int = 200) -> str:
    """移除不可打印字符、折叠多空白，并截断为 max_chars 字符"""
    if not s:
        return ""
    # 移除不可打印字符
    s = ''.join(ch for ch in s if ch.isprintable())
    # 折叠多个空白
    s = re.sub(r'\s+', ' ', s).strip()
    # 截断
    if len(s) > max_chars:
        s = s[:max_chars].rstrip() + "..."
    # 避免太多重复单词：简单去重连续重复token（例如 "and and and"）
    s = re.sub(r'\b(\w+)(?: \1){3,}\b', r'\1...', s)
    return s


# ==================== 数据结构定义 ====================

@dataclass
class APISpecification:
    """API 规范"""
    name: str
    type: str  # "system" 或 "new"
    description: str
    signature: str  # 函数签名
    parameters: List[str] = field(default_factory=list)
    return_type: str = ""


@dataclass
class SubTaskWithAPI:
    """带 API 规范的子任务"""
    id: int
    description: str
    system_apis: List[APISpecification] = field(default_factory=list)  # 需要使用的系统 API
    new_apis: List[APISpecification] = field(default_factory=list)     # 需要实现的新 API
    difficulty: str = "medium"
    assigned_worker: Optional[int] = None
    code_result: Optional[str] = None  # Worker 生成的代码
    api_implementations: Dict[str, str] = field(default_factory=dict)  # API 名称 -> 实现代码
    status: str = "pending"  # pending, completed, failed, needs_revision


@dataclass
class EvaluationReport:
    """Evaluator 生成的代码审查报告"""
    worker_id: int
    task_id: int
    api_compliance_score: float = 0.0  # API 是否按要求实现
    code_quality_score: float = 0.0    # 代码质量
    logic_correctness_score: float = 0.0  # 逻辑正确性
    overall_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    needs_revision: bool = False
    report_text: str = ""


@dataclass
class VerificationResult:
    """Verifier 的最终决策"""
    overall_pass: bool = False
    cross_module_issues: List[str] = field(default_factory=list)
    modules_need_revision: List[int] = field(default_factory=list)  # 需要重做的任务 ID
    
    # 🔥 新增：每个任务的详细修订建议
    task_revision_instructions: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    # 格式: {
    #   task_id: {
    #     "scores": {"api": 0.8, "quality": 0.7, "logic": 0.8},
    #     "recommendations": ["建议1", "建议2"]
    #   }
    # }
    
    final_code: str = ""
    integrated_report: str = ""
    quality_score: float = 0.0


@dataclass
class ImprovedCoderMetrics:
    """改进版 Coder 工作流性能指标"""
    workflow_id: int
    planner_latency: float = 0.0
    workers_latency: float = 0.0
    evaluators_latency: float = 0.0
    verifier_latency: float = 0.0
    total_latency: float = 0.0
    num_subtasks: int = 0
    num_iterations: int = 1
    num_revisions: int = 0  # 修复迭代次数
    success: bool = False
    final_quality_score: float = 0.0


# ==================== Prompt 模板准备 ====================

def prepare_improved_chains(
    planner_model: str = "gpt-3.5-turbo",
    worker_model: str = "gpt-3.5-turbo",
    evaluator_model: str = "gpt-3.5-turbo",
    verifier_model: str = "gpt-3.5-turbo",
    temperature: float = 0.1,
    max_tokens: int = 300
):
    """准备改进版工作流的所有 Chains"""

    # ========== 1. Enhanced Planner (with API Planning) ==========
    planner_template = """You are a senior software architect and API design expert.
Analyze the programming task and produce a detailed implementation plan, including API specifications.

User requirement:
{user_prompt}

Step 1: Analyze task complexity

Classification criteria:
- **Simple task** (<100 lines of code): single algorithm or utility function → 1 subtask
- **Medium task** (100–300 lines): small application or multi-module tool → 2–3 subtasks
- **Complex task** (>300 lines): full system, multiple services, or database → 3–5 subtasks

Step 2: Plan APIs for each subtask

CRITICAL: Strictly limit the number of subtasks based on complexity:
- Simple task → Output EXACTLY 1 subtask (Task 1 only)
- Medium task → Output 2-3 subtasks (Task 1, Task 2, optionally Task 3)
- Complex task → Output 3-5 subtasks (Task 1 through Task 5 maximum)

DO NOT output more subtasks than the complexity level allows.

Strictly follow the output format below:

Task complexity: [Simple / Medium / Complex]

Overall architecture: [one-sentence description of the system architecture, within 20 words]

Subtask list:

Task 1: [concise description, within 15 words]
System APIs: [system libraries / third-party APIs to use, e.g., os.path.exists, requests.get]
New APIs: [new functions or classes to implement, format: function_name(parameters) -> return_type]
Implementation notes: [key logic, within 15 words]

Task 2: ...
[ONLY include Task 2 and beyond if complexity is Medium or Complex]

Key principles:
1. Each subtask must clearly list:
   - which system APIs to call
   - which new APIs to implement
2. API names must be clear and follow Python naming conventions
3. All new APIs must specify parameters and return types
4. MOST IMPORTANT: Respect the subtask count limits for each complexity level

Now start the analysis:
"""
    
    planner_prompt = PromptTemplate(
        input_variables=["user_prompt"],
        template=planner_template
    )
    planner_llm = ChatOpenAI(model_name=planner_model, temperature=temperature, max_tokens=max_tokens)
    planner_chain = LLMChain(llm=planner_llm, prompt=planner_prompt)
    
    # ========== 2. Worker (API-aware) ==========
    worker_template = """You are Software Developer Worker #{worker_id}.
Implement the coding task strictly according to the Planner's API specifications.

Project context:
{project_context}

Your task:
{task_description}

API specifications:

System APIs (must be used):
{system_apis}

New APIs (must be implemented):
{new_apis}

Requirements:
1. **Strictly follow the API specifications**. Function signatures must match exactly.
2. Use the specified system APIs; do not reimplement them.
3. The code must be complete, runnable, and include all necessary imports.
4. Add appropriate comments to explain key logic.
5. Output code only. Do not include any additional explanation.

Your implementation:
"""
    
    worker_prompt = PromptTemplate(
        input_variables=["worker_id", "project_context", "task_description", "system_apis", "new_apis"],
        template=worker_template
    )
    worker_llm = ChatOpenAI(model_name=worker_model, temperature=0.3, max_tokens=max_tokens)
    worker_chain = LLMChain(llm=worker_llm, prompt=worker_prompt)
    
    # ========== 3. Evaluator (Code Reviewer) - 简化版 ==========
    evaluator_template = """You are a code review expert.
Briefly review the following code.

Task:
{task_description}

Required APIs:
System APIs [{required_system_apis}]
New APIs [{required_new_apis}]

Code:
{worker_code}

Output strictly in the following format (1–2 sentences per item):

API compliance (0–10): X/10
[Whether the required APIs are correctly implemented]

Code quality (0–10): X/10
[Structure, naming, comments]

Logical correctness (0–10): X/10
[Algorithms, edge cases]

Revision suggestions:
[If revision is required, list 1–2 suggestions; otherwise write "None"]

Important:
- Output only the specified format. No extra explanations.
- Limit each evaluation item to within 30 words.
- Do not output duplicate content or garbled text.

Start:
"""
    
    evaluator_prompt = PromptTemplate(
        input_variables=[
            "task_description",
            "required_system_apis", "required_new_apis", "worker_code"
        ],
        template=evaluator_template
    )
    evaluator_llm = ChatOpenAI(model_name=evaluator_model, temperature=0.0, max_tokens=200)  # 🔥 减少 max_tokens
    evaluator_chain = LLMChain(llm=evaluator_llm, prompt=evaluator_prompt)
    
    # ========== 4. Verifier (Integration & Final Decision) ==========
    verifier_template = """You are a system integration expert and code review analyst.
Provide a descriptive summary and cross-module analysis based on the Evaluator reports.

Note: You will NOT make the final Pass/Fail decision. Your role is to:
1. Summarize the quality and concerns from all reports
2. Identify potential cross-module issues

Original requirement:
{original_prompt}

Overall architecture:
{project_context}

All Evaluator reports:
{all_evaluation_reports}

Strictly follow the format below:

I. Report summary
[Provide a DESCRIPTIVE summary of the Evaluator reports in 3-5 sentences.
Describe overall quality, main strengths, and any concerns.
DO NOT list numerical scores here.
Example: "All modules demonstrate solid implementation. The API compliance is excellent. 
However, some modules show room for improvement in code documentation and error handling."]

II. Cross-module consistency analysis
[Analyze potential issues between modules based on the reports]

Potential issues:
[List cross-module concerns such as:
- API interface mismatches between modules
- Inconsistent data formats or naming conventions
- Missing integration points
If no issues detected, write "No obvious cross-module issues"]

IMPORTANT:
- Focus on qualitative analysis, not scores
- Be specific about cross-module concerns if any exist
- Keep the summary concise and actionable

Start analysis:
"""
    
    verifier_prompt = PromptTemplate(
        input_variables=[
            "original_prompt", "project_context",
            "all_evaluation_reports"
        ],
        template=verifier_template
    )
    verifier_llm = ChatOpenAI(model_name=verifier_model, temperature=0.0, max_tokens=max_tokens)
    verifier_chain = LLMChain(llm=verifier_llm, prompt=verifier_prompt)
    
    return planner_chain, worker_chain, evaluator_chain, verifier_chain


# ==================== 解析函数 ====================

def parse_enhanced_planner_output(
    planner_text: str
) -> Tuple[str, List[SubTaskWithAPI], str]:
    """
    Parse English planner output with explicit API specifications
    """
    import re

    print("\n" + "="*70)
    print("🔍 [DEBUG] 开始解析 Planner 输出")
    print("="*70)

    architecture = ""
    complexity = "medium"
    tasks: List[SubTaskWithAPI] = []

    lines = [l.strip() for l in planner_text.splitlines() if l.strip()]

    current_task = None
    in_subtasks = False

    for line in lines:
        print(f"[DEBUG] LINE: {line}")
        # ---- Task complexity ----
        if line.lower().startswith("task complexity"):
            if "simple" in line.lower():
                complexity = "low"
            elif "medium" in line.lower():
                complexity = "medium"
            else:
                complexity = "high"
            print(f"✅ 识别到复杂度: {complexity}")  # 添加这行
            continue

        # ---- Architecture ----
        if line.lower().startswith("overall architecture"):
            architecture = line.split(":", 1)[1].strip()
            continue

        # ---- Subtask section ----
        if re.match(r'subtask', line, re.IGNORECASE):
            in_subtasks = True
            print("🧩 进入 Subtask 区块")
            continue

        if not in_subtasks:
            continue

        # ---- New task ----
        task_match = re.match(r'task\s*(\d+)\s*:\s*(.+)', line, re.IGNORECASE)
        if task_match:
            task_id = int(task_match.group(1))
            desc = task_match.group(2).strip()

            print(f"📋 发现 Task {task_id}: {desc[:50]}...")  # 添加这行
            
            # 🔥 跳过标记为 Optional 的任务
            if re.search(r'\(optional\)', desc, re.IGNORECASE):
                print(f"⏭️  跳过 Task {task_id} (标记为 Optional)")  # 添加这行
                continue
            
            if current_task:
                tasks.append(current_task)
                print(f"✅ Task {current_task.id} 已添加到任务列表")  # 添加这行

            current_task = SubTaskWithAPI(
                id=task_id,
                description=desc
            )
            continue

        if not current_task:
            continue

        # ---- System APIs ----
        if line.lower().startswith("system api"):
            api_text = line.split(":", 1)[1].strip()
            if api_text.lower() not in ("none", "[]"):
                for api in api_text.split(","):
                    api = api.strip()
                    if api:
                        current_task.system_apis.append(
                            APISpecification(
                                name=api,
                                type="system",
                                signature=api,
                                description=""
                            )
                        )
            continue

        # ---- New APIs ----
        if line.lower().startswith("new api"):
            api_text = line.split(":", 1)[1].strip()
            if api_text.lower() not in ("none", "[]"):
                api_defs = re.findall(
                    r'(\w+)\((.*?)\)\s*->\s*([\w\[\], ]+)',
                    api_text
                )
                for name, params, ret in api_defs:
                    current_task.new_apis.append(
                        APISpecification(
                            name=name,
                            type="new",
                            signature=f"{name}({params})",
                            parameters=[p.strip() for p in params.split(",") if p.strip()],
                            return_type=ret.strip(),
                            description=""
                        )
                    )

    if current_task:
        tasks.append(current_task)
        print(f"✅ Task {current_task.id} 已添加到任务列表")

    if not architecture:
        architecture = "Complete solution implementing the user requirements"

    if not tasks:
        tasks = [SubTaskWithAPI(id=1, description="Implement core functionality")]
    
    print(f"\n📊 解析结果汇总:")
    print(f"  - 复杂度: {complexity}")
    print(f"  - 架构: {architecture[:60]}...")
    print(f"  - 子任务数量: {len(tasks)}")
    for t in tasks:
        print(f"    • Task {t.id}: {t.description[:50]}...")
    print("="*70 + "\n")

    return architecture, tasks, complexity



def parse_evaluation_report(
    report_text: str,
    worker_id: int,
    task_id: int
) -> EvaluationReport:
    import re

    print("\n" + "="*70)
    print(f"🔍 [DEBUG] 开始解析 Evaluator 报告 (Worker {worker_id}, Task {task_id})")
    print("="*70)
    print(f"📄 原始报告长度: {len(report_text)} 字符")

    report = EvaluationReport(
        worker_id=worker_id,
        task_id=task_id,
        report_text=report_text
    )

    # ==========================================================
    # 1. 垃圾 / 重复输出检测
    # ==========================================================
    if re.search(r'(.)\1{12,}', report_text):
        print("⚠️  检测到重复字符，标记为异常输出")
        report.needs_revision = True
        report.overall_score = 0.0
        report.issues.append("Malformed or repetitive output")
        return report

    # ==========================================================
    # 2. 通用分数提取器（支持 x/10, x/30, 浮点）
    # ==========================================================
    def extract_fraction_score(pattern: str, scale: float, label: str):
        m = re.search(pattern, report_text, re.IGNORECASE)
        if not m:
            print(f"❌ {label}: 未找到")
            return None
        value = float(m.group(1))
        normalized = value / scale
        print(f"✅ {label}: {value}/{scale} = {normalized:.2f}")
        return normalized

    # ==========================================================
    # 3. 解析各项评分（字段名对齐 evaluator）
    # ==========================================================
    print("\n📊 解析评分项:")
    report.api_compliance_score = extract_fraction_score(
        r'API compliance\s*[(:]\s*([\d.]+)\s*/\s*10', 10, "API合规"
    )

    report.code_quality_score = extract_fraction_score(
        r'Code quality\s*[(:]\s*([\d.]+)\s*/\s*10', 10, "代码质量"
    )

    report.logic_correctness_score = extract_fraction_score(
        r'Logical correctness\s*[(:]\s*([\d.]+)\s*/\s*10', 10, "逻辑正确"
    )

    # ==========================================================
    # 4. Fallback：用子项平均
    # ==========================================================
    scores = [
        s for s in [
            report.api_compliance_score,
            report.code_quality_score,
            report.logic_correctness_score
        ] if s is not None
    ]
    if scores:
        report.overall_score = sum(scores) / len(scores)
        print(f"⚙️  综合评分使用子项平均值: {report.overall_score:.2f}")
    else:
        report.overall_score = 0.0
        print(f"⚠️  所有评分项均未找到，默认为 0.0")

    # ==========================================================
    # 5. 是否需要修订
    # ==========================================================
    # 🔥 优先基于分数判断，不信任 LLM 的 "Revision required" 输出
    needs_revision = False
    revision_reasons = []

    # 检查单项分数（任何一项 < 0.8 都需要修订）
    if report.api_compliance_score is not None and report.api_compliance_score < 0.8:
        needs_revision = True
        revision_reasons.append(f"API合规分数 {report.api_compliance_score:.2f} < 0.8")

    if report.code_quality_score is not None and report.code_quality_score < 0.8:
        needs_revision = True
        revision_reasons.append(f"代码质量分数 {report.code_quality_score:.2f} < 0.8")

    if report.logic_correctness_score is not None and report.logic_correctness_score < 0.8:
        needs_revision = True
        revision_reasons.append(f"逻辑正确分数 {report.logic_correctness_score:.2f} < 0.8")

    # 检查综合平均分
    if report.overall_score < 0.8:
        needs_revision = True
        revision_reasons.append(f"综合评分 {report.overall_score:.2f} < 0.8")

    report.needs_revision = needs_revision

    # 输出判断结果
    if needs_revision:
        print(f"⚠️  需要修订 (基于分数阈值 0.8):")
        for reason in revision_reasons:
            print(f"     - {reason}")
    else:
        print(f"✅ 无需修订 (所有分数均 >= 0.8)")

    # ==========================================================
    # 6. 解析 Revision suggestions
    # ==========================================================
    print("\n💡 解析修订建议:")
    
    # 查找 "Revision suggestions:" 后的内容
    suggestions_match = re.search(
        r'Revision suggestions?\s*:?\s*(.*?)(?:\n\n|$)',
        report_text,
        re.DOTALL | re.IGNORECASE
    )
    
    if suggestions_match:
        suggestions_text = suggestions_match.group(1).strip()
        
        # 检查是否是 "None" 或空
        if re.search(r'^(None|N/A|No suggestions?)\.?$', suggestions_text, re.IGNORECASE):
            print(f"   ℹ️  无修订建议")
        else:
            # 提取所有以 * 开头的建议项
            suggestions = re.findall(
                r'^\s*\*\s*(.+?)$',
                suggestions_text,
                re.MULTILINE
            )
            
            if suggestions:
                report.recommendations = [s.strip() for s in suggestions]
                print(f"   ✅ 找到 {len(report.recommendations)} 条建议:")
                for idx, rec in enumerate(report.recommendations, 1):
                    print(f"      {idx}. {rec[:80]}{'...' if len(rec) > 80 else ''}")
            else:
                # 如果没有 * 格式，尝试提取整段文本
                clean_text = suggestions_text.strip()
                if clean_text and clean_text.lower() not in ('none', 'n/a', 'no suggestions'):
                    report.recommendations = [clean_text]
                    print(f"   ✅ 找到 1 条建议: {clean_text[:80]}{'...' if len(clean_text) > 80 else ''}")
                else:
                    print(f"   ℹ️  无有效修订建议")
    else:
        print(f"   ❌ 未找到 'Revision suggestions' 区块")

    print(f"\n📋 解析结果:")
    print(f"  - 综合评分: {report.overall_score:.2f}")
    print(f"  - 需要修订: {report.needs_revision}")
    print(f"  - 修订建议数: {len(report.recommendations)}")
    print("="*70 + "\n")

    return report




def parse_verification_result(verifier_text: str) -> VerificationResult:
    import re

    print("\n" + "="*70)
    print("🔍 [DEBUG] 开始解析 Verifier 输出")
    print("="*70)
    print(f"📄 原始报告长度: {len(verifier_text)} 字符")

    result = VerificationResult()

    # ---- Overall quality ----
    print("\n📊 解析质量分数:")
    m = re.search(
        r'Overall quality score\s*:\s*(\d+)\s*/\s*100',
        verifier_text,
        re.IGNORECASE
    )
    if m:
        result.quality_score = float(m.group(1)) / 100.0
        print(f"✅ 找到质量分数: {m.group(1)}/100 = {result.quality_score:.2f}")
    else:
        print(f"❌ 未找到质量分数，默认为 0.0")

    # ---- Pass / Fail ----
    print("\n🎯 解析通过/失败状态:")
    # 先尝试匹配 "Pass / Fail: Pass" 或 "Pass or fail: Pass" 格式
    if re.search(r'Pass\s*[/or]+\s*[Ff]ail\s*:\s*Pass', verifier_text, re.IGNORECASE):
        result.overall_pass = True
        print(f"✅ 状态: Pass (通过) - 格式1")
    elif re.search(r'Pass\s*[/or]+\s*[Ff]ail\s*:\s*Fail', verifier_text, re.IGNORECASE):
        result.overall_pass = False
        print(f"❌ 状态: Fail (失败) - 格式1")
    # 尝试匹配独立的 "* Pass" 或 "Pass" (在 III. Final decision 区块内)
    elif re.search(r'III\..*?^\s*\*?\s*Pass\s*$', verifier_text, re.MULTILINE | re.DOTALL | re.IGNORECASE):
        result.overall_pass = True
        print(f"✅ 状态: Pass (通过) - 格式2")
    elif re.search(r'III\..*?^\s*\*?\s*Fail\s*$', verifier_text, re.MULTILINE | re.DOTALL | re.IGNORECASE):
        result.overall_pass = False
        print(f"❌ 状态: Fail (失败) - 格式2")
    else:
        print(f"⚠️  未找到 Pass/Fail 标记，默认为 False")

    # ---- Modules requiring revision ----
    print("\n🔧 解析需要修订的模块:")
    m = re.search(
        r'Modules requiring revision\s*:(.*?)(?:\n\n|IV\.|$)',
        verifier_text,
        re.DOTALL | re.IGNORECASE
    )
    if m:
        text = m.group(1)
        print(f"📝 找到修订模块区块: {text[:100].strip()}...")
        if re.search(r'none', text, re.IGNORECASE):
            result.modules_need_revision = []
            print(f"✅ 无需修订的模块")
        else:
            result.modules_need_revision = [
                int(x) for x in re.findall(r'Task\s*(\d+)', text)
            ]
            if result.modules_need_revision:
                print(f"⚠️  需要修订的模块: {result.modules_need_revision}")
            else:
                print(f"⚠️  未找到具体任务编号")
    else:
        print(f"❌ 未找到 'Modules requiring revision' 区块")

    # ---- Cross-module issues ----
    print("\n🔗 解析跨模块问题:")
    m = re.search(
        r'Cross-module consistency analysis(.*?)(?:III\.|$)',
        verifier_text,
        re.DOTALL | re.IGNORECASE
    )
    if m:
        issues = [
            l.strip()
            for l in m.group(1).splitlines()
            if l.strip() and not l.lower().startswith("none") and not l.lower().startswith("potential issues")
        ]
        result.cross_module_issues = issues
        if issues:
            print(f"⚠️  发现 {len(issues)} 个跨模块问题:")
            for idx, issue in enumerate(issues[:3], 1):
                print(f"   {idx}. {issue[:80]}...")
        else:
            print(f"✅ 无跨模块问题")
    else:
        print(f"❌ 未找到 'Cross-module consistency analysis' 区块")

    # ---- Integrated summary ----
    print("\n📋 解析综合摘要:")
    m = re.search(
        r'I\.\s*(Report summary|Summary)(.*?)(?:II\.|$)',
        verifier_text,
        re.DOTALL | re.IGNORECASE
    )
    if m:
        result.integrated_report = m.group(2).strip()
        print(f"✅ 找到综合摘要 ({len(result.integrated_report)} 字符)")
        print(f"   {result.integrated_report[:100]}...")
    else:
        print(f"❌ 未找到综合摘要区块")

    print(f"\n📋 解析结果汇总:")
    print(f"  - 质量分数: {result.quality_score:.2f}")
    print(f"  - 通过状态: {'Pass' if result.overall_pass else 'Fail'}")
    print(f"  - 需要修订的模块: {result.modules_need_revision if result.modules_need_revision else '无'}")
    print(f"  - 跨模块问题数: {len(result.cross_module_issues)}")
    print(f"  - 综合摘要长度: {len(result.integrated_report)} 字符")
    print("="*70 + "\n")

    return result



# ==================== ImprovedCoderAgent 类实现 ====================

class ImprovedCoderAgent(BaseAgent):
    """
    改进版 Coder Agent
    工作流: User → Planner → Workers → Evaluators → Verifier → Final Output
    """
    
    def __init__(
        self,
        planner_config: AgentConfig,
        worker_config: AgentConfig,
        evaluator_config: AgentConfig,
        verifier_config: AgentConfig,
        max_iterations: int = 3
    ):
        super().__init__(planner_config)
        
        self.planner_config = planner_config
        self.worker_config = worker_config
        self.evaluator_config = evaluator_config
        self.verifier_config = verifier_config
        self.max_iterations = max_iterations
        
        self._current_metrics = None
        
        # 准备所有 chains
        (self.planner_chain, self.worker_chain, 
         self.evaluator_chain, self.verifier_chain) = prepare_improved_chains(
            planner_model=planner_config.llm_model_name,
            worker_model=worker_config.llm_model_name,
            evaluator_model=evaluator_config.llm_model_name,
            verifier_model=verifier_config.llm_model_name,
            temperature=0.1,
            max_tokens=300
        )
    
    def get_workflow_nodes(self) -> List[str]:
        return ["Planner", "Workers", "Evaluators", "Verifier"]
    
    def get_workflow_edges(self) -> List[Tuple[str, str]]:
        return [
            ("Planner", "Workers"),
            ("Workers", "Evaluators"),
            ("Evaluators", "Verifier"),
            ("Verifier", "Planner")  # 反馈循环
        ]
    
    def get_llm_call_count(self) -> int:
        return 4  # Planner + Workers + Evaluators + Verifier
    
    def get_workflow_description(self) -> str:
        return ("改进版 Coder Agent: Planner(API规划) → Workers(实现) → "
                "Evaluators(代码审查) → Verifier(整合&决策)")
    
    async def _execute_workflow(
        self,
        input_data: Dict[str, Any],
        metrics: PerformanceMetrics
    ) -> str:
        """执行改进版工作流"""
        user_prompt = input_data.get("user_prompt", "")
        workflow_id = input_data.get("workflow_id", 0)
        
        coder_metrics = ImprovedCoderMetrics(workflow_id=workflow_id)
        self._current_metrics = coder_metrics
        
        workflow_start = time.perf_counter_ns()
        
        iteration = 1
        architecture = ""
        tasks: List[SubTaskWithAPI] = []
        verification_result = None
        
        print(f"\n{'#'*70}")
        print(f"🚀 [改进版工作流 {workflow_id}] 开始执行")
        print(f"📝 用户需求: {user_prompt[:100]}...")
        print(f"{'#'*70}\n")
        
        while iteration <= self.max_iterations:
            print(f"\n{'='*70}")
            print(f"🔄 第 {iteration} 次迭代")
            print(f"{'='*70}\n")
            
            # ========== Step 1: Planner (with API Planning) ==========
            planner_start = time.perf_counter_ns()
            
            if iteration == 1:
                architecture, tasks, complexity = await self._execute_planner(user_prompt, workflow_id)
                print(f"📊 任务复杂度: {complexity.upper()}")
            else:
                # 基于 Verifier 反馈重新规划
                architecture, tasks = await self._execute_planner_with_feedback(
                    user_prompt, verification_result, architecture, iteration, workflow_id
                )
            
            planner_latency = (time.perf_counter_ns() - planner_start) / 1e6
            coder_metrics.planner_latency += planner_latency
            
            if iteration == 1:
                coder_metrics.num_subtasks = len(tasks)
            
            print(f"  ✅ 工作流{workflow_id}的Planner 完成: {len(tasks)} 个子任务, {planner_latency:.2f}ms\n")
            
            # ========== Step 2: Workers (parallel execution) ==========
            workers_start = time.perf_counter_ns()

            # 🔥 在迭代时，只重做需要修订的任务
            if iteration == 1:
                await self._execute_workers(tasks, architecture, workflow_id)
                print(f"  📝 首次执行所有 {len(tasks)} 个任务")
            else:
                # 只重做需要修订的任务
                tasks_to_redo = verification_result.modules_need_revision if verification_result else []
                if tasks_to_redo:
                    print(f"  🔄 重做任务: {tasks_to_redo}")
                    await self._execute_workers(tasks, architecture, workflow_id, tasks_to_execute=tasks_to_redo)
                else:
                    print(f"  ⚠️  无需重做任何任务（异常情况）")
            
            workers_latency = (time.perf_counter_ns() - workers_start) / 1e6
            coder_metrics.workers_latency += workers_latency
            
            completed = sum(1 for t in tasks if t.status == "completed")
            print(f"  ✅ 工作流{workflow_id}的Workers 完成: {completed}/{len(tasks)} 个任务, {workers_latency:.2f}ms\n")
            
            # ========== Step 3: Evaluators (per-worker review) ==========
            evaluators_start = time.perf_counter_ns()
            
            evaluation_reports = await self._execute_evaluators(tasks, workflow_id)

            evaluators_latency = (time.perf_counter_ns() - evaluators_start) / 1e6
            coder_metrics.evaluators_latency += evaluators_latency
            
            print(f"  ✅ 工作流{workflow_id}的Evaluators 完成: {len(evaluation_reports)} 份报告, {evaluators_latency:.2f}ms\n")
            


            # ========== Step 4: Verifier (integration & decision) ==========
            verifier_start = time.perf_counter_ns()
            
            verification_result = await self._execute_verifier(
                user_prompt, architecture, tasks, evaluation_reports, workflow_id
            )
            
            verifier_latency = (time.perf_counter_ns() - verifier_start) / 1e6
            coder_metrics.verifier_latency += verifier_latency

            # 放在 verifier_latency 累计之后、Decision 判断之前
            print(f"[DEBUG_DECISION] iteration={iteration}, max_iterations={self.max_iterations}")
            print(f"[DEBUG_DECISION] verification_result.quality_score (raw) = {verification_result.quality_score!r}")
            print(f"[DEBUG_DECISION] verification_result.modules_need_revision = {verification_result.modules_need_revision!r}")
            print(f"[DEBUG_DECISION] verification_result.overall_pass = {verification_result.overall_pass!r}")


            print(f"  ✅ 工作流{workflow_id}的Verifier 完成: 质量分数 {verification_result.quality_score:.2f}, "
                  f"通过: {verification_result.overall_pass}, {verifier_latency:.2f}ms\n")
            

            # ========== Decision: Continue or Finish? ==========
            print(f"\n{'='*70}")
            print(f"🎯 [工作流 {workflow_id}] 决策判断")
            print(f"{'='*70}")

            print(f"📊 当前状态:")
            print(f"   - 迭代次数: {iteration}/{self.max_iterations}")
            print(f"   - 需要修订的模块: {verification_result.modules_need_revision if verification_result.modules_need_revision else '无'}")
            print(f"   - 整体通过: {verification_result.overall_pass}")

            # 🔥 仅基于模块级别判断（移除综合分数）
            should_pass = (
                not verification_result.modules_need_revision and
                verification_result.overall_pass
            )

            if should_pass:
                print(f"\n✅ 决策: 通过")
                print(f"   理由: 所有模块均达标，无需修订")
                coder_metrics.success = True
                print(f"{'='*70}\n")
                break

            elif iteration < self.max_iterations:
                print(f"\n⚠️  决策: 继续迭代 (第 {iteration + 1} 次)")
                
                # 详细列出失败原因
                reasons = []
                if verification_result.modules_need_revision:
                    reasons.append(f"存在需要修订的模块: {verification_result.modules_need_revision}")
                if not verification_result.overall_pass:
                    reasons.append("模块级验证未通过")
                
                print(f"   失败原因:")
                for reason in reasons:
                    print(f"     - {reason}")
                
                if verification_result.integrated_report:
                    print(f"\n   📝 修订指令预览:")
                    lines = verification_result.integrated_report.split('\n')[:5]
                    for line in lines:
                        print(f"     {line}")
                    if len(verification_result.integrated_report.split('\n')) > 5:
                        print(f"     ... (更多)")
                
                coder_metrics.num_revisions += 1
                print(f"{'='*70}\n")
                iteration += 1
                continue

            else:
                print(f"\n⛔ 决策: 停止迭代")
                print(f"   理由: 已达到最大迭代次数 ({self.max_iterations})")
                print(f"   最终质量分数: {verification_result.quality_score:.2f}")
                print(f"{'='*70}\n")
                break
        
        coder_metrics.num_iterations = iteration
        coder_metrics.final_quality_score = verification_result.quality_score if verification_result else 0.0
        coder_metrics.total_latency = (time.perf_counter_ns() - workflow_start) / 1e6
        
        self._current_metrics = coder_metrics
        metrics.total_latency_ms = coder_metrics.total_latency
        
        print(f"{'#'*70}")
        print(f"🎉 [改进版工作流 {workflow_id}] 完成!")
        print(f"  迭代次数: {iteration}")
        print(f"  修复次数: {coder_metrics.num_revisions}")
        print(f"  成功: {coder_metrics.success}")
        print(f"  最终质量分数: {coder_metrics.final_quality_score:.2f}")
        print(f"  总延迟: {coder_metrics.total_latency:.2f}ms")
        print(f"  - Planner: {coder_metrics.planner_latency:.2f}ms")
        print(f"  - Workers: {coder_metrics.workers_latency:.2f}ms")
        print(f"  - Evaluators: {coder_metrics.evaluators_latency:.2f}ms")
        print(f"  - Verifier: {coder_metrics.verifier_latency:.2f}ms")
        print(f"{'#'*70}\n")
        
        return verification_result.final_code if verification_result else ""
    
    async def _execute_planner(self, user_prompt: str, workflow_id: int) -> Tuple[str, List[SubTaskWithAPI], str]:
        """执行 Planner（生成 API 规范）"""
        planner_output = await self.planner_chain.arun(user_prompt=user_prompt)
        print(f"📋 工作流{workflow_id}的PLANNER 输出:\n{planner_output}...\n")
        
        architecture, tasks, complexity = parse_enhanced_planner_output(planner_output)

        return architecture, tasks, complexity
    
    async def _execute_planner_with_feedback(
        self,
        user_prompt: str,
        verification_result: VerificationResult,
        previous_architecture: str,
        iteration: int,
        workflow_id: int
    ) -> Tuple[str, List[SubTaskWithAPI]]:
        """基于 Verifier 反馈重新规划"""
        
        # 🔥 构造详细的任务级反馈
        task_feedback_lines = []
        for task_id in verification_result.modules_need_revision:
            if task_id in verification_result.task_revision_instructions:
                instr = verification_result.task_revision_instructions[task_id]
                scores = instr["scores"]
                recs = instr["recommendations"]
                
                feedback = f"""
    Task {task_id} ({instr.get('task_description', 'Unknown')}):
    - Current scores: API={scores['api']:.2f}, Quality={scores['quality']:.2f}, Logic={scores['logic']:.2f}
    - Issues: Need to improve areas with scores < 0.8
    - Specific recommendations:
    """
                for idx, rec in enumerate(recs, 1):
                    feedback += f"\n  {idx}. {rec}"
                
                task_feedback_lines.append(feedback)
        
        task_feedback_text = "\n".join(task_feedback_lines)
        
        feedback_prompt = f"""Original requirement:
    {user_prompt}

    Previous architecture:
    {previous_architecture}

    Modules requiring revision: {verification_result.modules_need_revision}

    Detailed feedback for each problematic module:
    {task_feedback_text}

    Cross-module issues:
    {'; '.join(verification_result.cross_module_issues) if verification_result.cross_module_issues else 'None'}

    CRITICAL INSTRUCTION:
    You must ONLY replan the tasks that require revision: {verification_result.modules_need_revision}
    For other tasks, keep them unchanged from the previous iteration.
    Focus on addressing the specific issues mentioned in the feedback above.
    Ensure the new API design resolves all identified problems.
    """
        
        planner_output = await self.planner_chain.arun(user_prompt=feedback_prompt)
        print(f"📋 工作流{workflow_id}的PLANNER 输出 (迭代 {iteration}, 基于详细反馈):\n{planner_output}...\n")
        
        architecture, tasks, _ = parse_enhanced_planner_output(planner_output)
        return architecture, tasks
    
    async def _execute_workers(
        self,
        tasks: List[SubTaskWithAPI],
        architecture: str,
        workflow_id: int,
        tasks_to_execute: Optional[List[int]] = None  # 🔥 新增参数
    ) -> None:
        """并行执行所有 Workers"""
        worker_coros = []
        
        for task in tasks:

            # 🔥 如果指定了需要执行的任务，则只执行这些任务
            if tasks_to_execute is not None and task.id not in tasks_to_execute:
                print(f"  ⏭️  跳过 Task {task.id} (无需重做)")
                continue
            task.assigned_worker = task.id
            
            # 格式化 API 规范
            system_apis_text = "\n".join([f"  - {api.signature}" for api in task.system_apis]) or "  无"
            new_apis_text = "\n".join([
                f"  - {api.signature} -> {api.return_type}" for api in task.new_apis
            ]) or "  无"
            
            coro = self._execute_single_worker(
                task.id, architecture, task.description,
                system_apis_text, new_apis_text, workflow_id
            )
            worker_coros.append((task, coro))
        
        if worker_coros:
            task_objs, coros = zip(*worker_coros)
            results = await asyncio.gather(*coros, return_exceptions=True)
            
            for task, result in zip(task_objs, results):
                if isinstance(result, Exception):
                    task.code_result = f"# Error: {result}"
                    task.status = "failed"
                else:
                    task.code_result = result
                    task.status = "completed"
    
    async def _execute_single_worker(
        self,
        worker_id: int,
        project_context: str,
        task_description: str,
        system_apis: str,
        new_apis: str,
        workflow_id: int
    ) -> str:
        """执行单个 Worker"""
        result = await self.worker_chain.arun(
            worker_id=worker_id,
            project_context=project_context,
            task_description=task_description,
            system_apis=system_apis,
            new_apis=new_apis
        )
        
        print(f"\n{'='*70}")
        print(f"👷 工作流{workflow_id}的WORKER #{worker_id} 输出:")
        print(f"{'='*70}")
        print(result)
        print(f"{'='*70}\n")
        
        return result
    
    async def _execute_evaluators(
        self,
        tasks: List[SubTaskWithAPI],
        workflow_id: int
    ) -> List[EvaluationReport]:
        """为每个 Worker 的输出生成评审报告"""
        evaluator_coros = []
        
        for task in tasks:
            if task.status != "completed":
                continue
            
            # 格式化 API 要求
            system_apis_req = ", ".join([api.name for api in task.system_apis]) or "无"
            new_apis_req = ", ".join([f"{api.signature}" for api in task.new_apis]) or "无"
            
            worker_code = task.code_result or ""
            
            coro = self._execute_single_evaluator(
                task.id, task.assigned_worker, task.description,
                system_apis_req, new_apis_req, worker_code, workflow_id
            )
            evaluator_coros.append((task.id, coro))
        
        if evaluator_coros:
            task_ids, coros = zip(*evaluator_coros)
            reports = await asyncio.gather(*coros, return_exceptions=True)
            
            valid_reports = []
            for task_id, report in zip(task_ids, reports):
                if isinstance(report, Exception):
                    print(f"  ⚠️  Evaluator for Task {task_id} failed: {report}")
                    # 创建一个默认的失败报告
                    fallback_report = EvaluationReport(
                        worker_id=task_id,
                        task_id=task_id,
                        overall_score=0.3,
                        needs_revision=True,
                        report_text=f"Evaluator 执行失败: {str(report)}"
                    )
                    valid_reports.append(fallback_report)
                else:
                    valid_reports.append(report)
            
            return valid_reports
        
        return []
    
    async def _execute_single_evaluator(
        self,
        task_id: int,
        worker_id: int,
        task_description: str,
        required_system_apis: str,                              
        required_new_apis: str,   
        worker_code: str,
        workflow_id: int 
    ) -> EvaluationReport:
        """执行单个 Evaluator"""
        report_text = await self.evaluator_chain.arun(
            task_description=task_description,
            required_system_apis=required_system_apis,
            required_new_apis=required_new_apis,
            worker_code=worker_code
        )
        
        print(f"\n{'='*70}")
        print(f"📊 工作流{workflow_id}的EVALUATOR #{task_id} (审查 Worker #{worker_id}) 输出:")
        print(f"{'='*70}")
        print(report_text)
        print(f"{'='*70}\n")
        
        report = parse_evaluation_report(report_text, worker_id, task_id)
        return report
    
    async def _execute_verifier(
        self,
        original_prompt: str,
        project_context: str,
        tasks: List[SubTaskWithAPI],
        evaluation_reports: List[EvaluationReport],
        workflow_id: int 
    ) -> VerificationResult:
        """执行 Verifier（基于 Evaluator 报告进行整合、跨模块检查、最终决策）"""
        
        # ========== Step 1: 构造报告文本供 LLM 分析 ==========
        full_reports = []
        
        for r in evaluation_reports:
            report_block = f"""{'='*60}
    Task {r.task_id} - Full Evaluation Report (Worker #{r.worker_id})
    {'='*60}

    {r.report_text.strip()}

    {'='*60}
    """
            full_reports.append(report_block)
        
        reports_text = "\n".join(full_reports)
        
        # 打印调试信息
        print("\n" + "="*70)
        print("[DEBUG] 发送给 Verifier 的完整评审报告：")
        print("="*70)
        print(f"总长度: {len(reports_text)} 字符")
        print(f"报告数量: {len(full_reports)}")
        print("="*70)
        print(reports_text[:500] + "\n... [后续内容省略] ...\n")
        print("="*70 + "\n")
        
        # ========== Step 2: 调用 Verifier LLM 生成描述性总结 ==========
        verifier_output = await self.verifier_chain.arun(
            original_prompt=original_prompt,
            project_context=project_context,
            all_evaluation_reports=reports_text
        )
        
        print(f"\n{'='*70}")
        print(f"✅ 工作流{workflow_id}的VERIFIER 输出:")
        print(f"{'='*70}")
        print(verifier_output)
        print(f"{'='*70}\n")
        
        # ========== Step 3: 基于 EvaluationReport 数据结构做硬性判断 ==========
        print("\n" + "="*70)
        print("🔍 [DEBUG] Verifier 基于结构化数据做决策")
        print("="*70)
        
        result = VerificationResult()
        
        # 3.1 计算综合质量分数
        if evaluation_reports:
            avg_score = sum(r.overall_score for r in evaluation_reports) / len(evaluation_reports)
            result.quality_score = avg_score
            print(f"📊 综合质量分数: {result.quality_score:.2f} (平均值)")
        else:
            result.quality_score = 0.0
            print(f"⚠️  无有效评审报告，质量分数默认为 0.0")
        
        # 3.2 识别需要修订的模块
        modules_need_revision = []
        revision_details = []
        
        for r in evaluation_reports:
            if r.needs_revision:
                modules_need_revision.append(r.task_id)
                
                # 收集修订原因
                reasons = []
                if r.api_compliance_score and r.api_compliance_score < 0.8:
                    reasons.append(f"API合规 {r.api_compliance_score:.2f}")
                if r.code_quality_score and r.code_quality_score < 0.8:
                    reasons.append(f"代码质量 {r.code_quality_score:.2f}")
                if r.logic_correctness_score and r.logic_correctness_score < 0.8:
                    reasons.append(f"逻辑正确 {r.logic_correctness_score:.2f}")
                
                detail = f"Task {r.task_id}: {', '.join(reasons) if reasons else '综合评分不足'}"
                revision_details.append(detail)
                
                print(f"⚠️  Task {r.task_id} 需要修订:")
                print(f"   - 评分: API={r.api_compliance_score:.2f}, 质量={r.code_quality_score:.2f}, 逻辑={r.logic_correctness_score:.2f}")
                if r.recommendations:
                    print(f"   - 建议数: {len(r.recommendations)}")
                    for idx, rec in enumerate(r.recommendations[:2], 1):
                        print(f"     {idx}. {rec[:60]}...")
        
        result.modules_need_revision = modules_need_revision
        
        # 3.3 判断是否通过（硬性标准）
        MODULE_THRESHOLD = 0.8  # 单模块80分标准
        
        # 检查所有模块是否达标
        all_modules_pass = all(r.overall_score >= MODULE_THRESHOLD for r in evaluation_reports)
        
        result.overall_pass = (        
            all_modules_pass and
            len(modules_need_revision) == 0
        )
        
        print(f"\n🎯 最终决策:")
        print(f"   - 所有模块达标: {all_modules_pass}")
        print(f"   - 需要修订的模块: {modules_need_revision if modules_need_revision else '无'}")
        print(f"   - 最终判定: {'✅ Pass' if result.overall_pass else '❌ Fail'}")
        
        # 3.4 生成修订指令（增强版：同时填充结构化数据）
        if not result.overall_pass:
            revision_instructions = []
            
            for r in evaluation_reports:
                if r.needs_revision:
                    # 🔥 存储结构化的修订指令
                    result.task_revision_instructions[r.task_id] = {
                        "scores": {
                            "api": r.api_compliance_score or 0.0,
                            "quality": r.code_quality_score or 0.0,
                            "logic": r.logic_correctness_score or 0.0,
                            "overall": r.overall_score
                        },
                        "recommendations": r.recommendations.copy(),
                        "task_description": tasks[r.task_id - 1].description if r.task_id <= len(tasks) else ""
                    }
                    
                    # 生成人类可读的文本指令
                    task_instruction = f"\n**Task {r.task_id} 修订要求:**"
                    
                    # 添加分数不足的项
                    if r.api_compliance_score and r.api_compliance_score < 0.8:
                        task_instruction += f"\n- 改进 API 合规性 (当前 {r.api_compliance_score:.2f})"
                    if r.code_quality_score and r.code_quality_score < 0.8:
                        task_instruction += f"\n- 提升代码质量 (当前 {r.code_quality_score:.2f})"
                    if r.logic_correctness_score and r.logic_correctness_score < 0.8:
                        task_instruction += f"\n- 修正逻辑错误 (当前 {r.logic_correctness_score:.2f})"
                    
                    # 添加具体建议
                    if r.recommendations:
                        task_instruction += "\n\n具体建议:"
                        for idx, rec in enumerate(r.recommendations, 1):
                            task_instruction += f"\n  {idx}. {rec}"
                    
                    revision_instructions.append(task_instruction)
            
            result.integrated_report = "\n".join(revision_instructions)
            print(f"\n📝 修订指令已生成 ({len(revision_instructions)} 个任务)")
        else:
            result.integrated_report = "所有模块均通过验证，无需修订。"
            print(f"\n✅ 无需修订")
        
        print("="*70 + "\n")
        
        # ========== Step 4: 如果通过，整合所有代码 ==========
        if result.overall_pass:
            all_code_blocks = []
            for task in tasks:
                if task.code_result:
                    all_code_blocks.append(f"# === Module: {task.description} ===\n{task.code_result}\n")
            result.final_code = "\n\n".join(all_code_blocks)
        
        return result

    

