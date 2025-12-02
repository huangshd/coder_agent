# Figure20: Four Agentic Workflows - Complete Documentation Index

## 📖 Start Here

**New to Figure20?** Start with: [README.md](./README.md)

**Want to understand the design?** Read: [ARCHITECTURE.md](./ARCHITECTURE.md)

**Ready to implement?** Follow: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)

**Curious about the research plan?** See: [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md)

---

## 📑 Complete Documentation Map

### Core System Documentation

| Document | Purpose | Read If... | Duration |
|----------|---------|-----------|----------|
| **[README.md](./README.md)** | Quick overview & getting started | You're new to figure20 | 10 min |
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | System design & trade-offs | You want to understand design decisions | 20 min |
| **[DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)** | Complete implementation roadmap | You're implementing the system | 30 min |
| **[DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md)** | Completed work & next phases | You want overview + timeline | 15 min |

### Agent & Workflow Documentation

| Document | Purpose | Key Content | Read If... |
|----------|---------|-------------|-----------|
| **[docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md)** | Detailed agent characteristics | DAGs, LLM calls, cache needs, SLOs | You need to understand agents deeply |
| **[docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md)** | LLM placement optimization | Configurations, placement algorithms, auxiliary model placement | You're designing placement strategy |
| **[docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md)** | Request routing policies | Per-agent routing, contention handling, adaptation | You're implementing request dispatcher |

---

## 🎯 By Stakeholder Role

### For Software Engineers (Implementation)

**Phase 1 - Agent Implementation**:
1. Read: [README.md](./README.md) (quick overview)
2. Read: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) (Phase 1 section)
3. Reference: [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) (workflow details)
4. Implement: Follow DEVELOPMENT_GUIDE.md code templates

**Phase 2 - Auxiliary Models**:
1. Read: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) (Phase 2 section)
2. Reference: [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) (model requirements)
3. Implement: Following templates

**Phase 3 - Benchmarking**:
1. Read: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) (Phase 3 section)
2. Reference: [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) (performance targets)
3. Implement: Benchmark scripts

**Phase 4 - System Integration**:
1. Read: [ARCHITECTURE.md](./ARCHITECTURE.md) (system overview)
2. Read: [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md) (instance setup)
3. Read: [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md) (routing setup)
4. Implement: Launch scripts, dispatcher

### For Researchers (Experimentation)

**Understand the Problem**:
1. Read: [README.md](./README.md) (overview)
2. Read: [ARCHITECTURE.md](./ARCHITECTURE.md) (system design)
3. Read: [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) (agent characteristics)

**Design Experiments**:
1. Read: [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md) (placement options)
2. Read: [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md) (routing options)
3. Reference: [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md) (Phase 5)

**Conduct Experiments**:
1. Follow Phase 5 roadmap in [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md)
2. Use benchmarks from Phase 3
3. Measure metrics specified in [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md)

**Report Findings**:
1. Update [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) with empirical data
2. Update [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md) with validation
3. Update [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md) with results

### For System Architects

**Understand Design**:
1. Read: [ARCHITECTURE.md](./ARCHITECTURE.md)
2. Read: [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md) (configurations A, B, C)
3. Read: [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md) (routing policies)

**Make Decisions**:
1. Review Configuration A, B, C options
2. Consider trade-offs in [ARCHITECTURE.md](./ARCHITECTURE.md) section 7
3. Decide on implementation approach

### For Project Managers

**Plan Timeline**:
1. Read: [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md) (phases & timeline)
2. Reference: Phase breakdown (effort estimates, dependencies)
3. Plan resource allocation

**Track Progress**:
1. Follow checklist in [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md)
2. Monitor Phase completion
3. Adjust timeline based on learnings

---

## 🔍 Documentation by Topic

