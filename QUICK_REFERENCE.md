# Parrot 代码速查手册

> 快速查找Parrot系统中关于任务调度和引擎管理的关键代码位置和实现细节

---

## 📌 目录

1. [快速查找表](#快速查找表)
2. [调度相关代码](#调度相关代码)
3. [引擎管理代码](#引擎管理代码)
4. [关键数据结构](#关键数据结构)
5. [API速查](#api速查)
6. [常见问题解答](#常见问题解答)

---

## 快速查找表

### 我要找...

| 需求 | 对应文件 | 关键函数/类 | 行号 |
|------|---------|----------|------|
| **任务调度逻辑** | [scheduler.py](parrot/engine/scheduler.py) | `Scheduler.schedule()` | 77-268 |
| **FIFO_V1策略** | [scheduler.py](parrot/engine/scheduler.py) | fifo_v1分支 | 80-148 |
| **TGI策略** | [scheduler.py](parrot/engine/scheduler.py) | tgi分支 | 151-180 |
| **任务定义** | [primitive_job.py](parrot/engine/primitive_job.py) | `PrimitiveJob`, `Fill`, `Generate` | 13-123 |
| **Fill任务** | [primitive_job.py](parrot/engine/primitive_job.py) | `class Fill` | 36-63 |
| **Generate任务** | [primitive_job.py](parrot/engine/primitive_job.py) | `class Generate` | 66-123 |
| **引擎基类** | [llm_engine.py](parrot/engine/llm_engine.py) | `class LLMEngine` | 22-165 |
| **OS级引擎** | [parrot/os/engine.py](parrot/os/engine.py) | `class ExecutionEngine` | 33-132 |
| **引擎创建** | [engine_creator.py](parrot/engine/engine_creator.py) | `create_engine()` | 22-59 |
| **调度器配置** | [config.py](parrot/engine/config.py) | `SchedulerConfig` | 87-92 |
| **引擎配置** | [config.py](parrot/engine/config.py) | `EngineConfig` | 95-154 |
| **采样配置** | [protocol/sampling_config.py](parrot/protocol/sampling_config.py) | `SamplingConfig` | - |
| **OS核心** | [pcore.py](parrot/os/pcore.py) | `class PCore` | 36-250+ |
| **线程分配** | [thread_dispatcher.py](parrot/os/thread_dispatcher.py) | `ThreadDispatcher` | - |
| **线程执行** | [executor.py](parrot/os/process/executor.py) | `class Executor` | 19-69 |
| **上下文管理** | [low_level_context.py](parrot/engine/context/low_level_context.py) | `LowLevelContext` | - |
| **心跳机制** | [llm_engine.py](parrot/engine/llm_engine.py) | `heartbeat()`, `_heartbeat_daemon()` | 120-165 |

---

## 调度相关代码

### 1. Scheduler 快速参考

#### 初始化

```python
# parrot/engine/scheduler.py:21-29

from .config import SchedulerConfig

scheduler = Scheduler(config=SchedulerConfig(
    max_batch_size=256,
    max_num_batched_tokens=8192,
    max_total_tokens=20480,
    policy="fifo_v1"
))
```

#### 添加任务

```python
# parrot/engine/scheduler.py:38-46

scheduler.add_job(job)  # job: PrimitiveJob (Fill or Generate)

# 内部逻辑：
# - 添加到waiting_jobs队列
# - 记录到达时间用于统计
```

#### 核心调度

```python
# parrot/engine/scheduler.py:77-268

jobs_to_run = scheduler.schedule()  # List[PrimitiveJob]

# 返回本轮可以执行的任务
# 遵循约束条件：
#   - max_batch_size: 任务数
#   - max_num_batched_tokens: batch内token数
#   - max_total_tokens: 含前缀的总token数
```

#### 完成处理

```python
# parrot/engine/scheduler.py:274-289

scheduler.finish()

# 内部逻辑：
# - 检查running_jobs中各任务的finish_event
# - 记录完成时间和延迟
# - 从running_jobs中移除已完成任务
```

### 2. 任务生命周期

```python
# parrot/engine/primitive_job.py

# Fill 任务
fill_job = Fill(
    pid=1,
    tid=1,
    context_id=1,
    parent_context_id=-1,  # 无父上下文
    end_flag=False,
    token_ids=[0, 1, 2, 3, ...],  # 输入token
    text="Hello world"  # 或者输入文本
)

# Generate 任务
gen_job = Generate(
    pid=1,
    tid=1,
    context_id=1,
    parent_context_id=-1,
    sampling_config=SamplingConfig(
        temperature=0.7,
        top_p=1.0,
        max_gen_length=512,
        stop_token_ids=[2],
    ),
    end_flag=False
)

# 任务执行
# Generate任务逐token生成：
gen_job.put_token(token_id=1024)  # 添加生成的token
gen_job.context.push_token_id(1024)  # 更新上下文
gen_job.gen_length += 1

# 检查停止条件
if gen_job.check_stop():
    gen_job.finish_event.set()  # 标记完成
```

### 3. 约束检查详解

```python
# parrot/engine/scheduler.py:126-144

# 约束1: 批大小
if cur_num_jobs + 1 > self.max_batch_size:
    break  # 无法再添加任务

# 约束2: Batch内Token数
# 注意：Generate每个算1个token，Fill按token_ids长度计算
job_num_tokens = 1 if isinstance(job, Generate) else len(job.token_ids)

if cur_num_batched_tokens + job_num_tokens > self.max_num_batched_tokens:
    break  # 无法容纳更多token

# 约束3: 总Token数（含前缀）
# 关键：前缀共享使用visited_context_ids避免重复计数
job_total_tokens = job.context.get_this_context_len()
if job.context.parent_context and parent_ctx.id not in visited_context_ids:
    job_total_tokens += parent_ctx.get_this_context_len()

if cur_total_tokens + job_total_tokens > self.max_total_tokens:
    break  # 内存超限
```

### 4. 调度策略对比

#### FIFO_V1（标准）
- **位置**：[scheduler.py:80-148](parrot/engine/scheduler.py#L80-L148)
- **特点**：
  - 按到达顺序处理任务
  - 支持前缀共享优化
  - 三重约束（batch_size, batch_tokens, total_tokens）
  - 适合复杂prefill的应用
- **代码**：考虑visited_context_ids

#### TGI
- **位置**：[scheduler.py:151-180](parrot/engine/scheduler.py#L151-L180)
- **特点**：
  - Fill任务优先级高
  - 可抢占Generate任务
  - 适合交互式应用
- **代码**：检查Fill任务，设置preemption

#### 默认FIFO（兼容）
- **位置**：[scheduler.py:182-268](parrot/engine/scheduler.py#L182-L268)
- **特点**：
  - 不考虑前缀共享
  - 按线程和任务到达顺序排序
  - 只用total_token约束

---

## 引擎管理代码

### 1. LLMEngine 接口

#### 位置
[parrot/engine/llm_engine.py](parrot/engine/llm_engine.py)

#### 关键接口

```python
class LLMEngine(ABC):
    """所有引擎的基类"""

    def __init__(self, engine_config: Dict, connect_to_os: bool = True):
        """初始化引擎

        Args:
            engine_config: 引擎配置字典
            connect_to_os: 是否连接到OS（影响心跳和注册）
        """
        ...

    # === Fill操作（Prefill阶段）===
    @abstractmethod
    async def fill(self, payload: Dict) -> Dict:
        """填充KV缓存

        payload包含：
        - context_id: 上下文ID
        - token_ids: token列表
        - text: 输入文本（可选）
        """
        ...

    # === Generate操作（Decode阶段）===
    @abstractmethod
    async def generate(self, payload: Dict) -> Dict:
        """生成输出token

        payload包含：
        - context_id: 上下文ID
        - sampling_config: 采样参数
        """
        ...

    # === 流式生成 ===
    @abstractmethod
    def generate_stream(self, payload: Dict) -> AsyncGenerator:
        """逐token流式输出"""
        ...

    # === 资源释放 ===
    @abstractmethod
    async def free_context(self, payload: Dict) -> Dict:
        """释放上下文占用的KV缓存"""
        ...

    # === 运行时信息 ===
    @abstractmethod
    def get_runtime_info(self, profile: bool) -> EngineRuntimeInfo:
        """获取引擎运行时信息（用于心跳）"""
        ...

    # === 引擎循环 ===
    @abstractmethod
    async def engine_iter(self):
        """每个周期的引擎迭代（处理任务）"""
        ...

    # === 内置实现：注册和通信 ===
    def _register_engine(self, engine_config: EngineConfig):
        """向OS注册此引擎（获取engine_id）"""
        ...

    def heartbeat(self):
        """发送心跳到OS（运行时信息）"""
        ...

    def _heartbeat_daemon(self):
        """心跳守护线程（后台运行）"""
        ...

    async def engine_loop(self):
        """主引擎循环

        - 启动心跳线程
        - 不断调用engine_iter()
        """
        ...
```

### 2. ExecutionEngine（OS级）

#### 位置
[parrot/os/engine.py](parrot/os/engine.py)

#### 关键属性和方法

```python
class ExecutionEngine:
    """OS视图的引擎抽象"""

    def __init__(self,
        engine_id: int,          # OS分配的ID
        config: EngineConfig,    # 引擎配置
        tokenizer: Tokenizer,    # 分词器
    ):
        ...

    # === 基础属性 ===
    @property
    def name(self) -> str:
        return self.config.engine_name

    @property
    def http_address(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"

    @property
    def interpreter_type(self) -> InterpretType:
        # TOKEN_ID (Builtin) 或 TEXT (OpenAI/MLC)
        return INTERPRET_TYPE_MAP[self.config.engine_type]

    # === 容量属性 ===
    @property
    def remain_thread_locs(self) -> int:
        """还能接受多少个线程"""
        return self.config.threads_capacity - self.num_threads

    @property
    def num_threads(self) -> int:
        """当前有多少个线程"""
        return len(self.threads)

    @property
    def requests_num_upperbound(self) -> int:
        """能处理的最大并发任务数"""
        return min([self.config.threads_capacity] +
                   [t.requests_num_upperbound for t in self.threads])

    # === 线程管理 ===
    def accept_thread(self, thread: "Thread"):
        """分配一个线程到此引擎

        - 计算线程的token数量
        - 添加到self.threads
        - 更新self.tokens_num
        """
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
        """计算线程的总token数（用于负载均衡）"""
        # 遍历语义变量AST，统计token数
        ...
```

### 3. 引擎工厂

#### 位置
[parrot/engine/engine_creator.py](parrot/engine/engine_creator.py)

#### 工厂函数

```python
from parrot.engine.engine_creator import create_engine

# 创建引擎
engine = create_engine(
    engine_config_path="config/engine0.json",
    connect_to_os=True,  # 向OS注册并发送心跳
    override_args={"device": "cuda:1"}
)

# 支持的engine_type:
# - "builtin": 自实现的推理引擎
# - "openai": OpenAI API兼容
# - "mlcllm": MLC LLM框架
```

#### 配置文件示例

```json
{
    "engine_name": "engine0",
    "engine_type": "builtin",
    "model": "meta-llama/Llama-2-7b",
    "tokenizer": "meta-llama/Llama-2-7b",
    "host": "127.0.0.1",
    "port": 8000,

    "instance": {
        "num_kv_cache_blocks": 4096,
        "attn_func": "flash_attention",
        "dtype": "float16",
        "device": "cuda",
        "block_size": 1
    },

    "scheduler": {
        "max_batch_size": 256,
        "max_num_batched_tokens": 8192,
        "max_total_tokens": 20480,
        "policy": "fifo_v1"
    },

    "os": {
        "host": "127.0.0.1",
        "port": 8080
    }
}
```

---

## 关键数据结构

### 1. PrimitiveJob 家族

```python
# parrot/engine/primitive_job.py

class PrimitiveJob:
    """所有任务的基类"""
    pid: int                          # 进程ID
    tid: int                          # 线程ID
    context_id: int                   # 上下文唯一ID
    parent_context_id: int            # 父上下文ID（前缀）
    end_flag: bool                    # 是否为最后一个任务
    context: Optional[LowLevelContext]
    finish_event: Event               # 完成标记
    start_time: float                 # 纳秒级时间戳
    end_time: float

class Fill(PrimitiveJob):
    """Prefill阶段任务"""
    token_ids: Optional[List[int]]    # 输入token
    text: Optional[str]               # 输入文本

class Generate(PrimitiveJob):
    """Decode阶段任务"""
    sampling_config: SamplingConfig   # 采样参数
    output_queue: AsyncQueue[int]     # 输出token队列
    gen_text: str
    gen_length: int

    def put_token(self, token_id: int):
        """生成一个token"""
        self.output_queue.put_nowait(token_id)
        self.context.push_token_id(token_id)
        self.gen_length += 1

    def check_stop(self) -> bool:
        """检查是否应停止生成"""
        token_id = self.context.get_last_token_id()
        return (token_id in self.sampling_config.stop_token_ids or
                self.gen_length >= self.sampling_config.max_gen_length)

    async def generator(self):
        """流式生成器"""
        while True:
            token_id = await self.output_queue.get()
            if self.check_stop():
                break
            yield token_id.to_bytes(4, 'big')
```

### 2. EngineConfig & SchedulerConfig

```python
# parrot/engine/config.py

@dataclass
class SchedulerConfig:
    max_batch_size: int                    # 最多任务数
    max_num_batched_tokens: int            # Batch内最多token
    max_total_tokens: int                  # 含前缀的总token上限
    policy: Literal["fifo", "tgi"] = "fifo"

@dataclass
class EngineConfig:
    model: str = "unknown"
    host: str = "127.0.0.1"
    port: int = 8000
    engine_name: str = "unknown"
    engine_type: str = "builtin"  # builtin/openai/mlcllm
    random_seed: int = 0
    tokenizer: str = "unknown"
    dtype: Literal["float16", "float32"] = "float16"
    device: str = "cuda"
    threads_capacity: int = 256            # 最多支持线程数
    tokens_capacity: int = 262144          # 最多缓存token数
```

### 3. SamplingConfig

```python
# parrot/protocol/sampling_config.py

@dataclass
class SamplingConfig:
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int = -1
    max_gen_length: int = 512
    stop_token_ids: List[int] = []
```

### 4. EngineRuntimeInfo

```python
# parrot/protocol/runtime_info.py

@dataclass
class EngineRuntimeInfo:
    num_running_jobs: int = 0
    num_waiting_jobs: int = 0
    num_cached_tokens: int = 0
    cached_tokens_size_bytes: int = 0
    latency_ms: float = 0.0
    throughput_tokens_per_sec: float = 0.0
    utilization_rate: float = 0.0
```

### 5. LowLevelContext

```python
# parrot/engine/context/low_level_context.py

class LowLevelContext:
    context_id: int
    parent_context: Optional[LowLevelContext]  # 前缀树结构
    tokens: List[int] = []

    def get_this_context_len(self) -> int:
        """此上下文独有的token数（不计前缀）"""
        return len(self.tokens)

    def get_context_len(self) -> int:
        """完整上下文长度（计前缀）"""
        length = len(self.tokens)
        if self.parent_context:
            length += self.parent_context.get_context_len()
        return length
```

---

## API速查

### HTTP RPC API

#### 引擎注册

```python
# parrot/protocol/layer_apis.py

from parrot.protocol.layer_apis import register_engine

response = register_engine(
    http_addr="http://127.0.0.1:8080",  # OS地址
    engine_config=EngineConfig(...)
)
# response.engine_id 是OS分配的引擎ID
```

#### 引擎心跳

```python
from parrot.protocol.layer_apis import engine_heartbeat

engine_heartbeat(
    http_addr="http://127.0.0.1:8080",
    engine_id=0,
    engine_name="engine0",
    runtime_info=EngineRuntimeInfo(...)
)
```

#### 引擎Ping

```python
from parrot.protocol.layer_apis import ping_engine

response = ping_engine(
    http_addr="http://127.0.0.1:8000"  # 引擎地址
)
```

### Python API

#### Scheduler API

```python
# parrot/engine/scheduler.py

scheduler = Scheduler(config=SchedulerConfig(...))

# 添加任务
scheduler.add_job(job: PrimitiveJob)

# 调度任务
running_jobs = scheduler.schedule() -> List[PrimitiveJob]

# 完成处理
scheduler.finish()

# 查询
scheduler.num_running_jobs -> int
scheduler.num_total_jobs -> int
scheduler.empty -> bool
```

#### ExecutionEngine API

```python
# parrot/os/engine.py

engine = ExecutionEngine(engine_id, config, tokenizer)

# 分配线程
engine.accept_thread(thread)

# 移除线程
engine.remove_thread(thread)

# 计算线程token数
tokens = engine.count_thread_token_nums(thread) -> int

# 查询
engine.name -> str
engine.http_address -> str
engine.interpreter_type -> InterpretType
engine.num_threads -> int
engine.remain_thread_locs -> int
engine.requests_num_upperbound -> int
```

#### LLMEngine API

```python
# parrot/engine/llm_engine.py

engine = BuiltinEngine(config, connect_to_os=True)

# 任务处理
await engine.fill(payload)
await engine.generate(payload)
engine.generate_stream(payload) -> AsyncGenerator
await engine.free_context(payload)

# 运行时信息
info = engine.get_runtime_info(profile=False)

# 主循环
await engine.engine_loop()

# 引擎迭代（由engine_loop调用）
await engine.engine_iter()
```

---

## 常见问题解答

### Q1: 如何添加新的调度策略？

**A**: 修改 [scheduler.py:77-268](parrot/engine/scheduler.py#L77-L268)

```python
def schedule(self) -> List[PrimitiveJob]:
    if self.policy == "my_new_policy":
        # 实现你的策略
        # 1. 从waiting_jobs中选择任务
        # 2. 检查约束
        # 3. 添加到running_jobs
        # 4. 返回running_jobs.copy()
        ...

    # 继续支持其他策略
    if self.policy == "fifo_v1":
        ...
```

### Q2: 如何创建新的引擎类型？

**A**: 继承 [LLMEngine](parrot/engine/llm_engine.py)

```python
from parrot.engine.llm_engine import LLMEngine

class MyCustomEngine(LLMEngine):
    def __init__(self, engine_config: Dict, connect_to_os: bool = True):
        super().__init__(engine_config, connect_to_os)
        # 初始化你的引擎

    async def fill(self, payload: Dict) -> Dict:
        # 实现fill逻辑
        ...

    async def generate(self, payload: Dict) -> Dict:
        # 实现generate逻辑
        ...

    # 实现其他abstract方法
    ...

# 注册到工厂
# parrot/engine/engine_creator.py:22-59
# 添加 elif engine_type == "my_custom":
#         return MyCustomEngine(engine_config, connect_to_os)
```

### Q3: 如何监控调度器的状态？

**A**: 使用Scheduler的属性

```python
# parrot/engine/scheduler.py:57-75

print(f"Running: {scheduler.num_running_jobs}")
print(f"Total: {scheduler.num_total_jobs}")
print(f"Empty: {scheduler.empty}")

# 或访问队列
print(f"Waiting queue: {scheduler.waiting_jobs}")
print(f"Running queue: {scheduler.running_jobs}")

# 统计信息
print(f"Job arrival times: {scheduler._job_arrival_time}")
print(f"Thread arrival times: {scheduler._thread_arrival_time}")
```

### Q4: 前缀共享如何工作？

**A**: 查看 [scheduler.py:87-102](parrot/engine/scheduler.py#L87-L102)

```python
# 关键：visited_context_ids set
visited_context_ids = set()

for job in self.running_jobs:
    ctx = job.context
    if ctx.context_id not in visited_context_ids:
        # 只有第一次计算此context的大小
        cur_total_tokens += ctx.get_this_context_len()
        visited_context_ids.add(ctx.context_id)

    # 父context也只计算一次
    parent_ctx = ctx.parent_context
    if parent_ctx and parent_ctx.context_id not in visited_context_ids:
        cur_total_tokens += parent_ctx.get_this_context_len()
        visited_context_ids.add(parent_ctx.context_id)
```

### Q5: 如何找到某个engine_id对应的ExecutionEngine？

**A**: 通过PCore

```python
# parrot/os/pcore.py

pcore = PCore(config)
engine = pcore.engines.get(engine_id)  # Dict[int, ExecutionEngine]
```

### Q6: 心跳多久发送一次？

**A**: 在constants.py中定义

```python
# parrot/constants.py

ENGINE_HEARTBEAT_INTERVAL = 1.0  # 秒

# llm_engine.py:146-151
def _heartbeat_daemon(self):
    while True:
        self.heartbeat()
        time.sleep(ENGINE_HEARTBEAT_INTERVAL)
```

### Q7: 如何理解context_id和parent_context_id的关系？

**A**: 它们形成一棵树（前缀树）

```
context_id=1: "Tell me a joke"
  ├─ tokens=[T0, T1, T2, ...]
  └─ parent=None

context_id=2: 基于context_id=1的前缀
  ├─ tokens=[T100, T101, ...]  [新增部分]
  ├─ parent=context_id=1
  └─ 完整内容 = [T0...] + [T100...]

context_id=3: 基于context_id=2的前缀
  ├─ tokens=[T200, T201, ...]
  ├─ parent=context_id=2
  └─ 完整内容 = [T0...] + [T100...] + [T200...]
```

### Q8: Generate任务何时标记为完成？

**A**: 在 [primitive_job.py:105-112](parrot/engine/primitive_job.py#L105-L112)

```python
def check_stop(self) -> bool:
    token_id = self.context.get_last_token_id()
    return (
        token_id in self.sampling_config.stop_token_ids  # 遇到EOS
        or self.gen_length >= self.sampling_config.max_gen_length  # 长度限制
    )

# 当check_stop()返回True时，设置finish_event
job.finish_event.set()

# scheduler.finish()会检测并移除此任务
```

---

## 外部资源

- 📄 论文：`Parrot efficient serving of LLMbased applications with semantic variable.pdf`
- 📘 详细指南：[LEARNING_GUIDE.md](LEARNING_GUIDE.md)
- 🏗️ 架构图：[ARCHITECTURE.md](ARCHITECTURE.md)

