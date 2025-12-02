# Parrot 系统架构可视化与代码关系图

## 1. 高层系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                     Client Application                              │
│              (使用SemanticVariable编写的应用)                       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │ MyApp                                                   │       │
│  │  ├─ function_call_1: context_id=1                      │       │
│  │  │   └─ Fill → Generate → Generate → ...               │       │
│  │  ├─ function_call_2: context_id=2 (prefix=context_id=1)│       │
│  │  │   └─ Fill → Generate → ...                          │       │
│  │  └─ function_call_3: context_id=3 (prefix=context_id=2)│       │
│  │      └─ Generate → ...                                 │       │
│  └──────────────────────────────────────────────────────────┘       │
│                            │                                        │
│                HTTP RPC /submit_request                             │
│                            │                                        │
└────────────────────────────┼────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                     Parrot OS Server                                │
│                    (parrot/os/pcore.py)                            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │ PCore                                                   │       │
│  │                                                          │       │
│  │ ├─ Process Manager: pid=1,2,3...                       │       │
│  │ │                                                       │       │
│  │ ├─ Thread Management                                  │       │
│  │ │  ├─ Thread(pid=1, tid=1, call=call_1)              │       │
│  │ │  │  └─ engine: Engine0                              │       │
│  │ │  │     tokens_per_thread: 1024                      │       │
│  │ │  │                                                   │       │
│  │ │  ├─ Thread(pid=1, tid=2, call=call_2)              │       │
│  │ │  │  └─ engine: Engine0 or Engine1?                  │       │
│  │ │  │                                                   │       │
│  │ │  └─ Thread(pid=2, tid=1, call=call_3)              │       │
│  │ │     └─ engine: Engine1                              │       │
│  │ │                                                       │       │
│  │ ├─ ThreadDispatcher                                   │       │
│  │ │  └─ 负责选择合适的引擎分配线程                      │       │
│  │ │     基于: token_count, latency, load                │       │
│  │ │                                                       │       │
│  │ ├─ MemorySpace                                        │       │
│  │ │  └─ 全局共享内存管理                                │       │
│  │ │                                                       │       │
│  │ ├─ Executor                                           │       │
│  │ │  └─ TokenIdInterpreter: 将SemanticVariable转换     │       │
│  │ │     为token序列                                     │       │
│  │ │                                                       │       │
│  │ ├─ Tokenizer                                          │       │
│  │ │  └─ 文本 <-> token_ids 转换                        │       │
│  │ │                                                       │       │
│  │ └─ Runtime Monitoring                                │       │
│  │    ├─ proc_last_seen_time: pid -> timestamp          │       │
│  │    └─ engine_last_seen_time: engine_id -> timestamp  │       │
│  │                                                       │       │
│  └──────────────────────────────────────────────────────────┘       │
│                            │                                        │
│   HTTP RPC (fill, generate, free_context, get_runtime_info)       │
│                            │                                        │
└────────────────────────────┼────────────────────────────────────────┘
                │            │            │
     ┌──────────┼────────────┼────────────┼──────────┐
     │          │            │            │          │
     ▼          ▼            ▼            ▼          ▼
  Engine0    Engine1      Engine2      Engine3    Engine...
 (Builtin)  (OpenAI)     (MLC LLM)    (Builtin)