### Agent Workflows
- **Coder Agent**: [AGENT_PROFILES.md § 1](./docs/AGENT_PROFILES.md#1-coder-agent-profile)
- **RAG Agent**: [AGENT_PROFILES.md § 2](./docs/AGENT_PROFILES.md#2-rag-agent-profile)
- **Multimodal Agent**: [AGENT_PROFILES.md § 3](./docs/AGENT_PROFILES.md#3-multimodal-agi-agent-profile)
- **Chatbox Agent**: [AGENT_PROFILES.md § 4](./docs/AGENT_PROFILES.md#4-chatbox-agent-profile)

### System Architecture
- **High-level architecture**: [ARCHITECTURE.md § 1](./ARCHITECTURE.md#1-high-level-architecture)
- **Component design**: [ARCHITECTURE.md § 2](./ARCHITECTURE.md#2-component-design-decisions)
- **Data flow patterns**: [ARCHITECTURE.md § 3](./ARCHITECTURE.md#3-data-flow--execution-patterns)
- **Performance optimizations**: [ARCHITECTURE.md § 4](./ARCHITECTURE.md#4-performance-optimization-strategies)
- **Configuration management**: [ARCHITECTURE.md § 5](./ARCHITECTURE.md#5-configuration-management)

### Placement & Scheduling
- **Problem formulation**: [PLACEMENT_STRATEGY.md § 1](./docs/PLACEMENT_STRATEGY.md#1-problem-formulation)
- **ILP formulation**: [PLACEMENT_STRATEGY.md § 2](./docs/PLACEMENT_STRATEGY.md#2-placement-strategy-sia-inspired-ilp-formulation)
- **Configuration options**: [PLACEMENT_STRATEGY.md § 3](./docs/PLACEMENT_STRATEGY.md#3-recommended-placement-configurations)
- **Routing policies**: [PLACEMENT_STRATEGY.md § 4 & SCHEDULING_STRATEGY.md § 3](./docs/PLACEMENT_STRATEGY.md#4-routing-policies-request-dispatcher)
- **Contention handling**: [SCHEDULING_STRATEGY.md § 4](./docs/SCHEDULING_STRATEGY.md#4-contention-handling-strategies)
- **Adaptive scheduling**: [SCHEDULING_STRATEGY.md § 5](./docs/SCHEDULING_STRATEGY.md#5-performance-monitoring--adaptation)

### Implementation Details
- **Phase 1 (Agents)**: [DEVELOPMENT_GUIDE.md § 2](./DEVELOPMENT_GUIDE.md#phase-1-agent-implementation-current-focus)
- **Phase 2 (Models)**: [DEVELOPMENT_GUIDE.md § 3](./DEVELOPMENT_GUIDE.md#phase-2-auxiliary-models-integration)
- **Phase 3 (Benchmarks)**: [DEVELOPMENT_GUIDE.md § 4](./DEVELOPMENT_GUIDE.md#phase-3-benchmark-implementation)
- **Phase 4 (Setup)**: [DEVELOPMENT_GUIDE.md § 5](./DEVELOPMENT_GUIDE.md#phase-5-launch-scripts)
- **Phase 5 (Experiments)**: [DOCUMENTATION_SUMMARY.md § Phase 5](./DOCUMENTATION_SUMMARY.md#phase-5-experimentation--optimization-3-4-weeks)

---

## 📊 Quick Reference Tables

### Agent Characteristics Summary

| Aspect | Coder | RAG | Multimodal | Chatbox |
|--------|-------|-----|-----------|---------|
| **Complexity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **LLM Calls** | 10-25 | 1 | 1 | 1 |
| **Parallelism** | Workers (N) | None | OCR/ASR (parallel) | None |
| **Affinity Needs** | Medium | 🔴 Critical | Weak | Session-sticky |
| **Cache Potential** | Medium | Very High | Medium | Very High |
| **Throughput** | 5-20 req/min | 20-100 req/min | 5-30 req/min | 50-200 req/min |
| **SLO** | <30s | <5s | <10s | <2s |

[Full comparison →](./docs/AGENT_PROFILES.md#5-comparative-summary)

### Placement Configurations

| Configuration | Instances | Specialization | GPU 6-7 | Best For |
|---------------|-----------|-----------------|---------|----------|
| **A (Balanced)** ✅ | 4 | Medium | Auxiliary models | Recommended |
| **B (Specialized)** | 4 | High | Multimodal overflow | Perfect affinity |
| **C (Minimal)** | 3 | Low | Auxiliary only | Cost-sensitive |

[Detailed comparison →](./docs/PLACEMENT_STRATEGY.md#3-recommended-placement-configurations)

### Routing Policies

| Agent | Strategy | Key Features | Benefits |
|-------|----------|--------------|----------|
| **Coder** | Affinity-aware + specialization | Planner→latency, Workers→throughput, Checker→flexible | Worker cache, TTFT optimization |
| **RAG** | Strict affinity enforcement | Embedding+Reranker+LLM co-located | Minimal network latency, high cache hits |
| **Multimodal** | Modality-specific + LLM selection | OCR/ASR separate, LLM load-balanced | GPU efficiency, parallelizable preprocessing |
| **Chatbox** | Session-sticky load balancing | Route user sessions to same instance | Conversation history caching |

[Detailed algorithms →](./docs/SCHEDULING_STRATEGY.md#3-per-agent-routing-policies)

---

## 🚀 Quick Start Paths

### Path 1: I Want to Understand the System (30 minutes)

1. Read [README.md](./README.md) (10 min)
2. Read [ARCHITECTURE.md](./ARCHITECTURE.md) (20 min)

**Result**: Understand system design, four agents, key decisions

### Path 2: I Want to Implement It (2-3 hours)

1. Read [README.md](./README.md) (10 min)
2. Read [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) Phase 1 (30 min)
3. Read [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) § 1-2 (60 min)
4. Start coding base_agent.py (follow templates)

**Result**: Ready to implement Phase 1

### Path 3: I Want to Run Experiments (1-2 hours)

1. Read [README.md](./README.md) (10 min)
2. Read [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md) (45 min)
3. Read [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md) (30 min)
4. Read [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md) (15 min)

**Result**: Understand experiment design (ready for Phase 5)

### Path 4: I Want to Deploy It (3-4 hours)

1. Read [README.md](./README.md) (10 min)
2. Read [ARCHITECTURE.md](./ARCHITECTURE.md) (20 min)
3. Read [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md) (60 min)
4. Read [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md) (60 min)
5. Review configuration options in [PLACEMENT_STRATEGY.md § 3](./docs/PLACEMENT_STRATEGY.md#3-recommended-placement-configurations)

**Result**: Ready to configure and deploy

---

## 📚 Documentation Statistics

```
Total Documentation:
├── Core Files: 4 (README, ARCHITECTURE, DEVELOPMENT_GUIDE, DOCUMENTATION_SUMMARY)
├── Specialized Files: 3 (AGENT_PROFILES, PLACEMENT_STRATEGY, SCHEDULING_STRATEGY)
├── Index File: 1 (this file)
│
├── Total Words: ~27,000
├── Code Examples: 20+
├── Diagrams & Tables: 40+
├── Implementation Phases: 6
│
└── Coverage:
    ✅ System architecture & design
    ✅ 4 agent profiles with detailed characteristics
    ✅ 3 placement strategy options
    ✅ 4 routing algorithms
    ✅ Complete implementation guide
    ✅ Experimental plan & timeline
    ✅ Reproducibility instructions
```

---

## 🔗 Key Cross-References

### Design Decisions
- [Why separate agents?](./ARCHITECTURE.md#212-agent-layer) → ARCHITECTURE.md
- [Why multiple instances?](./ARCHITECTURE.md#24-vllm-instance-management) → ARCHITECTURE.md
- [Why affinity enforcement?](./docs/AGENT_PROFILES.md#27-affinity-requirements) → AGENT_PROFILES.md
- [Why session stickiness?](./docs/SCHEDULING_STRATEGY.md#34-chatbox-agent-routing) → SCHEDULING_STRATEGY.md

### Implementation Details
- [How to implement Coder agent?](./DEVELOPMENT_GUIDE.md#12-coder-agent-implementation) → DEVELOPMENT_GUIDE.md
- [How to integrate OCR?](./DEVELOPMENT_GUIDE.md#23-ocr-model-modelsocr_modelpy) → DEVELOPMENT_GUIDE.md
- [How to route requests?](./docs/SCHEDULING_STRATEGY.md) → SCHEDULING_STRATEGY.md
- [What config to use?](./docs/PLACEMENT_STRATEGY.md#6-configuration-selection-for-figure20) → PLACEMENT_STRATEGY.md

### Research & Measurement
- [What metrics matter?](./docs/AGENT_PROFILES.md) → AGENT_PROFILES.md
- [What experiments to run?](./DOCUMENTATION_SUMMARY.md#phase-5-experimentation--optimization-3-4-weeks) → DOCUMENTATION_SUMMARY.md
- [How to measure cache hits?](./SCHEDULING_STRATEGY.md#51-metrics-collection) → SCHEDULING_STRATEGY.md
- [How to compare placements?](./docs/PLACEMENT_STRATEGY.md#7-placement-iteration--refinement) → PLACEMENT_STRATEGY.md

---

## 🔄 Documentation Maintenance

This documentation is **living documentation** that should be updated as:

1. **Implementation reveals issues** (update DEVELOPMENT_GUIDE.md)
2. **Experiments produce empirical data** (update AGENT_PROFILES.md)
3. **Placement strategies prove suboptimal** (update PLACEMENT_STRATEGY.md)
4. **Routing policies need adjustment** (update SCHEDULING_STRATEGY.md)
5. **New phases are discovered** (update DOCUMENTATION_SUMMARY.md)

---

## 📞 Navigation Help

### I'm Looking For...

- **Quick overview** → [README.md](./README.md)
- **System design** → [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Agent details** → [docs/AGENT_PROFILES.md](./docs/AGENT_PROFILES.md)
- **Placement strategy** → [docs/PLACEMENT_STRATEGY.md](./docs/PLACEMENT_STRATEGY.md)
- **Routing policies** → [docs/SCHEDULING_STRATEGY.md](./docs/SCHEDULING_STRATEGY.md)
- **Implementation steps** → [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
- **Timeline & phases** → [DOCUMENTATION_SUMMARY.md](./DOCUMENTATION_SUMMARY.md)
- **Code examples** → [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) (Python templates)
- **Configuration template** → [docs/PLACEMENT_STRATEGY.md § 6](./docs/PLACEMENT_STRATEGY.md#6-configuration-selection-for-figure20)

---

## ✨ Status

**Documentation Phase**: ✅ COMPLETE

**Created**: 2025-12-01
**Status**: Ready for implementation phases
**Next**: Phase 1 - Base Agent Implementation

---

## 📖 How to Use This Index

1. **Find your role** (engineer, researcher, architect, manager)
2. **Follow the recommended reading path**
3. **Reference specific sections** as needed during work
4. **Update documentation** when you discover new information
5. **Share findings** to improve future iterations

---

**Happy researching and building! 🚀**
