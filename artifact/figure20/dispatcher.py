"""
Request Dispatcher and Router
Manages request routing to LLM instances based on affinity and load
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RoutingStrategy(Enum):
    """Routing strategy types"""
    LOAD_BALANCED = "load_balanced"
    AFFINITY_AWARE = "affinity_aware"
    SESSION_STICKY = "session_sticky"
    INTELLIGENT = "intelligent"


@dataclass
class InstanceStats:
    """Statistics for a vLLM instance"""
    instance_id: str
    queue_length: int = 0
    active_requests: int = 0
    total_requests: int = 0
    total_latency_ms: float = 0.0
    gpu_utilization: float = 0.0
    memory_usage_gb: float = 0.0
    cache_hit_rate: float = 0.0
    last_updated: float = 0.0


class RequestDispatcher:
    """
    Intelligent request dispatcher for multi-agent LLM serving.

    Supports multiple routing strategies:
    1. Load-balanced: Route to least-loaded instance
    2. Affinity-aware: Keep affinity nodes on same instance
    3. Session-sticky: Pin sessions to same instance
    4. Intelligent: Adaptive routing based on agent profile
    """

    def __init__(self, instances: Dict[str, Any]):
        """
        Initialize dispatcher.

        Args:
            instances: Dict of {instance_id: instance_config}
        """
        self.instances = instances
        self.instance_stats: Dict[str, InstanceStats] = {}
        self.session_pinning: Dict[str, str] = {}  # session_id -> instance_id
        self.affinity_groups: Dict[str, List[str]] = {}  # affinity_group_id -> instance_ids

        # Initialize stats for each instance
        for instance_id in instances:
            self.instance_stats[instance_id] = InstanceStats(instance_id=instance_id)

    async def route(self, request: Dict[str, Any], agent_type: str,
                   strategy: RoutingStrategy = RoutingStrategy.INTELLIGENT) -> str:
        """
        Route request to appropriate instance.

        Args:
            request: Request data
            agent_type: Type of agent (coder, rag, multimodal, chatbox)
            strategy: Routing strategy to use

        Returns:
            Instance ID to route to
        """
        if strategy == RoutingStrategy.LOAD_BALANCED:
            return await self._route_load_balanced()

        elif strategy == RoutingStrategy.AFFINITY_AWARE:
            return await self._route_affinity_aware(request, agent_type)

        elif strategy == RoutingStrategy.SESSION_STICKY:
            return await self._route_session_sticky(request)

        elif strategy == RoutingStrategy.INTELLIGENT:
            return await self._route_intelligent(request, agent_type)

        else:
            return await self._route_load_balanced()

    async def _route_load_balanced(self) -> str:
        """
        Route to least-loaded instance.

        Returns:
            Instance ID with minimum queue length
        """
        min_instance = None
        min_queue = float('inf')

        for instance_id, stats in self.instance_stats.items():
            if stats.queue_length < min_queue:
                min_queue = stats.queue_length
                min_instance = instance_id

        return min_instance or list(self.instances.keys())[0]

    async def _route_affinity_aware(self, request: Dict[str, Any],
                                   agent_type: str) -> str:
        """
        Route with affinity awareness.

        For RAG: Keep embedding + reranker + LLM together
        For Coder: Keep workers together

        Returns:
            Instance ID with best affinity
        """
        if agent_type == "rag":
            # RAG: Critical affinity requirement
            # Try to find instance with cached context
            for instance_id, stats in self.instance_stats.items():
                if stats.cache_hit_rate > 0.5:  # Has some cached content
                    return instance_id

            # Otherwise use least-loaded
            return await self._route_load_balanced()

        elif agent_type == "coder":
            # Coder: Prefer throughput-optimized instance for workers
            # Find instance marked as "throughput-optimized"
            for instance_id, config in self.instances.items():
                if "throughput" in config.get("description", "").lower():
                    return instance_id

            return await self._route_load_balanced()

        else:
            return await self._route_load_balanced()

    async def _route_session_sticky(self, request: Dict[str, Any]) -> str:
        """
        Route based on session affinity (chatbox).

        Returns:
            Instance ID for session (pinned if exists, otherwise new)
        """
        session_id = request.get("session_id")

        if session_id and session_id in self.session_pinning:
            # Return pinned instance
            return self.session_pinning[session_id]

        else:
            # Pin new session to least-loaded instance
            instance_id = await self._route_load_balanced()
            if session_id:
                self.session_pinning[session_id] = instance_id
            return instance_id

    async def _route_intelligent(self, request: Dict[str, Any],
                                agent_type: str) -> str:
        """
        Adaptive routing based on agent profile and current load.

        Uses combination of strategies based on agent characteristics.

        Returns:
            Optimally selected instance ID
        """
        if agent_type == "rag":
            # RAG benefits from affinity
            return await self._route_affinity_aware(request, agent_type)

        elif agent_type == "coder":
            # Coder benefits from affinity for workers
            return await self._route_affinity_aware(request, agent_type)

        elif agent_type == "chatbox":
            # Chatbox benefits from session stickiness
            return await self._route_session_sticky(request)

        elif agent_type == "multimodal":
            # Multimodal: flexible, use load balancing
            return await self._route_load_balanced()

        else:
            # Default: load balanced
            return await self._route_load_balanced()

    def update_instance_stats(self, instance_id: str, stats: Dict[str, Any]):
        """Update statistics for an instance"""
        if instance_id in self.instance_stats:
            current = self.instance_stats[instance_id]
            current.queue_length = stats.get("queue_length", current.queue_length)
            current.active_requests = stats.get("active_requests", current.active_requests)
            current.gpu_utilization = stats.get("gpu_utilization", current.gpu_utilization)
            current.memory_usage_gb = stats.get("memory_usage_gb", current.memory_usage_gb)
            current.cache_hit_rate = stats.get("cache_hit_rate", current.cache_hit_rate)
            current.last_updated = time.time()

    def get_instance_stats(self, instance_id: Optional[str] = None) -> Dict[str, InstanceStats] or InstanceStats:
        """Get stats for specific instance or all instances"""
        if instance_id:
            return self.instance_stats.get(instance_id)
        return self.instance_stats

    def get_routing_recommendation(self, agent_type: str) -> Dict[str, Any]:
        """
        Get recommended routing configuration for agent type.

        Returns:
            Dict with recommended strategy and configuration
        """
        recommendations = {
            "coder": {
                "strategy": RoutingStrategy.AFFINITY_AWARE.value,
                "notes": "Workers should be co-located for context sharing",
                "preferred_instance_type": "throughput-optimized"
            },
            "rag": {
                "strategy": RoutingStrategy.AFFINITY_AWARE.value,
                "notes": "Critical affinity: Embedding + Reranker + LLM must be co-located",
                "preferred_instance_type": "balanced"
            },
            "multimodal": {
                "strategy": RoutingStrategy.LOAD_BALANCED.value,
                "notes": "Flexible placement, OCR/ASR can be separate",
                "preferred_instance_type": "any"
            },
            "chatbox": {
                "strategy": RoutingStrategy.SESSION_STICKY.value,
                "notes": "Session pinning enables prefix cache reuse",
                "preferred_instance_type": "latency-optimized"
            }
        }

        return recommendations.get(agent_type, {})

    def get_dispatcher_stats(self) -> Dict[str, Any]:
        """Get overall dispatcher statistics"""
        total_requests = sum(s.total_requests for s in self.instance_stats.values())
        avg_utilization = sum(s.gpu_utilization for s in self.instance_stats.values()) / len(self.instance_stats)

        return {
            "total_instances": len(self.instances),
            "total_requests_routed": total_requests,
            "avg_gpu_utilization": avg_utilization,
            "active_sessions": len(self.session_pinning),
            "instance_stats": {
                iid: {
                    "queue_length": s.queue_length,
                    "active_requests": s.active_requests,
                    "gpu_utilization": s.gpu_utilization,
                    "cache_hit_rate": s.cache_hit_rate
                }
                for iid, s in self.instance_stats.items()
            }
        }
