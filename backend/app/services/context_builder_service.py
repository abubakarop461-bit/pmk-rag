from typing import List, Dict, Any, Optional
from loguru import logger

class ContextBuilderService:
    def __init__(self, max_tokens: int = 12000):
        self.default_max_tokens = max_tokens

    def estimate_tokens(self, text: str) -> int:
        """
        Simple character-based token estimator (1 token ≈ 4 characters).
        Provides a lightweight, zero-dependency estimation for local execution.
        """
        return len(text) // 4

    def build_context(self, ranked_chunks: List[Dict[str, Any]], max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Builds the final structured context package from ranked chunks:
        Deduplicates, sorts for document flow, merges adjacent chunks, and enforces token budget.
        """
        limit_tokens = max_tokens or self.default_max_tokens
        logger.info(f"ContextBuilderService starting. Token budget: {limit_tokens} tokens.")
        
        if not ranked_chunks:
            return {
                "context_blocks": [],
                "confidence_summary": "Low",
                "total_estimated_tokens": 0,
                "citations": []
            }
            
        # 1. Deduplicate by chunk ID
        deduped = {}
        for chunk in ranked_chunks:
            deduped[chunk["id"]] = chunk
        unique_chunks = list(deduped.values())
        
        # 2. Sort by document_id, page_number, chunk_index to preserve document flow
        unique_chunks.sort(key=lambda x: (x["document_id"], x["page_number"], x["chunk_index"]))
        
        # 3. Merge Adjacent Chunks (same document, consecutive chunks or adjacent pages)
        merged_blocks = []
        current_block = None
        
        for chunk in unique_chunks:
            if current_block is None:
                # Initialize first block
                current_block = {
                    "text": chunk["text"],
                    "document_id": chunk["document_id"],
                    "project_id": chunk["project_id"],
                    "revision_id": chunk["revision_id"],
                    "filename": chunk["filename"],
                    "document_type": chunk["document_type"],
                    "pages": [chunk["page_number"]],
                    "chunk_indexes": [chunk["chunk_index"]],
                    "vector_score": chunk["vector_score"],
                    "keyword_score": chunk["keyword_score"],
                    "rerank_score": chunk["rerank_score"],
                    "explain": chunk["explain"]
                }
            else:
                # Check if current chunk is adjacent to the previous one
                is_same_doc = chunk["document_id"] == current_block["document_id"]
                is_adjacent_page = abs(chunk["page_number"] - current_block["pages"][-1]) <= 1
                is_consecutive_chunk = abs(chunk["chunk_index"] - current_block["chunk_indexes"][-1]) <= 1
                
                if is_same_doc and (is_adjacent_page or is_consecutive_chunk):
                    # Merge text and append metadata arrays
                    current_block["text"] += "\n" + chunk["text"]
                    if chunk["page_number"] not in current_block["pages"]:
                        current_block["pages"].append(chunk["page_number"])
                    current_block["chunk_indexes"].append(chunk["chunk_index"])
                    # Carry forward highest score parameters
                    current_block["vector_score"] = max(current_block["vector_score"], chunk["vector_score"])
                    current_block["keyword_score"] = max(current_block["keyword_score"], chunk["keyword_score"])
                    current_block["rerank_score"] = max(current_block["rerank_score"], chunk["rerank_score"])
                else:
                    # Save previous block and start new one
                    merged_blocks.append(current_block)
                    current_block = {
                        "text": chunk["text"],
                        "document_id": chunk["document_id"],
                        "project_id": chunk["project_id"],
                        "revision_id": chunk["revision_id"],
                        "filename": chunk["filename"],
                        "document_type": chunk["document_type"],
                        "pages": [chunk["page_number"]],
                        "chunk_indexes": [chunk["chunk_index"]],
                        "vector_score": chunk["vector_score"],
                        "keyword_score": chunk["keyword_score"],
                        "rerank_score": chunk["rerank_score"],
                        "explain": chunk["explain"]
                    }
                    
        if current_block is not None:
            merged_blocks.append(current_block)
            
        # 4. Respect Token Budget and Compile Citations
        final_blocks = []
        cumulative_tokens = 0
        citations = []
        
        for block in merged_blocks:
            block_tokens = self.estimate_tokens(block["text"])
            if cumulative_tokens + block_tokens > limit_tokens:
                logger.info(f"Token budget reached ({cumulative_tokens} + {block_tokens} > {limit_tokens}). Capping context.")
                break
                
            cumulative_tokens += block_tokens
            final_blocks.append(block)
            
            # Format citation metadata dictionary
            citations.append({
                "document_id": block["document_id"],
                "filename": block["filename"],
                "pages": block["pages"],
                "document_type": block["document_type"]
            })
            
        # 5. Calculate Overall Confidence Summary
        # Based on highest re-rank score logit threshold mappings
        max_rerank = -99.0
        for block in final_blocks:
            if block["rerank_score"] > max_rerank:
                max_rerank = block["rerank_score"]
                
        confidence_summary = "Low"
        if max_rerank > 1.5:
            confidence_summary = "Very High"
        elif max_rerank > 0.0:
            confidence_summary = "High"
        elif max_rerank > -2.0:
            confidence_summary = "Medium"
            
        logger.info(f"Context compiled successfully. {len(final_blocks)} blocks generated. Confidence: {confidence_summary}. Est. Tokens: {cumulative_tokens}")
        
        return {
            "context_blocks": final_blocks,
            "confidence_summary": confidence_summary,
            "total_estimated_tokens": cumulative_tokens,
            "citations": citations
        }