```

---

## 2. 引擎层架构

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│                    Engine Process (e.g., Engine0)             │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ LLMEngine (abc)                                         │ │
│  │ - engine_id: int                                        │ │
│  │ - engine_config: EngineConfig                           │ │
│  │ - os_http_address: str                                  │ │
│  │                                                         │ │
│  │ Methods:                                                │ │
│  │ ├─ abstract fill(payload)                              │ │
│  │ ├─ abstract generate(payload)                          │ │
│  │ ├─ abstract generate_stream(payload)                   │ │
│  │ ├─ abstract free_context(payload)                      │ │
│  │ ├─ abstract get_runtime_info(profile)                  │ │
│  │ ├─ abstract engine_iter()                              │ │
│  │ │                                                       │ │
│  │ ├─ _register_engine() → HTTP to OS                    │ │
│  │ │  └─ OS returns: engine_id                           │ │
│  │ │                                                       │ │
│  │ ├─ heartbeat() → HTTP to OS (every 1s)               │ │
│  │ │  └─ sends: EngineRuntimeInfo                        │ │
│  │ │                                                       │ │
│  │ ├─ engine_loop()                                       │ │
│  │ │  ├─ start _heartbeat_daemon()                        │ │
│  │ │  └─ while True:                                      │ │
│  │ │      └─ await engine_iter()                          │ │
│  │ │                                                       │ │
│  │ └─ _heartbeat_daemon() [Thread]                        │ │
│  │    └─ while True: heartbeat(); sleep(1s)              │ │
│  └─────────────────────────────────────────────────────────┘ │
│           ▲          ▲          ▲                            │
│           │          │          │                            │
│    ┌──────┴──┐ ┌──────┴──┐ ┌──────┴──┐                       │
│    │          │          │          │                        │
│    ▼          ▼          ▼          ▼                        │
│  ┌────────┐┌────────┐┌────────┐┌────────┐                  │
│  │Builtin││ OpenAI │ │ MLC    ││ Custom │                  │
│  │Engine ││ Engine │ │Engine  ││ Engine │                  │
│  │        ││        │ │        ││        │                  │
│  │ - has ││ - calls││ - uses  ││ - user││                  │
│  │  own  ││ OpenAI││  MLC    ││defined││                  │
│  │  impl ││  API  │ │  lib   ││impl   │                  │
│  │        ││        │ │        ││        │                  │
│  │ - with ││ - no ││ - cross-││        │                  │
│  │ Scheduler││need││  platform││        │                  │
│  │ - with ││  local││        ││        │                  │
│  │ custom ││  GPU││        ││        │                  │
│  │ kernels│└────────┘└────────┘└────────┘                  │
│  │        │                                                  │
│  └────────┘                                                  │
│      │                                                       │
│      └─── ┌───────────────────────────────────┐             │
│           │ Builtin 引擎的特定组件            │             │
│           │                                   │             │
│           ├─ Scheduler                        │             │
│           │  ├─ policy: "fifo_v1", "tgi"    │             │
│           │  ├─ max_batch_size               │             │
│           │  ├─ max_num_batched_tokens       │             │
│           │  ├─ max_total_tokens             │             │
│           │  ├─ waiting_jobs: [PrimitiveJob] │             │
│           │  ├─ running_jobs: [PrimitiveJob] │             │
│           │  │                               │             │
│           │  └─ schedule() -> [Jobs]         │             │
│           │     └─ 约束检查 & 任务选择      │             │
│           │                                   │             │
│           ├─ Runner                          │             │
│           │  └─ execute(jobs)                │             │
│           │                                   │             │
│           ├─ Model                           │             │
│           │  ├─ forward(tokens)              │             │
│           │  └─ KV缓存管理                  │             │
│           │                                   │             │
│           └─ Kernels                         │             │
│              ├─ flash_attention              │             │
│              ├─ rotary_embedding             │             │
│              ├─ rmsnorm                      │             │
│              └─ other optimized kernels      │             │
│                                               │             │
│           └───────────────────────────────────┘             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. 调度器详细流程

```
Task Lifecycle in Scheduler:

┌────────────────────────────────────────────────────────────────┐
│                     初始状态                                    │
│  waiting_jobs: [ ]    running_jobs: [ ]                        │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       │ 新任务从应用到达
                       ▼
┌────────────────────────────────────────────────────────────────┐
│              scheduler.add_job(job)                            │
│                                                                │
│  waiting_jobs: [job]                                          │
│  running_jobs: [ ]                                            │
│                                                                │
│  记录统计：                                                   │
│  _job_arrival_time[job.context_id] = now                     │
│  _thread_arrival_time[pid_tid] = now                         │
└──────────────────────────────────────────────────────────────┘
                       │
                       │ scheduler.schedule() 被调用
                       ▼
