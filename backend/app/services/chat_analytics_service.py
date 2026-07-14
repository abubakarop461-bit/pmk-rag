import os
import json
import time
from typing import Dict, Any, List, Optional
from loguru import logger
from app.repositories.chat_repository import ChatRepository

class ChatAnalyticsService:
    def __init__(self, chat_repository: Optional[ChatRepository] = None, log_dir: str = None):
        self.chat_repo = chat_repository
        if log_dir is None:
            # Default to the scratch artifacts folder for persistence
            log_dir = r"C:\Users\HP\.gemini\antigravity\brain\9a37a6f4-075e-483d-877f-de2d92c490d8\scratch"
        self.log_filepath = os.path.join(log_dir, "chat_analytics.jsonl")

    def log_interaction(
        self,
        query: str,
        intent: str,
        retrieval_confidence: str,
        chunk_ids: List[str],
        prompt_len: int,
        completion_len: int,
        tokens_used: int,
        answer_confidence: str,
        latencies_ms: Dict[str, float],
        session_id: str,
        project_id: str
    ):
        """
        Logs RAG metrics to BOTH a local JSONL log and the Supabase chat_analytics database.
        Fails gracefully if Supabase is offline/unavailable.
        """
        # 1. Local JSONL Write
        try:
            os.makedirs(os.path.dirname(self.log_filepath), exist_ok=True)
            entry = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "session_id": session_id,
                "project_id": project_id,
                "user_query": query,
                "detected_intent": intent,
                "retrieval_confidence": retrieval_confidence,
                "retrieved_chunk_ids": chunk_ids,
                "prompt_character_length": prompt_len,
                "completion_character_length": completion_len,
                "estimated_tokens_used": tokens_used,
                "answer_confidence": answer_confidence,
                "latencies_ms": latencies_ms
            }
            
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
                
            logger.info(f"ChatAnalyticsService wrote local log entry to {self.log_filepath}")
        except Exception as e:
            logger.error(f"Failed to save local chat analytics JSONL: {e}")

        # 2. Supabase Write (Fails Gracefully)
        if self.chat_repo:
            try:
                db_entry = {
                    "session_id": session_id,
                    "project_id": project_id,
                    "user_query": query,
                    "detected_intent": intent,
                    "retrieval_confidence": retrieval_confidence,
                    "answer_confidence": answer_confidence,
                    "retrieved_chunk_ids": chunk_ids,
                    "prompt_length": prompt_len,
                    "completion_length": completion_len,
                    "token_usage": tokens_used,
                    "retrieval_latency": latencies_ms.get("retrieval_ms", 0.0),
                    "llm_latency": latencies_ms.get("generation_ms", 0.0),
                    "total_latency": latencies_ms.get("total_ms", 0.0),
                    "feedback": None
                }
                self.chat_repo.create_analytics_entry(db_entry)
            except Exception as supabase_err:
                logger.warning(f"Failed to record analytics in Supabase (Graceful Fallback): {supabase_err}")
