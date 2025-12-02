"""
Multimodal AGI Agent - Image/Audio/Video Understanding Workflow
Implements: Input Recognition → OCR/ASR → Text Fusion → LLM Understanding
"""

import asyncio
import time
from typing import Any, Dict, List, Tuple, Optional
from langchain.llms.base import BaseLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from .base_agent import BaseAgent, AgentConfig, PerformanceMetrics


class MultimodalAgent(BaseAgent):
    """
    Multimodal AGI Agent: Processes images, audio, and videos for understanding.

    Workflow:
    1. Input Recognition: Detect modality (image/audio/video)
    2. Preprocessing:
       - Image → OCR → text extraction
       - Audio → ASR → speech-to-text
       - Video → Frame extraction → OCR
    3. Text Fusion: Merge results from preprocessing
    4. LLM Understanding: Multimodal reasoning
    5. Output Generation: Natural language response

    Key characteristics:
    - Heterogeneous models (OCR/ASR + LLM)
    - Modality-dependent branching
    - Parallel preprocessing (OCR/ASR can run concurrently)
    - Long multimodal context (2000-10000 tokens)
    - I/O intensive (loading multimedia)
    - Weak affinity: OCR/ASR can run on separate hardware
    """

    def __init__(self, config: AgentConfig, llm: BaseLLM,
                 ocr_model: Optional[Any] = None,
                 asr_model: Optional[Any] = None):
        super().__init__(config)
        self.llm = llm
        self.ocr_model = ocr_model
        self.asr_model = asr_model
        self.max_frames_per_video = 5  # Sample frames from video

        # Understanding prompt template
        self.understanding_prompt = PromptTemplate(
            input_variables=["modality", "extracted_text", "query"],
            template="""You are a multimodal AI assistant. Analyze the following {modality} content
and answer the question.

Extracted Content:
{extracted_text}

Question: {query}

Answer:"""
        )

    async def _execute_workflow(self, input_data: Dict[str, Any],
                               metrics: PerformanceMetrics) -> str:
        """Execute Multimodal workflow: Input Recognition → OCR/ASR → Fusion → LLM"""
        modality = input_data.get("modality", "").lower()
        content = input_data.get("content")  # File path or data
        query = input_data.get("query", "")

        if not modality or not content:
            raise ValueError("Missing 'modality' or 'content' in input_data")

        if modality not in ["image", "audio", "video"]:
            raise ValueError(f"Unsupported modality: {modality}")

        start_time = time.time()
        metrics.input_tokens = len(query.split())

        # Phase 1-2: Modality-dependent preprocessing
        extracted_text = ""

        if modality == "image":
            extracted_text = await self._process_image(content)

        elif modality == "audio":
            extracted_text = await self._process_audio(content)

        elif modality == "video":
            extracted_text = await self._process_video(content)

        metrics.ttft_ms = (time.time() - start_time) * 1000

        # Phase 3: Text Fusion (already done in preprocessing)
        # Phase 4-5: LLM Understanding

        llm_start = time.time()
        understanding_chain = LLMChain(
            llm=self.llm,
            prompt=self.understanding_prompt
        )
        answer = await understanding_chain.arun(
            modality=modality,
            extracted_text=extracted_text,
            query=query
        )
        llm_time = time.time() - llm_start

        # Update metrics
        metrics.output_tokens = len(answer.split())
        metrics.tpot_ms = (llm_time * 1000) / max(metrics.output_tokens, 1)

        return answer

    async def _process_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        if not self.ocr_model:
            return f"[Image content from: {image_path}]"

        try:
            # Simulate OCR processing
            extracted_text = self.ocr_model.extract_text(image_path)
            return extracted_text
        except Exception as e:
            return f"[OCR Error: {str(e)}]"

    async def _process_audio(self, audio_path: str) -> str:
        """Convert audio to text using ASR"""
        if not self.asr_model:
            return f"[Audio content from: {audio_path}]"

        try:
            # Simulate ASR processing
            transcribed_text = self.asr_model.transcribe(audio_path)
            return transcribed_text
        except Exception as e:
            return f"[ASR Error: {str(e)}]"

    async def _process_video(self, video_path: str) -> str:
        """Extract frames from video and apply OCR"""
        if not self.ocr_model:
            return f"[Video content from: {video_path}]"

        try:
            # Simulate frame extraction and OCR
            frames_text = []
            for frame_id in range(self.max_frames_per_video):
                # In reality, would extract actual frames
                frame_text = self.ocr_model.extract_text(f"{video_path}#frame_{frame_id}")
                frames_text.append(f"[Frame {frame_id}]\n{frame_text}")

            return "\n---\n".join(frames_text)
        except Exception as e:
            return f"[Video Processing Error: {str(e)}]"

    def get_workflow_nodes(self) -> List[str]:
        """Return workflow node names"""
        return [
            "Input Recognition",
            "OCR/ASR Preprocessing",
            "Text Fusion",
            "LLM Understanding",
            "Output Generation"
        ]

    def get_workflow_edges(self) -> List[Tuple[str, str]]:
        """Return workflow edges (branching structure)"""
        return [
            ("Input Recognition", "OCR/ASR Preprocessing"),
            ("OCR/ASR Preprocessing", "Text Fusion"),
            ("Text Fusion", "LLM Understanding"),
            ("LLM Understanding", "Output Generation")
        ]

    def get_llm_call_count(self) -> int:
        """Multimodal has 1 main LLM call (understanding phase)"""
        return 1

    def get_workflow_description(self) -> str:
        return (f"Multimodal Agent: Input Recognition → OCR/ASR "
                f"(up to {self.max_frames_per_video} frames for video) → "
                f"Text Fusion → LLM Understanding")

    def set_max_frames_per_video(self, num: int):
        """Set number of frames to sample from video"""
        self.max_frames_per_video = num

    def has_weak_affinity(self) -> bool:
        """
        Multimodal has WEAK affinity:
        OCR/ASR can run on separate hardware from LLM
        """
        return True

    def get_affinity_recommendation(self) -> Dict[str, str]:
        """Return affinity recommendations"""
        return {
            "OCR/ASR": "Separate GPU or CPU (can be specialized hardware)",
            "LLM": "Dedicated GPU for inference"
        }