┌────────────────────────────────────────────────────────────────┐
│              FIFO_V1 调度策略                                 │
│                                                                │
│  初始化约束：                                                 │
│  cur_num_jobs = len(running_jobs)         [当前任务数]       │
│  cur_num_batched_tokens = len(running)    [当前batch token]   │
│  cur_total_tokens = sum(context_len)      [总token含前缀]    │
│                                                                │
│  visited_context_ids = set()              [防重复计数]       │
│                                                                │
│  while waiting_jobs 不为空:                                   │
│    job = waiting_jobs[0]  [取最老的任务]                      │
│                                                                │
│    ┌─ 计算任务的资源需求                                     │
│    │  job_num_tokens = 1 if Generate else len(token_ids)     │
│    │  job_total_tokens = job.context.get_this_context_len()  │
│    │                                                           │
│    │  [如果父上下文未计数过，加上父上下文大小]               │
│    │                                                           │
│    ├─ 约束检查 (Decision Tree)                               │
│    │                                                           │
│    │  Is (cur_num_jobs + 1) > max_batch_size?                │
│    │    ├─ YES: break [无法继续添加任务]                     │
│    │    └─ NO: 继续检查下一个约束                            │
│    │                                                           │
│    │  Is (cur_num_batched_tokens + job_num_tokens)            │
│    │      > max_num_batched_tokens?                           │
│    │    ├─ YES: break [token超限]                            │
│    │    └─ NO: 继续检查下一个约束                            │
│    │                                                           │
│    │  Is (cur_total_tokens + job_total_tokens)                │
│    │      > max_total_tokens?                                 │
│    │    ├─ YES: break [总内存超限]                           │
│    │    └─ NO: 可以调度此任务                                │
│    │                                                           │
│    └─ 调度任务                                               │
│       running_jobs.append(job)                               │
│       job.start_time = now                                   │
│       waiting_jobs.pop(0)                                    │
│                                                               │
│       更新约束：                                              │
│       cur_num_jobs += 1                                      │
│       cur_num_batched_tokens += job_num_tokens               │
│       cur_total_tokens += job_total_tokens                   │
│                                                               │
│  return running_jobs.copy()  [返回本轮要执行的任务]         │
└────────────────────────────────────────────────────────────────┘
                       │
                       │ 引擎执行这些任务
                       ▼
┌────────────────────────────────────────────────────────────────┐
│            Engine Runner.execute(jobs)                         │
│                                                                │
│  for job in jobs:                                             │
│    if isinstance(job, Fill):                                  │
│      - 预处理tokens                                          │
│      - 计算attention: q@k^t                                   │
│      - 写入KV缓存                                            │
│      - job.context.push_tokens(...)                           │
│                                                               │
│    elif isinstance(job, Generate):                            │
│      - 读取KV缓存                                            │
│      - 计算logits                                            │
│      - 采样token_id                                          │
│      - job.put_token(token_id)  [放入输出队列]               │
│      - job.context.push_token_id(token_id)  [更新上下文]    │
│                                                               │
│      if job.check_stop():                                     │
│        job.finish_event.set()                                │
│                                                               │
└────────────────────────────────────────────────────────────────┘
                       │
                       │ scheduler.finish() 被调用
                       ▼
┌────────────────────────────────────────────────────────────────┐
│              处理已完成的任务                                  │
│                                                                │
│  new_running = []                                             │
│                                                                │
│  for job in running_jobs:                                     │
│    if job.finish_event.is_set():                              │
│      [任务已完成]                                            │
│      remove_job(job)  [清除统计数据]                         │
│      job.end_time = now                                       │
│      latency = job.end_time - job.start_time                  │
│      logger.debug(f"Job {job} finished. Latency: {latency}")  │
│    else:                                                       │
│      [任务继续运行]                                          │
│      new_running.append(job)                                  │
│                                                               │
│  running_jobs = new_running                                   │
│                                                               │
└────────────────────────────────────────────────────────────────┘
                       │
                       │ 下一个周期循环
                       ▼
┌────────────────────────────────────────────────────────────────┐
│   waiting_jobs 中有新的任务，循环回到 schedule()              │
│                                                                │
│   waiting_jobs: [job2, job3, ...]                             │
│   running_jobs: [job1_still_generating, ...]                  │
│                                                                │
│   → schedule() 重新调度                                       │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. 前缀共享示例

