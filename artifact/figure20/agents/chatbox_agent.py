"""
Chatbox Agent - Conversational AI Workflow
Implements: Session Management → Context Building → LLM Response
"""

import time
from typing import Any, Dict, List, Tuple, Optional
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from .base_agent import BaseAgent, AgentConfig, PerformanceMetrics


class ChatboxAgent(BaseAgent):
    """
    Chatbox Agent: Simple single-turn conversational AI.

    Workflow:
    1. Session Loading: Retrieve conversation history
    2. Context Building: Assemble prompt with history and new message
    3. LLM Generation: Generate single-turn response
    4. Session Update: Store new response in conversation history

    Key characteristics:
    - Simplest workflow (single LLM call per request)
    - High concurrency (50-200 req/min)
    - Low latency (< 2s SLO)
    - Session-based caching: Conversation history as prefix
    - Flexible placement: No affinity requirements
    - High cache hit potential (80%+)
    """

    def __init__(self, config: AgentConfig, llm: BaseLLM,
                 session_store: Optional[Any] = None):
        super().__init__(config)
        self.llm = llm
        self.session_store = session_store or {}
        self.max_history_tokens = 2000

        self.conversation_prompt = PromptTemplate(
            input_variables=["history", "user_input"],
            template="""You are a helpful AI assistant. Continue the conversation naturally.

Conversation History:
{history}

User: {user_input}
Assistant:"""
        )

    async def _execute_workflow(self, input_data: Dict[str, Any],
                               metrics: PerformanceMetrics) -> str:
        """Execute Chatbox workflow: Load Session → Build Context → Generate Response"""
        session_id = input_data.get("session_id", "default")
        user_input = input_data.get("message", "")

        if not user_input:
            raise ValueError("Missing 'message' in input_data")

        start_time = time.time()

        # Phase 1: Session Loading
        conversation_history = self._load_session(session_id)
        metrics.input_tokens = len(conversation_history.split()) + len(user_input.split())

        # Phase 2: Context Building
        metrics.ttft_ms = (time.time() - start_time) * 1000

        # Phase 3: LLM Generation
        llm_start = time.time()
        generation_chain = LLMChain(llm=self.llm, prompt=self.conversation_prompt)
        response = await generation_chain.arun(history=conversation_history, user_input=user_input)
        llm_time = time.time() - llm_start

        # Phase 4: Session Update
        self._update_session(session_id, user_input, response)

        # Update metrics
        metrics.output_tokens = len(response.split())
        metrics.tpot_ms = (llm_time * 1000) / max(metrics.output_tokens, 1)

        return response

    def _load_session(self, session_id: str) -> str:
        """Load conversation history from session store"""
        if session_id not in self.session_store:
            self.session_store[session_id] = []
        
        history_lines = []
        total_tokens = 0
        
        for turn in reversed(self.session_store[session_id]):
            turn_text = f"User: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}"
            turn_tokens = len(turn_text.split())
            
            if total_tokens + turn_tokens > self.max_history_tokens:
                break
            
            history_lines.insert(0, turn_text)
            total_tokens += turn_tokens
        
        return "\n\n".join(history_lines)

    def _update_session(self, session_id: str, user_input: str, response: str):
        """Update session with new turn"""
        if session_id not in self.session_store:
            self.session_store[session_id] = []
        
        self.session_store[session_id].append({
            "user": user_input,
            "assistant": response,
            "timestamp": time.time()
        })

    def get_workflow_nodes(self) -> List[str]:
        """Return workflow node names"""
        return [
            "Session Loading",
            "Context Building",
            "LLM Generation",
            "Session Update"
        ]

    def get_workflow_edges(self) -> List[Tuple[str, str]]:
        """Return workflow edges (strict pipeline)"""
        return [
            ("Session Loading", "Context Building"),
            ("Context Building", "LLM Generation"),
            ("LLM Generation", "Session Update")
        ]

    def get_llm_call_count(self) -> int:
        """Chatbox has 1 LLM call (generation phase)"""
        return 1

    def get_workflow_description(self) -> str:
        return "Chatbox Agent: Session Loading → Context Building → LLM Generation → Update"

    def set_max_history_tokens(self, num: int):
        """Set maximum conversation history tokens"""
        self.max_history_tokens = num

    def clear_session(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.session_store:
            del self.session_store[session_id]

    def clear_all_sessions(self):
        """Clear all sessions"""
        self.session_store.clear()

    def has_affinity_requirement(self) -> bool:
        """Chatbox has NO affinity requirements"""
        return False

    def supports_session_affinity(self) -> bool:
        """Chatbox benefits from session-sticky routing"""
        return True
