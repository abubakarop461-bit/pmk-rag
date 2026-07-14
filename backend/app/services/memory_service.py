from typing import List, Dict, Any
from loguru import logger
import httpx
from app.repositories.chat_repository import ChatRepository
from app.core.config import settings

class MemoryService:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repo = chat_repository

    def estimate_tokens(self, text: str) -> int:
        """
        Simple character-based token estimator (1 token ≈ 4 characters).
        """
        return len(text) // 4

    def get_pruned_history(self, session_id: str, max_history_tokens: int = 3000) -> List[Dict[str, str]]:
        """
        Retrieves message history for a session, checking if it fits the token budget.
        Keeps newer turns intact and prunes/summarizes older turns.
        """
        logger.info(f"MemoryService loading history for session {session_id} (Limit: {max_history_tokens} tokens)...")
        raw_msgs = self.chat_repo.get_messages_by_session(session_id)
        
        if not raw_msgs:
            return []
            
        formatted_history = []
        for msg in raw_msgs:
            formatted_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        # Check cumulative history length
        total_tokens = sum(self.estimate_tokens(m["content"]) for m in formatted_history)
        if total_tokens <= max_history_tokens:
            logger.info(f"Loaded entire history of {len(formatted_history)} messages ({total_tokens} tokens).")
            return formatted_history
            
        # Pruning: Keep the last 4 messages intact, summarize older ones if possible
        logger.info(f"History length exceeds budget ({total_tokens} > {max_history_tokens}). Pruning...")
        
        keep_last_n = 4
        if len(formatted_history) <= keep_last_n:
            # Just return whatever we have if it's small, to prevent breaking flows
            return formatted_history
            
        recent_messages = formatted_history[-keep_last_n:]
        older_messages = formatted_history[:-keep_last_n]
        
        # Summarize older messages
        older_tokens = sum(self.estimate_tokens(m["content"]) for m in older_messages)
        logger.info(f"Summarizing older {len(older_messages)} turns ({older_tokens} tokens)...")
        
        summary_text = self.summarize_history(older_messages)
        
        pruned_history = [
            {
                "role": "system",
                "content": f"Summary of previous discussion: {summary_text}"
            }
        ]
        pruned_history.extend(recent_messages)
        
        new_total = sum(self.estimate_tokens(m["content"]) for m in pruned_history)
        logger.info(f"Pruned history compiled. New token count: {new_total} tokens.")
        return pruned_history

    def summarize_history(self, messages: List[Dict[str, str]]) -> str:
        """
        Queries the LLM provider synchronously or lightweight-async to summarize dialogue history.
        """
        # Format discussion turns into a clean text block
        dialogue = ""
        for m in messages:
            dialogue += f"{m['role'].capitalize()}: {m['content']}\n"
            
        summary_instruction = (
            "Summarize the following conversation history between the user and assistant in 3 sentences or less, "
            "preserving all crucial facts, technical terms, and document names:\n\n" + dialogue
        )
        
        # Since we want to switch LLMs dynamically based on settings, we query using standard HTTP requests
        # to ensure lightweight modularity and avoid circular dependencies.
        try:
            api_url = f"{settings.API_V1_STR}/chat/summary" # fallback or direct HTTP post
            # We can use the settings directly to query the provider endpoints:
            if settings.OPENROUTER_API_KEY and "openrouter" in settings.LLM_MODEL:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
            else:
                # Default to Ollama/vLLM base URL
                base_url = settings.LLM_MODEL # wait, config uses LLM_MODEL or LLM_API_BASE
                url = "http://localhost:11434/v1/chat/completions"
                headers = {"Content-Type": "application/json"}
                
            payload = {
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "user", "content": summary_instruction}
                ],
                "temperature": 0.3,
                "max_tokens": 150
            }
            
            # Executing a fast synchronous POST request
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    summary = data["choices"][0]["message"]["content"].strip()
                    logger.info(f"Historical summary generated successfully: '{summary}'")
                    return summary
        except Exception as err:
            logger.warning(f"Failed to generate history summary via LLM: {err}. Using basic truncation fallback.")
            
        # Fallback summary: simple text snippet from the last messages
        return "... " + messages[-1]["content"][:200] + " ..."