```
语义变量树结构与token共享：

AppCall_1: "Tell me a joke"
┌────────────────────────────────────┐
│ context_id = 1                     │
│ tokens = [T0, T1, T2, ...]         │
│ memory = <KV_Cache_1>              │
│                                    │
│ Fill(context_id=1)                 │
│   → 处理tokens → 写入KV_1          │
│                                    │
│ Generate(context_id=1)             │
│   → 读KV_1 → 生成token             │
│                                    │
│ Result: "Why did the..."           │
└────────────────────────────────────┘
         │
         │ 使用此结果作为前缀
         │
AppCall_2: 继续接龙
┌────────────────────────────────────────────────────────┐
│ context_id = 2                                         │
│ parent_context_id = 1                                  │
│ tokens = [T100, T101, ...]  [新增的token]             │
│                                                        │
│ 内存布局：                                            │
│  [KV_1: 旧token的KV] ← [KV_2_delta: 新token的KV]  │
│   (由parent指向，不重复)    (此context独有)          │
│                                                        │
│ get_this_context_len() = len([T100, T101, ...])       │
│ get_context_len() = len([T0,...,T100,T101,...])       │
│                                                        │
│ Fill(context_id=2, parent=context_id=1)               │
│   → 从KV_1读旧KV                                     │
│   → 处理新token [T100, T101, ...]                    │
│   → 增量写入KV_2_delta                              │
│                                                        │
│ Generate(context_id=2)                                │
│   → 读 KV_1 + KV_2_delta                            │
│   → 生成token                                        │
│                                                        │
│ Result: "chicken egg"                                 │
└────────────────────────────────────────────────────────┘
         │
         │ 再次使用前缀
         │
AppCall_3: "Did you get it?"
┌──────────────────────────────────────────────────────────────┐
│ context_id = 3                                               │
│ parent_context_id = 2                                        │
│ tokens = [T200, T201, ...]  [第三次的新token]               │
│                                                               │
│ 内存布局：                                                   │
│ [KV_1] ← [KV_2_delta] ← [KV_3_delta]                        │
│                                                               │
│ 调度时的Token计数（FIFO_V1）：                              │
│                                                               │
│ cur_total_tokens = 0                                        │
│ visited_context_ids = set()                                 │
│                                                               │
│ for running_job in running_jobs:  [假设有Task_1, Task_2]  │
│   ctx_1 = Task_1.context  (context_id=1)                   │
│   if 1 not in visited:                                      │
│     cur_total_tokens += ctx_1.get_this_context_len()  [200]│
│     visited.add(1)                                          │
│                                                               │
│   ctx_2 = Task_2.context  (context_id=2)                   │
│   if 2 not in visited:                                      │
│     cur_total_tokens += ctx_2.get_this_context_len()  [100]│
│     visited.add(2)                                          │
│                                                               │
│ # 总计：只计200+100，而不是200+300+400                      │
│ # 这就是前缀共享的效果！                                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘


Scheduler约束示例（假设内存限制为512 tokens）：

running_jobs:
  Task_1: Generate(context_id=1)
  Task_2: Generate(context_id=2)
  → cur_total_tokens = 200 + 100 = 300 (已使用)

waiting_jobs:
  Task_3: Generate(context_id=3)
  → 需要token = 300 + 200 = 500

约束检查：
  cur_total_tokens + task_total_tokens = 300 + 500 = 800
  > max_total_tokens (512) ?  YES
  → break, 无法调度Task_3
  → Task_3 被抢占

这时如果有Fill任务到达（TGI策略）：
  Fill(context_id=4, tokens=[...], len=50)
  → 可以抢占Task_1, Task_2
  → 运行新的Fill任务
```

---

## 5. 引擎分配流程

