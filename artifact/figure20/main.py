#!/usr/bin/env python3
"""
Figure20 Multi-Agent System - Main Entry Point
Demonstrates the four agentic workflows with vLLM + LangChain
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from agents import (
    CoderAgent, RAGAgent, MultimodalAgent, ChatboxAgent,
    AgentConfig, PerformanceMetrics
)
from models import EmbeddingModel, RerankerModel, OCRModel, ASRModel
from dispatcher import RequestDispatcher, RoutingStrategy


class Figure20System:
    """
    Figure20 Multi-Agent LLM Serving System
    """

    def __init__(self, config_dir: str = "./configs"):
        """
        Initialize Figure20 system.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.vllm_config = self._load_json("vllm_config.json")
        self.agent_config = self._load_json("agent_config.json")
        self.benchmark_config = self._load_json("benchmark_config.json")

        # Initialize dispatcher
        self.dispatcher = RequestDispatcher(
            {inst["instance_id"]: inst for inst in self.vllm_config["vllm_instances"]}
        )

        # Initialize auxiliary models
        self.embedding_model = self._create_embedding_model()
        self.reranker_model = self._create_reranker_model()
        self.ocr_model = self._create_ocr_model()
        self.asr_model = self._create_asr_model()

        # Initialize agents (with mock LLM for now)
        self.agents = self._create_agents()

        print(" Figure20 System Initialized")
        print(f"   Agents: {len(self.agents)}")
        print(f"   LLM Instances: {len(self.vllm_config['vllm_instances'])}")
        print(f"   Auxiliary Models: 4 (Embedding, Reranker, OCR, ASR)")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON configuration file"""
        filepath = self.config_dir / filename
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"  Config file not found: {filepath}")
            return {}

    def _create_embedding_model(self) -> Optional[EmbeddingModel]:
        """Create embedding model"""
        try:
            config = self.agent_config.get("auxiliary_models", {}).get("embedding", {})
            return EmbeddingModel(
                model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                device=config.get("device", "cpu")
            )
        except Exception as e:
            print(f"  Failed to create embedding model: {e}")
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
            print(f"  Failed to create reranker model: {e}")
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
            print(f"  Failed to create OCR model: {e}")
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
            print(f"  Failed to create ASR model: {e}")
            return None

    def _create_agents(self) -> Dict[str, Any]:
        """Create all four agents"""
        # Mock LLM for demonstration
        class MockLLM:
            async def arun(self, **kwargs):
                await asyncio.sleep(0.01)
                return "Mock response from LLM"

        agents = {}

        # Coder Agent
        coder_cfg = self.agent_config.get("coder", {})
        agents["coder"] = CoderAgent(
            AgentConfig(
                name="coder_agent",
                llm_model_name=coder_cfg.get("llm_model_name", "mock"),
                max_tokens=coder_cfg.get("max_tokens", 2048),
                temperature=coder_cfg.get("temperature", 0.7)
            ),
            MockLLM()
        )

        # RAG Agent
        rag_cfg = self.agent_config.get("rag", {})
        agents["rag"] = RAGAgent(
            AgentConfig(
                name="rag_agent",
                llm_model_name=rag_cfg.get("llm_model_name", "mock"),
                max_tokens=rag_cfg.get("max_tokens", 1024),
                temperature=rag_cfg.get("temperature", 0.0)
            ),
            MockLLM(),
            embedding_model=self.embedding_model,
            reranker_model=self.reranker_model
        )

        # Multimodal Agent
        mm_cfg = self.agent_config.get("multimodal", {})
        agents["multimodal"] = MultimodalAgent(
            AgentConfig(
                name="multimodal_agent",
                llm_model_name=mm_cfg.get("llm_model_name", "mock"),
                max_tokens=mm_cfg.get("max_tokens", 1536),
                temperature=mm_cfg.get("temperature", 0.5)
            ),
            MockLLM(),
            ocr_model=self.ocr_model,
            asr_model=self.asr_model
        )

        # Chatbox Agent
        chat_cfg = self.agent_config.get("chatbox", {})
        agents["chatbox"] = ChatboxAgent(
            AgentConfig(
                name="chatbox_agent",
                llm_model_name=chat_cfg.get("llm_model_name", "mock"),
                max_tokens=chat_cfg.get("max_tokens", 512),
                temperature=chat_cfg.get("temperature", 0.7)
            ),
            MockLLM()
        )

        return agents

    async def run_agent_demo(self, agent_type: str) -> Dict[str, Any]:
        """
        Run demo for specific agent type.

        Args:
            agent_type: Type of agent (coder, rag, multimodal, chatbox)

        Returns:
            Execution results
        """
        if agent_type not in self.agents:
            return {"error": f"Unknown agent type: {agent_type}"}

        agent = self.agents[agent_type]

        # Prepare demo input based on agent type
        if agent_type == "coder":
            input_data = {
                "task": "Write a Python function to calculate the Fibonacci sequence"
            }

        elif agent_type == "rag":
            input_data = {
                "query": "What is machine learning?",
                "documents": [
                    {"title": "ML Basics", "content": "Machine learning is a subset of AI that enables systems to learn from data."},
                    {"title": "ML Algorithms", "content": "Common ML algorithms include neural networks, decision trees, and support vector machines."},
                ]
            }

        elif agent_type == "multimodal":
            input_data = {
                "modality": "image",
                "content": "/path/to/sample/image.jpg",
                "query": "What is shown in this image?"
            }

        elif agent_type == "chatbox":
            input_data = {
                "session_id": "demo_session_001",
                "message": "Hello, how are you?"
            }

        else:
            return {"error": f"Unsupported agent type: {agent_type}"}

        # Route request
        instance_id = await self.dispatcher.route(input_data, agent_type, RoutingStrategy.INTELLIGENT)

        # Execute agent
        try:
            output, metrics = await agent.execute(input_data)
            return {
                "success": True,
                "agent_type": agent_type,
                "instance_routed": instance_id,
                "output": output[:100] + "..." if len(output) > 100 else output,
                "metrics": {
                    "latency_ms": metrics.total_latency_ms,
                    "ttft_ms": metrics.ttft_ms,
                    "tpot_ms": metrics.tpot_ms,
                    "input_tokens": metrics.input_tokens,
                    "output_tokens": metrics.output_tokens
                },
                "workflow": agent.get_workflow_dag()
            }
        except Exception as e:
            return {
                "success": False,
                "agent_type": agent_type,
                "error": str(e)
            }

    async def run_all_demos(self) -> Dict[str, Any]:
        """Run demo for all four agents"""
        results = {}
        for agent_type in ["coder", "rag", "multimodal", "chatbox"]:
            print(f"\n  Running {agent_type.upper()} agent demo...")
            result = await self.run_agent_demo(agent_type)
            results[agent_type] = result

            if result.get("success"):
                print(f"    Success")
                print(f"    Latency: {result['metrics']['latency_ms']:.2f}ms")
                print(f"    Instance: {result['instance_routed']}")
            else:
                print(f"    Error: {result.get('error')}")

        return results

    def print_system_info(self):
        """Print system information"""
        print("\n" + "="*60)
        print("FIGURE20 - FOUR AGENTIC WORKFLOWS")
        print("="*60)

        print("\n📋 SYSTEM CONFIGURATION")
        print("-" * 60)

        # VLLMs
        print(f"\n  vLLM Instances: {len(self.vllm_config['vllm_instances'])}")
        for inst in self.vllm_config["vllm_instances"]:
            print(f"   • {inst['instance_id']}: GPU {inst['gpu_ids']} - {inst['description']}")

        # Agents
        print(f"\n Agents: {len(self.agents)}")
        for agent_type, agent in self.agents.items():
            dag = agent.get_workflow_dag()
            print(f"   • {agent_type.upper()}")
            print(f"     - Nodes: {len(dag['nodes'])}")
            print(f"     - LLM calls: {dag['llm_calls']}")
            print(f"     - Description: {dag['description']}")

        # Auxiliary Models
        print(f"\n Auxiliary Models")
        print(f"   • Embedding: {self.embedding_model is not None}")
        print(f"   • Reranker: {self.reranker_model is not None}")
        print(f"   • OCR: {self.ocr_model is not None}")
        print(f"   • ASR: {self.asr_model is not None}")

        # Dispatcher
        print(f"\n Request Dispatcher")
        print(f"   • Strategy: Intelligent (adaptive)")
        print(f"   • Routing modes: Load-balanced, Affinity-aware, Session-sticky")

        # Routing recommendations
        print(f"\n Routing Recommendations")
        for agent_type in ["coder", "rag", "multimodal", "chatbox"]:
            rec = self.dispatcher.get_routing_recommendation(agent_type)
            if rec:
                print(f"   • {agent_type.upper()}: {rec.get('strategy', 'N/A')}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Figure20",
            "agents": list(self.agents.keys()),
            "vllm_instances": len(self.vllm_config["vllm_instances"]),
            "auxiliary_models": 4,
            "dispatcher_stats": self.dispatcher.get_dispatcher_stats()
        }


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Figure20 Multi-Agent System")
    parser.add_argument("--demo", choices=["coder", "rag", "multimodal", "chatbox", "all"],
                       default="all", help="Run specific agent demo")
    parser.add_argument("--config-dir", default="./configs", help="Configuration directory")
    parser.add_argument("--info", action="store_true", help="Print system information")

    args = parser.parse_args()

    # Initialize system
    system = Figure20System(config_dir=args.config_dir)

    # Print system info
    system.print_system_info()

    if args.info:
        print(json.dumps(system.get_system_status(), indent=2))
        return

    # Run demos
    if args.demo == "all":
        results = await system.run_all_demos()
    else:
        results = {args.demo: await system.run_agent_demo(args.demo)}

    # Print results
    print("\n" + "="*60)
    print("DEMO RESULTS")
    print("="*60)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
