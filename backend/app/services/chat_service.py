import time
import json
from typing import AsyncGenerator, Dict, Any, List, Optional
from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.answer_validation_service import AnswerValidationService
from app.services.chat_analytics_service import ChatAnalyticsService

class ChatService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        conversation_service: ConversationService,
        memory_service: MemoryService,
        prompt_builder: PromptBuilderService,
        validation_service: AnswerValidationService,
        analytics_service: ChatAnalyticsService
    ):
        self.retrieval_svc = retrieval_service
        self.conv_svc = conversation_service
        self.memory_svc = memory_service
        self.prompt_svc = prompt_builder
        self.val_svc = validation_service
        self.analytics_svc = analytics_service

    def _get_openai_client(self) -> AsyncOpenAI:
        """
        Dynamically initializes the AsyncOpenAI client based on provider settings.
        Supports OpenRouter, vLLM, and Ollama.
        """
        provider = settings.LLM_PROVIDER.lower()
        logger.info(f"ChatService loading OpenAI client for provider: {provider}")
        
        if provider == "openrouter":
            return AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY or settings.LLM_API_KEY,
                default_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Construction Document Intelligence"
                }
            )
        elif provider == "vllm":
            return AsyncOpenAI(
                base_url=settings.LLM_API_BASE,
                api_key=settings.LLM_API_KEY or "vllm-token"
            )
        else:  # Default to Ollama local API base
            return AsyncOpenAI(
                base_url=settings.LLM_API_BASE,
                api_key="ollama"
            )

    async def stream_chat(
        self,
        query: str,
        session_id: str,
        project_id: str,
        max_tokens: Optional[int] = 12000
    ) -> AsyncGenerator[str, None]:
        """
        Executes the full RAG pipeline, streaming back markdown tokens followed by metadata JSON payloads.
        """
        t_total_start = time.time()
        
        # 1. Fetch pruned chat history from MemoryService
        history = self.memory_svc.get_pruned_history(session_id)
        
        # 2. Retrieve document context chunks
        t_ret_start = time.time()
        retrieval_res = self.retrieval_svc.retrieve(
            query=query,
            project_id=project_id,
            max_tokens=max_tokens
        )
        t_ret_ms = (time.time() - t_ret_start) * 1000
        
        context_package = retrieval_res["context_package"]
        confidence_summary = context_package["confidence_summary"]
        citations = context_package["citations"]
        
        # 3. Scaffold prompts payload
        t_prompt_start = time.time()
        system_prompt, messages_payload = self.prompt_svc.build_prompt(
            context_package=context_package,
            question=query,
            history=history
        )
        t_prompt_ms = (time.time() - t_prompt_start) * 1000
        
        # 4. Initiate stream request to configured LLM
        client = self._get_openai_client()
        t_gen_start = time.time()
        full_content = ""
        
        try:
            logger.info(f"Requesting completions stream for model: {settings.LLM_MODEL}")
            stream = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages_payload,
                stream=True,
                temperature=0.2,
                max_tokens=1000
            )
            
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    full_content += token
                    yield json.dumps({"token": token})
                    
        except Exception as stream_err:
            logger.error(f"Completions stream error: {stream_err}")
            yield json.dumps({"error": f"LLM streaming failure: {str(stream_err)}"})
            return
            
        t_gen_ms = (time.time() - t_gen_start) * 1000
        
        # 5. Run AnswerValidationService
        validated_content = self.val_svc.validate_answer(
            answer=full_content,
            context_package=context_package,
            confidence_summary=confidence_summary
        )
        
        # If validation updated the response text (to the fallback message), push it to user
        validation_failed = (validated_content != full_content)
        if validation_failed:
            logger.warning("Answer validation failed, yielding fallback message override.")
            yield json.dumps({"validated_content": validated_content})
            
        # Determine overall answer confidence summary status
        answer_confidence = "High"
        if validation_failed:
            answer_confidence = "Low (Validation Failed)"
        elif confidence_summary == "Low":
            answer_confidence = "Low (Low Retrieval Confidence)"
            
        # 6. Save dialogue messages to Supabase history
        try:
            # Save User Message
            self.conv_svc.save_message(
                session_id=session_id,
                role="user",
                content=query
            )
            # Save Assistant Message with citation metadata
            self.conv_svc.save_message(
                session_id=session_id,
                role="assistant",
                content=validated_content,
                citations=citations
            )
        except Exception as db_save_err:
            logger.error(f"Failed to persist chat message history: {db_save_err}")
            
        # 7. Write analytics entry
        t_total_ms = (time.time() - t_total_start) * 1000
        
        chunk_ids = [block.get("id", "N/A") for block in context_package.get("context_blocks", [])]
        latencies = {
            "retrieval_ms": round(t_ret_ms, 2),
            "prompt_construction_ms": round(t_prompt_ms, 2),
            "generation_ms": round(t_gen_ms, 2),
            "total_ms": round(t_total_ms, 2)
        }
        
        self.analytics_svc.log_interaction(
            query=query,
            intent=retrieval_res["detected_intent"],
            retrieval_confidence=confidence_summary,
            chunk_ids=chunk_ids,
            prompt_len=len(system_prompt) + sum(len(m["content"]) for m in messages_payload),
            completion_len=len(validated_content),
            tokens_used=len(validated_content) // 4,
            answer_confidence=answer_confidence,
            latencies_ms=latencies,
            session_id=session_id,
            project_id=project_id
        )
        
        # 8. Yield final metadata block
        yield json.dumps({
            "citations": citations,
            "confidence_summary": confidence_summary,
            "timings": latencies
        })