```
Thread Dispatch Flow:

┌─────────────────────────────────────────────────────────┐
│ OS收到线程分配请求                                      │
│ Thread(pid=1, tid=1, call=semantic_call, tokens=1024)  │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ ThreadDispatcher.dispatch(thread)                       │
│                                                         │
│ ├─ 选择引擎策略：                                      │
│ │  ├─ shortest_queue: min(engine.tokens_num)          │
│ │  ├─ least_latency: min(engine.latency)              │
│ │  └─ load_balance: min(utilization_rate)             │
│ │                                                      │
│ ├─ 候选引擎集合：                                      │
│ │  engines_candidates = []                            │
│ │  for engine in all_engines:                         │
│ │    if engine.remain_thread_locs > 0:                │
│ │       if engine.tokens_num + thread.tokens < cap:   │
│ │         engines_candidates.append(engine)           │
│ │                                                      │
│ ├─ 选择最优引擎：                                      │
│ │  best_engine = select_strategy(engines_candidates)  │
│ │                                                      │
│ └─ 分配线程：                                          │
│    best_engine.accept_thread(thread)                  │
│                                                        │
└─────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ ExecutionEngine.accept_thread(thread)                   │
│                                                         │
│ ├─ thread.engine = self                               │
│ │                                                      │
│ ├─ thread_tokens = count_thread_token_nums(thread)    │
│ │  └─ 遍历语义变量的AST，统计token数                 │
│ │                                                      │
│ ├─ self.threads.append(thread)                        │
│ ├─ self.threads_len[thread.uid] = thread_tokens       │
│ ├─ self.tokens_num += thread_tokens                   │
│ │                                                      │
│ └─ 更新运行时信息：                                    │
│    self.runtime_info.num_threads = len(self.threads)  │
│    self.runtime_info.total_tokens = self.tokens_num   │
│                                                        │
└─────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ Executor.submit(thread)                                │
│                                                         │
│ ├─ 确定解释器类型：                                    │
│ │  interpret_type = thread.engine.interpreter_type    │
│ │                                                      │
│ ├─ 选择解释器：                                        │
│ │  if interpret_type == TOKEN_ID:                     │
│ │    interpreter = TokenIdInterpreter(...)            │
│ │  else:  # TEXT                                      │
│ │    interpreter = TextInterpreter()                  │
│ │                                                      │
│ ├─ 解释线程：                                          │
│ │  interpreter.interpret(thread)                      │
│ │  └─ 将语义变量转换为操作序列                       │
│ │     Fill(context_id=..., tokens=[...])              │
│ │     Generate(context_id=..., config=...)            │
│ │     ...                                              │
│ │                                                      │
│ └─ 启动线程执行：                                      │
│    create_task_in_loop(thread.executing())            │
│    └─ 触发异步任务执行线程逻辑                        │
│                                                        │
└─────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│ Thread.executing()  [在引擎内执行]                      │
│                                                         │
│ for operator in thread.operators:                      │
│   ├─ if operator == Fill:                             │
│   │   scheduler.add_job(Fill(...))                    │
│   │                                                    │
│   ├─ elif operator == Generate:                       │
│   │   scheduler.add_job(Generate(...))                │
│   │                                                    │
│   └─ elif operator == Free:                           │
│       engine.free_context(...)                        │
│                                                        │
│ 引擎的 schedule() / finish() / engine_iter()          │
│ 不断处理这些操作，驱动执行                            │
│                                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 代码文件依赖关系图

```
parrot/
│
├── program/                    [语义变量程序层]
│   ├── semantic_variable.py    [核心：SemanticVariable]
│   ├── function.py             [SemanticCall, NativeCall]
│   ├── function_call.py
│   ├── vm.py                   [虚拟机执行]
│   └── transforms/             [优化变换]
│       ├── prompt_compressor.py
│       ├── conversation_template.py
│       └── ...
│
├── protocol/                   [通信协议层]
│   ├── layer_apis.py           [register_engine, engine_heartbeat]
│   ├── runtime_info.py         [EngineRuntimeInfo, VMRuntimeInfo]
│   ├── sampling_config.py      [SamplingConfig]
│   └── primitive_request.py
│
├── engine/                     [引擎层]
│   ├── llm_engine.py           [LLMEngine基类]
│   │   ├── fill()
│   │   ├── generate()
│   │   ├── heartbeat()
│   │   └── engine_loop()
│   │
│   ├── scheduler.py            [Scheduler调度器] ⭐
│   │   ├── add_job()
│   │   ├── schedule()           [3种策略：FIFO_V1, TGI, default]
│   │   └── finish()
│   │
│   ├── primitive_job.py        [PrimitiveJob基类] ⭐
│   │   ├── PrimitiveJob
│   │   ├── Fill (prefill)
│   │   └── Generate (decode)
│   │
│   ├── config.py               [EngineConfig, SchedulerConfig]
│   │
│   ├── engine_creator.py       [create_engine() 工厂函数]
│   │
│   ├── builtin/                [内置引擎实现]
│   │   ├── builtin_engine.py   [BuiltinEngine extends LLMEngine]
│   │   ├── builtin_runner.py   [推理执行]
│   │   ├── model_instantiation.py
│   │   │
│   │   ├── models/
│   │   │   ├── llama.py
│   │   │   ├── opt.py
│   │   │   └── sampler.py
│   │   │
│   │   ├── kernels/            [优化kernel]
│   │   │   ├── flash_attention_with_context.py
│   │   │   ├── rotary_embedding.py
│   │   │   └── ...
│   │   │
│   │   └── mem.py, mem_layout.py  [内存管理]
│   │
│   ├── context/                [上下文管理]
│   │   ├── low_level_context.py [LowLevelContext]
│   │   ├── context_manager.py
│   │   └── text_context.py
│   │
│   ├── openai/                 [OpenAI兼容引擎]
│   │   ├── openai_engine.py
│   │   └── api_endpoint.py
│   │
│   └── mlc_llm/                [MLC LLM引擎]
│       └── mlc_engine.py
│
├── os/                         [操作系统层] ⭐⭐
│   ├── engine.py               [ExecutionEngine] ⭐
│   │   ├── accept_thread()
│   │   ├── remove_thread()
│   │   └── count_thread_token_nums()
│   │
│   ├── pcore.py                [PCore - OS核心]
│   │   ├── processes
│   │   ├── engines
│   │   ├── dispatcher
│   │   └── tokenizer
│   │
│   ├── thread_dispatcher.py    [ThreadDispatcher - 线程分配]
│   │   └── dispatch(thread)
│   │
│   ├── tokenizer.py            [Tokenizer - 分词]
│   │
│   ├── memory/
│   │   └── mem_space.py         [MemorySpace - 全局内存]
│   │
│   └── process/                [进程/线程执行]
│       ├── process.py
│       ├── thread.py            [Thread - 执行单元]
│       ├── executor.py          [Executor - 线程执行器]
│       │   └── submit(thread)
│       ├── interpreter.py       [TokenIdInterpreter, TextInterpreter]
│       ├── interpret_type.py    [InterpretType: TOKEN_ID / TEXT]
│       ├── primitive_operator.py [操作序列]
│       ├── dag_edge.py
│       └── placeholder.py
│
├── constants.py                [全局常量]
│
├── exceptions.py               [自定义异常]
│
└── utils/
    ├── logging.py
    ├── misc.py
    └── ...


