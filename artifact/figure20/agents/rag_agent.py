"""
RAG Agent - Retrieval-Augmented Generation Workflow
Implements: Embedding → Retrieval → Reranker → LLM Generation
"""

import time
from typing import Any, Dict, List, Tuple, Optional
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from .base_agent import BaseAgent, AgentConfig, PerformanceMetrics


class RAGAgent(BaseAgent):
    """
    RAG Agent: Retrieves documents and generates answers using LLM.

    Workflow:
    1. Embedding: Convert query to embedding vector
    2. Retrieval: Search vector DB for top-K documents
    3. Reranking: Score documents by relevance
    4. Context Assembly: Build context from top documents
    5. LLM Generation: Generate answer using LLM

    Key characteristics:
    - Pipeline-dependent (strict sequential order)
    - Single LLM call (generation phase only)
    - Strong affinity: Embedding + Reranker + LLM should be co-located
    - High cache potential: Context often repeated across requests
    - Long context input (2000-8000 tokens)
    """

    def __init__(self, config: AgentConfig, llm: BaseLLM,
                 embedding_model: Optional[Any] = None,
                 reranker_model: Optional[Any] = None,
                 vector_db: Optional[Any] = None):
        super().__init__(config)
        self.llm = llm
        self.embedding_model = embedding_model
        self.reranker_model = reranker_model
        self.vector_db = vector_db
        self.top_k = 5  # Top K documents to retrieve

        # Generation prompt template
        self.generation_prompt = PromptTemplate(
            input_variables=["context", "query"],
            template="""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""
        )

    async def _execute_workflow(self, input_data: Dict[str, Any],
                               metrics: PerformanceMetrics) -> str:
        """Execute RAG workflow: Embedding → Retrieval → Reranker → LLM"""
        query = input_data.get("query", "")
        documents = input_data.get("documents", [])

        if not query:
            raise ValueError("Missing 'query' in input_data")

        start_time = time.time()
        metrics.input_tokens = len(query.split())

        # Phase 1: Embedding
        query_embedding = None
        if self.embedding_model:
            query_embedding = self.embedding_model.encode(query)

        # Phase 2: Retrieval from vector DB or use provided documents
        retrieved_docs = documents[:self.top_k] if documents else []

        # Phase 3: Reranking (optional)
        if self.reranker_model and retrieved_docs:
            # Score documents
            scores = []
            for doc in retrieved_docs:
                doc_text = doc.get("content", "") if isinstance(doc, dict) else str(doc)
                score = self.reranker_model.score(query, doc_text)
                scores.append(score)

            # Sort by score
            sorted_docs = sorted(zip(retrieved_docs, scores), key=lambda x: x[1], reverse=True)
            retrieved_docs = [doc for doc, _ in sorted_docs[:self.top_k]]

        # Phase 4: Context Assembly
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            if isinstance(doc, dict):
                content = doc.get("content", "")
                title = doc.get("title", f"Document {i}")
                context_parts.append(f"[{title}]\n{content}")
            else:
                context_parts.append(str(doc))

        context = "\n\n".join(context_parts)
        metrics.ttft_ms = (time.time() - start_time) * 1000

        # Phase 5: LLM Generation
        llm_start = time.time()
        generation_chain = LLMChain(llm=self.llm, prompt=self.generation_prompt)
        answer = await generation_chain.arun(context=context, query=query)
        llm_time = time.time() - llm_start

        # Update metrics
        metrics.output_tokens = len(answer.split())
        metrics.tpot_ms = (llm_time * 1000) / max(metrics.output_tokens, 1)

        return answer

    def get_workflow_nodes(self) -> List[str]:
        """Return workflow node names"""
        nodes = ["Embedding", "Retrieval", "Reranking", "Context Assembly", "LLM Generation"]
        return nodes

    def get_workflow_edges(self) -> List[Tuple[str, str]]:
        """Return workflow edges (strict pipeline)"""
        return [
            ("Embedding", "Retrieval"),
            ("Retrieval", "Reranking"),
            ("Reranking", "Context Assembly"),
            ("Context Assembly", "LLM Generation")
        ]

    def get_llm_call_count(self) -> int:
        """RAG has only 1 LLM call (in generation phase)"""
        return 1

    def get_workflow_description(self) -> str:
        return (f"RAG Agent: Embedding → Retrieval (top {self.top_k}) → "
                f"Reranking → Context Assembly → LLM Generation")

    def set_top_k(self, k: int):
        """Set number of documents to retrieve"""
        self.top_k = k

    def has_affinity_requirement(self) -> bool:
        """
        Check if affinity placement is required.
        RAG has CRITICAL affinity: Embedding + Reranker + LLM should be co-located.
        """
        return True

    def get_affinity_groups(self) -> List[List[str]]:
        """Return groups of nodes that should be co-located"""
        return [
            ["Embedding", "Reranking", "LLM Generation"]
        ]
