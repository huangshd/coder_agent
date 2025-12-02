# Parrot 系统学习指南：任务调度和引擎实例管理

> 本文档整理了 Parrot 系统中关于**智能体任务调度**和**LLM引擎实例管理**的核心代码，便于快速学习和理解系统架构。

---

## 📋 目录

1. [系统总体架构](#系统总体架构)
2. [任务调度（Scheduler）详解](#任务调度scheduler详解)
3. [引擎实例管理](#引擎实例管理)
4. [关键数据结构](#关键数据结构)
5. [工作流程示例](#工作流程示例)
6. [核心代码速查](#核心代码速查)

---

## 系统总体架构

### Parrot 分布式系统架构图

```
┌─────────────────────────────────────────────────────────┐
│         Client Application (语义变量程序)               │
│              SemanticVariable编写的程序                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP RPC 通信
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   OS Server (系统核心)                   │
│  ┌─────────────────────────────────────────────────────┐│
│  │ PCore (Parrot OS Core)                              ││
│  │ ├─ ThreadDispatcher (线程调度和分配)                ││
│  │ ├─ MemorySpace (全局内存管理)                       ││
│  │ ├─ Executor (线程执行引擎)                          ││
│  │ ├─ Process Manager (进程管理)                       ││
│  │ └─ Tokenizer (分词器)                              ││
│  └─────────────────────────────────────────────────────┘│
└────────────────────┬────────────────────────────────────┘
                     │ HTTP 分配任务，心跳通信
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │Engine 0 │ │Engine 1 │ │Engine N │
   │         │ │         │ │         │
   │Scheduler│ │Scheduler│ │Scheduler│  (多个引擎实例)
   │Executor │ │Executor │ │Executor │
   └─────────┘ └─────────┘ └─────────┘
```

### 核心层次说明

| 层级 | 主要模块 | 职责 |
|------|---------|------|
| **应用层** | `parrot/program/` | 语义变量程序定义、优化、执行 |
| **协议层** | `parrot/protocol/` | RPC通信协议、数据格式定义 |
| **OS层** | `parrot/os/` | 线程调度、内存管理、进程管理 |
| **引擎层** | `parrot/engine/` | LLM推理、任务调度、Scheduler实现 |

---

## 任务调度（Scheduler）详解

### 📍 代码位置
- **主文件**：[parrot/engine/scheduler.py](parrot/engine/scheduler.py)
- **任务定义**：[parrot/engine/primitive_job.py](parrot/engine/primitive_job.py)
- **配置**：[parrot/engine/config.py](parrot/engine/config.py)（SchedulerConfig）

### 核心概念

#### 1. PrimitiveJob（基础任务）

任务是调度的基本单位，分为两种类型：

```python
# 基类定义
class PrimitiveJob:
    """所有引擎任务的基类"""
    def __init__(self,
        pid: int,              # 进程ID
        tid: int,              # 线程ID
        context_id: int,       # 上下文ID（唯一标识一个语义变量链）
        parent_context_id: int, # 父上下文ID（用于前缀共享）
        end_flag: bool,        # 是否为最后一个任务
    ):
        self.context: Optional[LowLevelContext] = None  # 上下文信息
        self.finish_event = Event()  # 任务完成事件
        self.start_time: float = -1
        self.end_time: float = -1
```

#### 2. Fill（填充任务 - Prefill阶段）

- **目标**：填充KV缓存，扩展上下文
- **输入**：token序列
- **输出**：更新后的KV缓存

```python
class Fill(PrimitiveJob):
    """填充任务，对应LLM的prefill阶段"""
    def __init__(self, ...,
        token_ids: Optional[List[int]] = None,  # 输入token IDs
        text: Optional[str] = None,             # 输入文本
    ):
        ...
```

**用途**：
- 初始化LLM上下文
- 处理长输入文本的编码
- 支持批处理多个填充请求

#### 3. Generate（生成任务 - Decode阶段）

- **目标**：逐个生成输出token
- **输入**：采样配置
- **输出**：token流

```python
class Generate(PrimitiveJob):
    """生成任务，对应LLM的decode阶段"""
    def __init__(self, ...,
        sampling_config: SamplingConfig,  # 采样配置
    ):
        self.output_queue: AsyncQueue[int] = AsyncQueue()  # 输出token队列
        self.gen_text = ""
        self.gen_length = 0

    def put_token(self, token_id: int) -> None:
        """添加生成的token"""
        self.output_queue.put_nowait(token_id)
        self.context.push_token_id(token_id)  # 更新上下文
        self.gen_length += 1

    def check_stop(self) -> bool:
        """检查是否应该停止生成"""
        token_id = self.context.get_last_token_id()
        return (
            token_id in self.sampling_config.stop_token_ids or
            self.gen_length >= self.sampling_config.max_gen_length
        )

    async def generator(self):
        """异步生成器，用于流式输出"""
        while True:
            token_id = await self.output_queue.get()
            if self.check_stop():
                break
            yield token_id.to_bytes(4, 'big')
```

**用途**：
- 逐token生成输出
- 支持流式传输
- 与采样配置集成（温度、top-k等）

---

### Scheduler 类详解

#### 类结构

```python
class Scheduler:
    """引擎的调度器，负责批处理任务"""

    def __init__(self, config: SchedulerConfig):
        self.max_batch_size: int              # 最大批大小
        self.max_num_batched_tokens: int      # 批中最大token数
        self.max_total_tokens: int            # 总最大token数（含前缀）

        self.waiting_jobs: List[PrimitiveJob] = []  # 等待队列
        self.running_jobs: List[PrimitiveJob] = []  # 运行队列

        self.policy: str                      # 调度策略

        # 统计信息
        self._job_arrival_time: Dict[int, float] = {}      # context_id -> 到达时间
        self._thread_arrival_time: Dict[str, float] = {}   # pid_tid -> 到达时间
```

#### 调度流程

```
┌─────────────────────────────────────────┐
│     新任务到达                          │
│     add_job(job)                        │
└────────────┬────────────────────────────┘
             ▼
┌─────────────────────────────────────────┐
│     调度函数                            │
│     schedule() -> List[PrimitiveJob]    │
└────────────┬────────────────────────────┘
             │
    ┌────────┴──────────┐
    ▼                   ▼
选择调度策略         检查约束
(fifo_v1, tgi)  max_batch_size
                max_num_batched_tokens
                max_total_tokens
    │                   │
    └─────────┬─────────┘
              ▼
       从 waiting_jobs 队列中
       依次选择满足约束的任务
              │
              ▼
       加入 running_jobs
       更新统计信息
              │
              ▼
    ┌────────────────────┐
    │ 任务完成           │
    │ finish() 检查      │
    │ finish_event.is_set│
    │ 从running移除      │
    └────────────────────┘
```

#### 关键方法

##### 1. `add_job(job: PrimitiveJob)` - 添加任务

```python
def add_job(self, job: PrimitiveJob):
    """添加任务到等待队列"""
    self.waiting_jobs.append(job)
    cur_time = time.perf_counter()

    # 记录任务到达时间（用于公平性）
    self._job_arrival_time[job.context_id] = cur_time

    # 记录线程首次到达时间
    key = f"{job.pid}_{job.tid}"
    if key not in self._thread_arrival_time:
        self._thread_arrival_time[key] = cur_time
```

**作用**：
- 保存任务到待调度队列
- 记录到达时间（用于统计和公平调度）

##### 2. `schedule() -> List[PrimitiveJob]` - 核心调度函数

**调度策略 1: FIFO_V1（标准FIFO + 前缀共享）**

```python
if self.policy == "fifo_v1":
    # 初始化当前使用情况
    cur_num_jobs = len(self.running_jobs)
    cur_num_batched_tokens = len(self.running_jobs)  # 每个Generate = 1 token
    cur_total_tokens = 0

    # 计算当前Token占用（考虑前缀共享）
    visited_context_ids = set()
    for job in self.running_jobs:
        assert isinstance(job, Generate)
        ctx = job.context
        if ctx.context_id not in visited_context_ids:
            cur_total_tokens += ctx.get_this_context_len()  # 只计算一次
            visited_context_ids.add(ctx.context_id)
        # 父上下文也需要计算（一次）
        parent_ctx = ctx.parent_context
        if parent_ctx and parent_ctx.context_id not in visited_context_ids:
            cur_total_tokens += parent_ctx.get_this_context_len()
            visited_context_ids.add(parent_ctx.context_id)

    # 从等待队列依次尝试调度任务
    while self.waiting_jobs:
        job = self.waiting_jobs[0]  # 获取最老的任务

        # 计算任务所需的token数
        job_num_tokens = (
            1 if isinstance(job, Generate) or job.token_ids is None
            else len(job.token_ids)  # Fill的token数
        )

        job_total_tokens = job.context.get_this_context_len()
        if (job.context.parent_context and
            job.context.parent_context.context_id not in visited_context_ids):
            job_total_tokens += job.context.parent_context.get_this_context_len()

        # 约束检查
        if cur_num_jobs + 1 > self.max_batch_size:
            break  # 无法再添加批任务
        if cur_num_batched_tokens + job_num_tokens > self.max_num_batched_tokens:
            break  # 无法容纳更多token
        if cur_total_tokens + job_total_tokens > self.max_total_tokens:
            break  # 内存不足

        # 调度这个任务
        self.running_jobs.append(job)
        if job.start_time == -1:
            job.start_time = time.perf_counter_ns()
        self.waiting_jobs.pop(0)

        # 更新约束计数
        cur_num_jobs += 1
        cur_num_batched_tokens += job_num_tokens
        cur_total_tokens += job_total_tokens

    return self.running_jobs.copy()
```

**约束说明**：
- `max_batch_size`: 批内最多任务数
- `max_num_batched_tokens`: 批内所有token数（不计前缀）
- `max_total_tokens`: 总token数（包括前缀和共享）

**调度策略 2: TGI（Fill优先，抢占Generate）**

```python
if self.policy == "tgi":
    # Fill优先级更高，可以抢占Generate任务

    # 1. 从等待队列中收集所有Fill任务
    fill_running_jobs = []
    cur_tokens_sum = 0

    for job in self.waiting_jobs:
        if not isinstance(job, Fill):
            continue

        job_num_tokens = len(job.token_ids) if job.token_ids else 0

        if cur_tokens_sum + job_num_tokens > self.max_num_batched_tokens:
            break

        fill_running_jobs.append(job)
        if job.start_time == -1:
            job.start_time = time.perf_counter_ns()
        cur_tokens_sum += job_num_tokens

    # 2. 如果有Fill任务要调度，抢占所有Generate任务
    if len(fill_running_jobs) > 0:
        # 移除Fill任务从等待队列
        self.waiting_jobs = [
            job for job in self.waiting_jobs if job not in fill_running_jobs
        ]

        # 所有Running的Generate任务重新加入等待队列
        self.waiting_jobs = self.running_jobs + self.waiting_jobs  # 保持FIFO顺序
        self.running_jobs = fill_running_jobs
        return fill_running_jobs.copy()

    # 3. 没有Fill任务，继续普通FIFO调度Generate任务
    # ... (与策略1的非fill部分相同)
```

**特点**：
- Fill任务有更高优先级
- 可以抢占正在运行的Generate任务
- 适合有复杂prefill的workload

**调度策略 3: 默认FIFO（无前缀共享优化）**

```python
else:
    # 不考虑前缀共享，每次都计算完整token数

    # 按线程到达时间和任务到达时间排序
    self.running_jobs.sort(
        key=lambda job: (
            self._thread_arrival_time[f"{job.pid}_{job.tid}"],
            self._job_arrival_time[job.context_id],
        )
    )

    # 应用总token约束
    new_running: List[PrimitiveJob] = []
    cur_total_tokens = 0
    preempted = False

    for job in self.running_jobs:
        if preempted:
            self._preempt(job)  # 移到等待队列前面
            continue

        job_tokens = job.context.get_context_len()
        if cur_total_tokens + job_tokens > self.max_total_tokens:
            # 内存超限，抢占此任务及之后任务
            preempted = True
            self._preempt(job)
            continue

        new_running.append(job)
        cur_total_tokens += job_tokens

    self.running_jobs = new_running
    return self.running_jobs.copy()
```

##### 3. `finish()` - 处理完成任务

```python
def finish(self):
    """检查并清理完成的任务"""
    new_running: List[PrimitiveJob] = []

    for job in self.running_jobs:
        if not job.finish_event.is_set():  # 未完成
            new_running.append(job)
        else:  # 已完成
            self.remove_job(job)
            job.end_time = time.perf_counter_ns()

            # 记录延迟统计
            latency_ms = (job.end_time - job.start_time) / 1e6
            logger.debug(f"Job {job} finished. Latency: {latency_ms} ms")

    self.running_jobs = new_running
```

#### 调度配置示例

```python
@dataclass
class SchedulerConfig:
    max_batch_size: int              # 例如：256
    max_num_batched_tokens: int      # 例如：8192
    max_total_tokens: int            # 例如：20480
    policy: Literal["fifo", "tgi"] = "fifo"  # 调度策略
```

---

## 引擎实例管理

### 📍 代码位置
- **引擎抽象**：[parrot/engine/llm_engine.py](parrot/engine/llm_engine.py)
- **OS级抽象**：[parrot/os/engine.py](parrot/os/engine.py)
- **引擎工厂**：[parrot/engine/engine_creator.py](parrot/engine/engine_creator.py)
- **内置引擎**：[parrot/engine/builtin/](parrot/engine/builtin/)
- **OpenAI兼容**：[parrot/engine/openai/](parrot/engine/openai/)
- **MLC LLM**：[parrot/engine/mlc_llm/](parrot/engine/mlc_llm/)

### 分层管理架构

```
┌──────────────────────────────────┐
│  Engine Layer (引擎进程内)        │
│                                  │
│  LLMEngine (抽象基类)             │
│  ├─ BuiltinEngine (自实现)       │
│  ├─ OpenAIEngine (OpenAI API)    │
│  └─ MLCEngine (MLC LLM)          │
│                                  │
│  Scheduler (任务调度)            │
│  Runner (推理执行)               │
└──────────────────────────────────┘
           ▲
           │ HTTP RPC
           │
┌──────────────────────────────────┐
│  OS Layer (系统进程内)           │
│                                  │
│  ExecutionEngine (OS级抽象)      │
│  ├─ 引擎注册和发现              │
│  ├─ 线程调度和分配              │
│  ├─ 运行时监控                  │
│  └─ 心跳和故障检测              │
└──────────────────────────────────┘
```

### LLMEngine - 引擎层抽象

#### 类定义和初始化

```python
class LLMEngine(ABC):
    """所有LLM引擎的基类，定义统一接口"""

    def __init__(self, engine_config: Dict, connect_to_os: bool = True):
        # 随机种子设置（复现性）
        set_random_seed(engine_config["random_seed"])

        self.connect_to_os = connect_to_os

        # OS服务器地址
        if self.connect_to_os:
            assert "os" in engine_config
            os_config = engine_config["os"]
            self.os_http_address = f"http://{os_config['host']}:{os_config['port']}"
        engine_config.pop("os")  # 移除后不再需要

        # 心跳线程（与OS保活通信）
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_daemon, daemon=True
        )
```

#### 核心接口

```python
class LLMEngine(ABC):
    # ========== 任务处理接口 ==========

    @abstractmethod
    async def fill(self, payload: Dict) -> Dict:
        """
        Fill操作：Prefill阶段，填充KV缓存

        Args:
            payload: 包含以下字段
                - context_id: 上下文ID
                - token_ids: token序列
                - text: 输入文本（可选）

        Returns:
            {'status': 'ok', ...}
        """
        ...

    @abstractmethod
    async def generate(self, payload: Dict) -> Dict:
        """
        Generate操作：Decode阶段，生成输出token

        Args:
            payload: 包含以下字段
                - context_id: 上下文ID
                - sampling_config: 采样参数

        Returns:
            {'status': 'ok', 'output_tokens': [...]}
        """
        ...

    @abstractmethod
    def generate_stream(self, payload: Dict) -> AsyncGenerator:
        """
        流式生成：逐token返回输出

        Returns:
            异步生成器，每次yield一个token
        """
        ...

    @abstractmethod
    async def free_context(self, payload: Dict) -> Dict:
        """
        释放上下文：清理KV缓存
        """
        ...

    @abstractmethod
    def get_runtime_info(self, profile: bool) -> EngineRuntimeInfo:
        """
        获取运行时信息：缓存使用量、任务数等
        """
        ...

    @abstractmethod
    async def engine_iter(self):
        """
        引擎迭代：在engine_loop中每个周期执行
        用于逐token推理、状态更新等
        """
        ...

    # ========== 注册和通信 ==========

    def _register_engine(self, engine_config: EngineConfig):
        """向OS注册引擎"""
        if self.connect_to_os:
            resp = register_engine(
                http_addr=self.os_http_address,
                engine_config=engine_config,
            )
            self.engine_id = resp.engine_id  # OS分配的引擎ID
        else:
            self.engine_id = 0

    def heartbeat(self):
        """发送心跳到OS"""
        if not self.connect_to_os:
            return

        engine_runtime_info = self.get_runtime_info(profile=False)

        resp = engine_heartbeat(
            http_addr=self.os_http_address,
            engine_id=self.engine_id,
            engine_name=self.engine_config.engine_name,
            runtime_info=engine_runtime_info,
        )

    def _heartbeat_daemon(self):
        """心跳守护线程，定期向OS发送状态"""
        while True:
            self.heartbeat()
            time.sleep(ENGINE_HEARTBEAT_INTERVAL)  # 例如：1秒

    async def engine_loop(self):
        """
        引擎主循环：
        1. 启动心跳线程
        2. 不断调用engine_iter()处理任务
        """
        self._heartbeat_thread.start()

        while True:
            await asyncio.sleep(ENGINE_LOOP_INTERVAL)  # 例如：0.01秒
            await self.engine_iter()
```

### ExecutionEngine - OS级引擎抽象

#### 类定义

```python
class ExecutionEngine:
    """OS级的引擎抽象，用于管理和监控远程引擎"""

    def __init__(
        self,
        engine_id: int,
        config: EngineConfig,
        tokenizer: Tokenizer,
    ):
        # ===== 基础配置 =====
        self.engine_id = engine_id          # OS分配的引擎ID
        self.config = config                # 引擎配置
        self.tokenizer = tokenizer          # 分词器
        self.dead = False                   # 是否已宕机

        # ===== 运行时状态 =====
        self.runtime_info = EngineRuntimeInfo()  # 最新运行时信息

        # ===== 线程管理 =====
        self.threads: List["Thread"] = []   # 分配给此引擎的线程
        self.threads_len: Dict[int, int] = {}  # thread_uid -> token数

        # ===== Token计数 =====
        self.tokens_num = 0  # 此引擎上所有线程的总token数
```

#### 关键属性

```python
class ExecutionEngine:
    @property
    def name(self) -> str:
        """引擎名称"""
        return self.config.engine_name

    @property
    def http_address(self) -> str:
        """引擎HTTP地址"""
        return f"http://{self.config.host}:{self.config.port}"

    @property
    def interpreter_type(self) -> InterpretType:
        """解释器类型（TOKEN_ID或TEXT）"""
        # 不同引擎类型使用不同的解释器
        return INTERPRET_TYPE_MAP[self.config.engine_type]
        # ENGINE_TYPE_BUILTIN -> InterpretType.TOKEN_ID
        # ENGINE_TYPE_OPENAI -> InterpretType.TEXT
        # ENGINE_TYPE_MLCLLM -> InterpretType.TEXT

    @property
    def remain_thread_locs(self) -> int:
        """还能接受多少个线程"""
        return self.config.threads_capacity - self.num_threads

    @property
    def num_threads(self) -> int:
        """当前线程数"""
        return len(self.threads)

    @property
    def requests_num_upperbound(self) -> int:
        """
        能处理的最大并发任务数
        = min(引擎线程容量，每个线程的请求上界)
        """
        return min(
            [self.config.threads_capacity] +
            [thread.requests_num_upperbound for thread in self.threads]
        )
```

#### 线程管理方法

```python
def accept_thread(self, thread: "Thread"):
    """接受一个线程分配到此引擎"""
    thread.engine = self

    # 计算线程的token数量
    thread_len = self.count_thread_token_nums(thread)

    self.threads.append(thread)
    self.threads_len[thread.unique_id] = thread_len
    self.tokens_num += thread_len

def remove_thread(self, thread: "Thread"):
    """从此引擎移除一个线程"""
    self.threads.remove(thread)
    self.tokens_num -= self.threads_len[thread.unique_id]
    self.threads_len.pop(thread.unique_id)

def count_thread_token_nums(self, thread: "Thread") -> int:
    """
    计算线程包含的总token数
    用于：
    1. 检查引擎负载
    2. 选择最合适的引擎
    """
    if self.config.engine_type != ENGINE_TYPE_BUILTIN:
        return 0  # TODO: 支持其他引擎类型

    tokenizer_name = self.config.tokenizer
    length = 0

    # 遍历线程函数体的每个部分
    for region in thread.call.func.body:
        if isinstance(region, ParameterLoc):
            # 参数区域
            value = thread.call.bindings[region.param.name]
            if isinstance(value, SVPlaceholder):
                length += value.max_length
            else:
                length += len(self.tokenizer.tokenize(value, tokenizer_name))
        else:
            # 常量区域
            assert isinstance(region, Constant)
            length += len(self.tokenizer.tokenize(region.text, tokenizer_name))

    return length
```

### 引擎工厂和创建

#### 工厂函数

```python
def create_engine(
    engine_config_path: str,
    connect_to_os: bool = True,
    override_args: Dict = {},
) -> LLMEngine:
    """
    创建引擎实例

    Args:
        engine_config_path: 配置文件路径
        connect_to_os: 是否连接到OS（True则注册并定期发送心跳）
        override_args: 覆盖配置的参数

    Returns:
        创建的LLMEngine实例

    示例配置文件：
    {
        "instance": {...},          # 引擎特定配置
        "scheduler": {...},         # 调度器配置
        "engine_name": "engine0",
        "engine_type": "builtin",   # builtin/openai/mlcllm
        "model": "meta-llama/Llama-2-7b",
        "tokenizer": "meta-llama/Llama-2-7b",
        "host": "127.0.0.1",
        "port": 8000,
        "os": {                     # 可选，connect_to_os=True时需要
            "host": "127.0.0.1",
            "port": 8080
        }
    }
    """

    with open(engine_config_path) as f:
        engine_config = dict(json.load(f))

    # 应用覆盖参数
    if "device" in override_args:
        engine_config["instance"]["device"] = override_args["device"]
        override_args.pop("device")
    engine_config.update(override_args)

    # 验证配置
    if not EngineConfig.verify_config(engine_config):
        raise ParrotEngineInternalError(f"Invalid engine config")

    # 根据引擎类型创建对应实例
    engine_type = engine_config["engine_type"]

    if engine_type == ENGINE_TYPE_BUILTIN:
        return BuiltinEngine(engine_config, connect_to_os)
    elif engine_type == ENGINE_TYPE_MLCLLM:
        return MLCEngine(engine_config, connect_to_os)
    elif engine_type == ENGINE_TYPE_OPENAI:
        return OpenAIEngine(engine_config, connect_to_os)
    else:
        raise ParrotEngineInternalError(f"Unsupported engine type")
```

#### 支持的引擎类型

| 类型 | 文件 | 特点 | 使用场景 |
|------|------|------|---------|
| `builtin` | [parrot/engine/builtin/builtin_engine.py](parrot/engine/builtin/builtin_engine.py) | 自实现推理，优化的kernel | 本地推理，需要高性能 |
| `openai` | [parrot/engine/openai/openai_engine.py](parrot/engine/openai/openai_engine.py) | 调用OpenAI API | 无需本地GPU，使用云服务 |
| `mlcllm` | [parrot/engine/mlc_llm/mlc_engine.py](parrot/engine/mlc_llm/mlc_engine.py) | MLC LLM框架 | 跨平台推理 |

---

## 关键数据结构

### EngineConfig

```python
@dataclass
class EngineConfig:
    # ===== 模型信息 =====
    model: str = "unknown"              # 模型名称
    tokenizer: str = "unknown"          # 分词器

    # ===== 网络配置 =====
    host: str = "127.0.0.1"
    port: int = 8000                    # 引擎HTTP端口

    # ===== 引擎标识 =====
    engine_name: str = "unknown"        # 引擎名称
    engine_type: str = ENGINE_TYPE_BUILTIN  # builtin/openai/mlcllm

    # ===== 基础参数 =====
    random_seed: int = 0
    dtype: Literal["float16", "float32"] = "float16"
    device: str = "cuda"
    fill_chunk_size: int = FILL_NO_CHUNK

    # ===== 容量 =====
    threads_capacity: int = 256         # 最多能处理多少个线程
    tokens_capacity: int = 262144       # 最多能处理多少个token

    @classmethod
    def verify_config(cls, config: Dict) -> bool:
        """验证配置完整性"""
        if "instance" not in config or "scheduler" not in config:
            return False
        if config["engine_type"] not in ENGINE_TYPES:
            return False
        return True
```

### SamplingConfig

```python
@dataclass
class SamplingConfig:
    """采样配置，用于生成阶段"""
    temperature: float = 0.7          # 温度参数
    top_p: float = 1.0                # top-p采样
    top_k: int = -1                   # top-k采样
    max_gen_length: int = 512         # 最大生成长度
    stop_token_ids: List[int] = []    # 停止token
```

### LowLevelContext

```python
class LowLevelContext:
    """
    低级上下文：表示KV缓存中的一个上下文

    在Parrot中，上下文形成树状结构：
    - 根上下文：初始输入
    - 子上下文：基于前缀的新上下文（前缀共享）
    """

    context_id: int                      # 唯一上下文ID
    parent_context: Optional[LowLevelContext]  # 父上下文（用于前缀）
    tokens: List[int] = []              # 此上下文的token列表

    def get_this_context_len(self) -> int:
        """获取此上下文独有的token数（不含前缀）"""
        return len(self.tokens)

    def get_context_len(self) -> int:
        """获取完整上下文长度（含前缀）"""
        length = len(self.tokens)
        if self.parent_context:
            length += self.parent_context.get_context_len()
        return length
```

### EngineRuntimeInfo

```python
@dataclass
class EngineRuntimeInfo:
    """
    引擎运行时信息，由引擎定期（心跳）发送给OS
    用于：
    1. 监控引擎状态
    2. 负载均衡决策
    3. 故障检测
    """

    num_running_jobs: int = 0           # 运行中的任务数
    num_waiting_jobs: int = 0           # 等待中的任务数
    num_cached_tokens: int = 0          # 缓存的token数
    cached_tokens_size_bytes: int = 0   # 缓存大小（字节）
    latency_ms: float = 0.0             # 最近任务延迟
    throughput_tokens_per_sec: float = 0.0  # 吞吐量
    utilization_rate: float = 0.0       # GPU使用率

    def display(self) -> str:
        """格式化显示"""
        return f"""
        Running jobs: {self.num_running_jobs}
        Waiting jobs: {self.num_waiting_jobs}
        Cached tokens: {self.num_cached_tokens}
        Cache size: {self.cached_tokens_size_bytes / 1e6:.2f} MB
        Latency: {self.latency_ms:.2f} ms
        Throughput: {self.throughput_tokens_per_sec:.2f} tokens/s
        Utilization: {self.utilization_rate:.2f}%
        """
```

---

## 工作流程示例

### 完整请求处理流程

#### 1. 应用提交任务

```python
# 用户应用（使用SemanticVariable编写）
app = MyParrotApp(...)  # 包含多个函数调用

# OS Server收到请求
POST http://os_server:8080/submit_task
{
    "pid": 1,
    "tid": 1,
    "program": <serialized_program>,
    "args": {...}
}
```

#### 2. OS分配线程和引擎

```
OS Server:
├─ Process: pid=1, tid=1
├─ Thread分析：
│  └─ 计算token需求：total_tokens = 1024
├─ 选择合适的引擎：
│  └─ Engine0: tokens_num=512, capacity=4096
│     -> remain = 3584 > 1024 ✓
├─ 分配Thread到Engine0
└─ Engine0.accept_thread(thread)
   └─ Update: Engine0.tokens_num = 1536
```

#### 3. 线程在引擎上执行

```
Engine0:

第1步：Prefill (Fill任务)
┌──────────────────────────────────────────┐
│ Fill(pid=1, tid=1, context_id=1,        │
│      token_ids=[0,1,2,...,255])          │
│                                          │
│ Scheduler.add_job(job)                   │
│  -> waiting_jobs = [Fill1]               │
│                                          │
│ Scheduler.schedule()                     │
│  -> 检查约束: OK                         │
│  -> running_jobs = [Fill1]               │
│  -> return [Fill1]                       │
│                                          │
│ Engine执行Fill1:                         │
│  - 计算attention: q,k,v                 │
│  - 写入KV缓存                           │
│  - 更新context: [0,...,255]             │
└──────────────────────────────────────────┘

第2步：Decode (Generate任务)
┌──────────────────────────────────────────┐
│ Generate(pid=1, tid=1,                   │
│          context_id=1,                   │
│          sampling_config={...})          │
│                                          │
│ Scheduler.add_job(job)                   │
│  -> waiting_jobs = [Generate1]           │
│                                          │
│ Scheduler.schedule()                     │
│  -> running_jobs = [Generate1]           │
│                                          │
│ Engine逐token生成：                      │
│  while not stop:                         │
│    - 读KV缓存，计算logits               │
│    - 采样生成token                       │
│    - job.put_token(token_id)             │
│    - context.push_token_id(token_id)     │
│    - job.check_stop()                    │
│                                          │
│ job.finish_event.set()                   │
│ Scheduler.finish() -> 清除完成的任务    │
└──────────────────────────────────────────┘
```

#### 4. 心跳和监控

```
Engine线程:                    OS线程:
every 1s:                      每5s检查:
├─ get_runtime_info()          ├─ 检查引擎心跳
├─ engine_heartbeat()          ├─ 监控线程状态
│  send to OS:                 └─ 更新分配决策
│  {
│    engine_id: 0,
│    num_running_jobs: 5,
│    num_waiting_jobs: 10,
│    num_cached_tokens: 2048,
│    ...
│  }
```

---

## 核心代码速查

### 文件导航表

| 功能 | 文件位置 | 关键类/函数 |
|------|---------|-----------|
| **任务调度** | [parrot/engine/scheduler.py](parrot/engine/scheduler.py) | `Scheduler` |
| **任务定义** | [parrot/engine/primitive_job.py](parrot/engine/primitive_job.py) | `PrimitiveJob`, `Fill`, `Generate` |
| **引擎抽象** | [parrot/engine/llm_engine.py](parrot/engine/llm_engine.py) | `LLMEngine` |
| **OS引擎** | [parrot/os/engine.py](parrot/os/engine.py) | `ExecutionEngine` |
| **OS核心** | [parrot/os/pcore.py](parrot/os/pcore.py) | `PCore` |
| **线程分配** | [parrot/os/thread_dispatcher.py](parrot/os/thread_dispatcher.py) | `ThreadDispatcher` |
| **线程执行** | [parrot/os/process/executor.py](parrot/os/process/executor.py) | `Executor` |
| **引擎创建** | [parrot/engine/engine_creator.py](parrot/engine/engine_creator.py) | `create_engine()` |
| **配置** | [parrot/engine/config.py](parrot/engine/config.py) | `EngineConfig`, `SchedulerConfig` |

### 快速查找

#### 看调度相关的代码：
1. 调度主逻辑：[scheduler.py:77-268](parrot/engine/scheduler.py#L77-L268)
2. FIFO_V1策略：[scheduler.py:80-148](parrot/engine/scheduler.py#L80-L148)
3. TGI策略：[scheduler.py:151-180](parrot/engine/scheduler.py#L151-L180)

#### 看引擎管理的代码：
1. 引擎基类：[llm_engine.py](parrot/engine/llm_engine.py)
2. OS级引擎：[parrot/os/engine.py](parrot/os/engine.py)
3. 内置引擎实现：[parrot/engine/builtin/builtin_engine.py](parrot/engine/builtin/builtin_engine.py)

#### 看OS核心：
1. PCore主循环：[pcore.py:95-120](parrot/os/pcore.py#L95-L120)
2. 线程分配器：[parrot/os/thread_dispatcher.py](parrot/os/thread_dispatcher.py)

---

## 相关论文

**主论文**：`Parrot efficient serving of LLMbased applications with semantic variable.pdf`

**核心贡献**：
- 语义变量（Semantic Variable）概念
- 前缀共享优化（Prefix Sharing）
- 智能任务调度策略
- 分布式引擎管理

---

## 学习路径建议

### 初级：理解基本概念
1. 阅读本文档的"系统总体架构"部分
2. 学习PrimitiveJob的两种类型（Fill/Generate）
3. 理解Scheduler的约束和调度策略

### 中级：深入调度实现
1. 分析Scheduler.schedule()的FIFO_V1策略
2. 理解前缀共享对token计数的影响
3. 学习任务完成处理（finish()方法）

### 高级：引擎管理和分布式
1. 研究LLMEngine的心跳和注册机制
2. 理解ExecutionEngine的线程管理
3. 学习PCore的多引擎管理
4. 分析ThreadDispatcher的分配算法

### 实战：修改和扩展
1. 实现新的调度策略（修改scheduler.py）
2. 添加新的引擎类型（继承LLMEngine）
3. 实现自定义监控指标（修改EngineRuntimeInfo）

---

**文档最后更新**：2025年11月