核心依赖关系：

LLMEngine ◀── BuiltinEngine
                  ↓
              Scheduler
                  ↓
          PrimitiveJob (Fill, Generate)
                  ↓
          LowLevelContext


ExecutionEngine ◀── PCore
    ↓                 ↓
  ThreadDispatcher  Executor
    ↓                 ↓
  dispatch()   ──→  submit()
    ↓
  Thread
    ↓
(分配给Engine)
```

---

## 7. 与论文的对应关系

```
Parrot论文 (OSDI'24)
│
├─ 语义变量（Semantic Variable）
│  └─ parrot/program/semantic_variable.py
│
├─ 前缀共享（Prefix Sharing）
│  ├─ parrot/engine/scheduler.py [FIFO_V1策略]
│  │  └─ visited_context_ids, get_this_context_len()
│  └─ parrot/engine/context/low_level_context.py
│     └─ parent_context, tree structure
│
├─ 分布式调度（Distributed Scheduling）
│  ├─ parrot/os/pcore.py [全局协调]
│  ├─ parrot/os/thread_dispatcher.py [线程分配]
│  └─ parrot/engine/scheduler.py [局部任务调度]
│
└─ 智能体编程支持（Agent Programming）
   ├─ parrot/program/function.py [SemanticCall]
   ├─ parrot/protocol/layer_apis.py [RPC通信]
   └─ 实现多个函数调用的编排和优化
```

---

## 8. 关键概念映射表

| 论文概念 | 代码实现 | 文件位置 |
|---------|---------|--------|
| Semantic Variable | SemanticVariable类 | program/semantic_variable.py |
| Program | SemanticCall序列 | program/function.py |
| Task | PrimitiveJob (Fill/Generate) | engine/primitive_job.py |
| Scheduler | Scheduler类 | engine/scheduler.py |
| Engine Instance | ExecutionEngine | os/engine.py |
| OS/Runtime | PCore | os/pcore.py |
| Thread | Thread类 | os/process/thread.py |
| Dispatch Strategy | ThreadDispatcher | os/thread_dispatcher.py |
| Prefix Tree | parent_context树 | engine/context/low_level_context.py |

---

## 9. 学习导航路由

```
入门 (1-2天)
  ↓
  1. 阅读 LEARNING_GUIDE.md 的"系统总体架构"
  2. 理解 Fill 和 Generate 的概念
  3. 查看本文件的"高层系统架构"图

理解调度 (2-3天)
  ↓
  1. 深入学习 "调度器详细流程"
  2. 分析 scheduler.py 的 schedule() 方法
  3. 理解 "前缀共享示例"

理解引擎管理 (3-4天)
  ↓
  1. 学习 "引擎层架构"
  2. 理解 LLMEngine 和 ExecutionEngine 的关系
  3. 跟踪 create_engine() 函数

分布式协调 (4-5天)
  ↓
  1. 学习 "引擎分配流程"
  2. 研究 PCore 和 ThreadDispatcher
  3. 理解心跳和监控机制

实战应用 (5+天)
  ↓
  1. 修改调度策略
  2. 添加自定义引擎
  3. 优化性能
```

