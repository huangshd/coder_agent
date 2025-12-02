"""
Figure20 Integration with Real vLLM Engines
Aligns with Figure19 setup for mixed workload deployment
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from multiprocessing import Process, Barrier
import json
from pathlib import Path

from agents import CoderAgent, RAGAgent, MultimodalAgent, ChatboxAgent, AgentConfig
from models import EmbeddingModel, RerankerModel, OCRModel, ASRModel
from dispatcher import RequestDispatcher, RoutingStrategy


class Figure20vLLMIntegration:
    """
    Figure20 integration with real vLLM engines.

    Supports:
    - Two vLLM instances (similar to Figure19 setup)
    - Four agentic workflows
    - Heterogeneous workload mixing
    - Performance measurement and comparison
    """

    def __init__(self, vllm_endpoints: List[str], config_dir: str = "./configs"):
        """
        Initialize Figure20 with real vLLM endpoints.

        Args:
            vllm_endpoints: List of vLLM service endpoints
                           e.g., ["http://localhost:8000", "http://localhost:8001"]
            config_dir: Configuration directory path
        """
        self.vllm_endpoints = vllm_endpoints
        self.config_dir = Path(config_dir)

        # Load configuration
        self.agent_config = self._load_json("agent_config.json")

        # Initialize vLLM clients
        self.vllm_clients = self._initialize_vllm_clients()

        # Initialize dispatcher with real endpoints
        self.dispatcher = RequestDispatcher({
            f"instance-{i}": {"endpoint": ep}
            for i, ep in enumerate(vllm_endpoints)
        })

        # Initialize auxiliary models
        self.embedding_model = self._create_embedding_model()
        self.reranker_model = self._create_reranker_model()
        self.ocr_model = self._create_ocr_model()
        self.asr_model = self._create_asr_model()

        # Create agents with real LLM
        self.agents = self._create_agents()

        print("✅ Figure20 with Real vLLM Initialized")
        print(f"   vLLM Endpoints: {len(self.vllm_endpoints)}")
        print(f"   Agents: {len(self.agents)}")
        print(f"   Auxiliary Models: 4 (Embedding, Reranker, OCR, ASR)")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON configuration file"""
        filepath = self.config_dir / filename
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _initialize_vllm_clients(self) -> List[Any]:
        """Initialize vLLM AsyncLLMEngine clients"""
        clients = []
        for endpoint in self.vllm_endpoints:
            # Initialize vLLM client connecting to endpoint
            try:
                from vllm.client import AsyncVLLMClient
                client = AsyncVLLMClient(endpoint)
                clients.append(client)
            except ImportError:
                print("⚠️  vLLM not installed. Using mock client.")
                clients.append(self._create_mock_vllm_client())
        return clients

    def _create_mock_vllm_client(self) -> Any:
        """Create mock vLLM client for testing"""
        class MockVLLMClient:
            async def generate(self, prompt, **kwargs):
                await asyncio.sleep(0.01)
                return "mock response"

        return MockVLLMClient()

    def _create_embedding_model(self) -> Optional[EmbeddingModel]:
        """Create embedding model"""
        try:
            config = self.agent_config.get("auxiliary_models", {}).get("embedding", {})
            return EmbeddingModel(
                model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                device=config.get("device", "cpu")
            )
        except Exception as e:
            print(f"⚠️  Failed to create embedding model: {e}")
            return None

    def _create_reranker_model(self) -> Optional[RerankerModel]:
        """Create reranker model"""
        try:
            config = self.agent_config.get("auxiliary_models", {}).get("reranker", {})
            return RerankerModel(
                model_name=config.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
                device=config.get("device", "cpu")
            )
        except Exception as e:
            print(f"⚠️  Failed to create reranker model: {e}")
            return None

    def _create_ocr_model(self) -> Optional[OCRModel]:
        """Create OCR model"""
        try:
            config = self.agent_config.get("auxiliary_models", {}).get("ocr", {})
            return OCRModel(
                model_type=config.get("model_type", "paddleocr"),
                language=config.get("language", "en"),
                use_gpu=config.get("use_gpu", False)
            )
        except Exception as e:
            print(f"⚠️  Failed to create OCR model: {e}")
            return None

    def _create_asr_model(self) -> Optional[ASRModel]:
        """Create ASR model"""
        try:
            config = self.agent_config.get("auxiliary_models", {}).get("asr", {})
            return ASRModel(
                model_type=config.get("model_type", "whisper"),
                model_size=config.get("model_size", "base"),
                device=config.get("device", "cpu")
            )
        except Exception as e:
            print(f"⚠️  Failed to create ASR model: {e}")
            return None

    def _create_agents(self) -> Dict[str, Any]:
        """Create agents with real vLLM backend"""
        # Create adapter for vLLM
        class vLLMAdapter:
            def __init__(self, clients: List[Any], dispatcher: RequestDispatcher):
                self.clients = clients
                self.dispatcher = dispatcher
                self.client_idx = 0

            async def arun(self, prompt: str, agent_type: str = "default", **kwargs):
                # Route to appropriate vLLM instance
                instance_id = await self.dispatcher.route(
                    {"agent_type": agent_type},
                    agent_type,
                    RoutingStrategy.INTELLIGENT
                )

                # Get client index from instance_id
                idx = int(instance_id.split("-")[-1]) % len(self.clients)
                client = self.clients[idx]

                # Generate response
                try:
                    result = await client.generate(prompt, **kwargs)
                    return result
                except Exception as e:
                    return f"Error: {str(e)}"

        llm_adapter = vLLMAdapter(self.vllm_clients, self.dispatcher)

        agents = {}

        # Coder Agent
        coder_cfg = self.agent_config.get("coder", {})
        agents["coder"] = CoderAgent(
            AgentConfig(
                name="coder_agent",
                llm_model_name=coder_cfg.get("llm_model_name", "vicuna-7b"),
                max_tokens=coder_cfg.get("max_tokens", 2048),
                temperature=coder_cfg.get("temperature", 0.7)
            ),
            llm_adapter
        )

        # RAG Agent
        rag_cfg = self.agent_config.get("rag", {})
        agents["rag"] = RAGAgent(
            AgentConfig(
                name="rag_agent",
                llm_model_name=rag_cfg.get("llm_model_name", "vicuna-7b"),
                max_tokens=rag_cfg.get("max_tokens", 1024),
                temperature=rag_cfg.get("temperature", 0.0)
            ),
            llm_adapter,
            embedding_model=self.embedding_model,
            reranker_model=self.reranker_model
        )

        # Multimodal Agent
        mm_cfg = self.agent_config.get("multimodal", {})
        agents["multimodal"] = MultimodalAgent(
            AgentConfig(
                name="multimodal_agent",
                llm_model_name=mm_cfg.get("llm_model_name", "vicuna-7b"),
                max_tokens=mm_cfg.get("max_tokens", 1536),
                temperature=mm_cfg.get("temperature", 0.5)
            ),
            llm_adapter,
            ocr_model=self.ocr_model,
            asr_model=self.asr_model
        )

        # Chatbox Agent
        chat_cfg = self.agent_config.get("chatbox", {})
        agents["chatbox"] = ChatboxAgent(
            AgentConfig(
                name="chatbox_agent",
                llm_model_name=chat_cfg.get("llm_model_name", "vicuna-7b"),
                max_tokens=chat_cfg.get("max_tokens", 512),
                temperature=chat_cfg.get("temperature", 0.7)
            ),
            llm_adapter
        )

        return agents

    async def benchmark_mixed_workload(self, duration_seconds: int = 60,
                                       workload_mix: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Benchmark mixed workload similar to Figure19.

        Args:
            duration_seconds: Duration of benchmark
            workload_mix: Mix of agent types
                         e.g., {"coder": 0.2, "rag": 0.3, "multimodal": 0.2, "chatbox": 0.3}

        Returns:
            Benchmark results
        """
        if workload_mix is None:
            workload_mix = {
                "coder": 0.15,
                "rag": 0.25,
                "multimodal": 0.15,
                "chatbox": 0.45
            }

        start_time = time.time()
        results = {
            "coder": [],
            "rag": [],
            "multimodal": [],
            "chatbox": []
        }

        request_count = {k: 0 for k in workload_mix.keys()}

        while time.time() - start_time < duration_seconds:
            # Select agent based on workload mix
            import random
            agent_type = random.choices(
                list(workload_mix.keys()),
                weights=list(workload_mix.values())
            )[0]

            request_count[agent_type] += 1

            try:
                if agent_type == "coder":
                    input_data = {"task": "Write a Python function for sorting"}
                elif agent_type == "rag":
                    input_data = {"query": "What is machine learning?", "documents": []}
                elif agent_type == "multimodal":
                    input_data = {"modality": "image", "content": "/tmp/test.jpg", "query": "What is shown?"}
                else:  # chatbox
                    input_data = {"session_id": "test_session", "message": "Hello"}

                output, metrics = await self.agents[agent_type].execute(input_data)
                results[agent_type].append({
                    "latency_ms": metrics.total_latency_ms,
                    "ttft_ms": metrics.ttft_ms,
                    "tpot_ms": metrics.tpot_ms,
                    "success": True
                })
            except Exception as e:
                results[agent_type].append({
                    "error": str(e),
                    "success": False
                })

        # Aggregate results
        summary = {
            "total_duration_seconds": time.time() - start_time,
            "total_requests": sum(request_count.values()),
            "request_counts": request_count,
            "workload_mix": workload_mix,
            "agent_results": {}
        }

        for agent_type, agent_results in results.items():
            successful = [r for r in agent_results if r.get("success")]
            if successful:
                latencies = [r["latency_ms"] for r in successful]
                summary["agent_results"][agent_type] = {
                    "request_count": len(successful),
                    "avg_latency_ms": sum(latencies) / len(latencies),
                    "min_latency_ms": min(latencies),
                    "max_latency_ms": max(latencies),
                    "throughput_req_per_sec": len(successful) / summary["total_duration_seconds"]
                }

        return summary

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "timestamp": time.time(),
            "vllm_endpoints": self.vllm_endpoints,
            "agents": list(self.agents.keys()),
            "dispatcher_stats": self.dispatcher.get_dispatcher_stats()
        }


class Figure20MultiProcessExperiment:
    """
    Multi-process experiment similar to Figure19.
    Runs multiple agent workloads in parallel.
    """

    def __init__(self, vllm_endpoints: List[str], config_dir: str = "./configs"):
        self.vllm_endpoints = vllm_endpoints
        self.config_dir = config_dir

    def run_coder_benchmark(self, barrier: Barrier, num_requests: int = 50, request_rate: float = 1.0):
        """Run Coder agent benchmark in parallel"""
        barrier.wait()

        integration = Figure20vLLMIntegration(self.vllm_endpoints, self.config_dir)

        # Run requests
        async def benchmark():
            results = []
            for i in range(num_requests):
                input_data = {"task": f"Code task {i}"}
                try:
                    output, metrics = await integration.agents["coder"].execute(input_data)
                    results.append({
                        "request_id": i,
                        "latency_ms": metrics.total_latency_ms,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "request_id": i,
                        "error": str(e),
                        "success": False
                    })

                # Rate limiting
                await asyncio.sleep(1.0 / request_rate)

            return results

        results = asyncio.run(benchmark())

        # Save results
        import json
        with open("figure20_coder_results.json", "w") as f:
            json.dump(results, f, indent=2)

    def run_rag_benchmark(self, barrier: Barrier, num_requests: int = 100, request_rate: float = 2.0):
        """Run RAG agent benchmark in parallel"""
        barrier.wait()

        # Give Coder time to start
        time.sleep(10)

        integration = Figure20vLLMIntegration(self.vllm_endpoints, self.config_dir)

        # Run requests
        async def benchmark():
            results = []
            for i in range(num_requests):
                input_data = {
                    "query": f"Question {i}",
                    "documents": [{"content": f"Document {i}"}]
                }
                try:
                    output, metrics = await integration.agents["rag"].execute(input_data)
                    results.append({
                        "request_id": i,
                        "latency_ms": metrics.total_latency_ms,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "request_id": i,
                        "error": str(e),
                        "success": False
                    })

                # Rate limiting
                await asyncio.sleep(1.0 / request_rate)

            return results

        results = asyncio.run(benchmark())

        # Save results
        import json
        with open("figure20_rag_results.json", "w") as f:
            json.dump(results, f, indent=2)

    def run_mixed_benchmark(self, barrier: Barrier, duration_seconds: int = 60):
        """Run mixed workload benchmark"""
        barrier.wait()

        integration = Figure20vLLMIntegration(self.vllm_endpoints, self.config_dir)

        async def benchmark():
            return await integration.benchmark_mixed_workload(duration_seconds)

        results = asyncio.run(benchmark())

        # Save results
        import json
        with open("figure20_mixed_results.json", "w") as f:
            json.dump(results, f, indent=2)


async def main():
    """Main entry point for Figure20 with real vLLM"""
    import argparse

    parser = argparse.ArgumentParser(description="Figure20 with Real vLLM Integration")
    parser.add_argument("--endpoints", type=str, nargs="+",
                       default=["http://localhost:8000", "http://localhost:8001"],
                       help="vLLM service endpoints")
    parser.add_argument("--config-dir", type=str, default="./configs",
                       help="Configuration directory")
    parser.add_argument("--benchmark", choices=["mixed", "coder", "rag", "all"],
                       default="mixed", help="Benchmark type")
    parser.add_argument("--duration", type=int, default=60,
                       help="Benchmark duration in seconds")

    args = parser.parse_args()

    # Initialize system
    integration = Figure20vLLMIntegration(args.endpoints, args.config_dir)

    # Print system status
    print("\n" + "="*60)
    print("FIGURE20 - MIXED AGENT DEPLOYMENT")
    print("="*60)
    print(json.dumps(integration.get_system_status(), indent=2))

    # Run benchmark
    if args.benchmark in ["mixed", "all"]:
        print("\n▶️  Running mixed workload benchmark...")
        results = await integration.benchmark_mixed_workload(args.duration)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
