import uuid
from typing import List, Optional
from langchain_core.documents import Document
from qdrant_client.models import PointStruct
from loguru import logger

from app.repositories.vector_repository import VectorRepository
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService

class IndexingService:
    def __init__(
        self, 
        vector_repository: VectorRepository,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService
    ):
        self.vector_repo = vector_repository
        self.chunk_svc = chunking_service
        self.embed_svc = embedding_service

    def index_document_pages(
        self, 
        project_id: str,
        document_id: str,
        revision_id: str,
        document_type: str,
        filename: str,
        pages: List[Document],
        collection_name: str = "rag_documents",
        extra_metadata: Optional[dict] = None
    ) -> dict:
        """
        Chunks pages individually to preserve page numbers, computes embeddings, and inserts to Qdrant.
        """
        import time
        logger.info(f"IndexingService starting chunking and vector mapping for: {filename}")
        
        # 1. Ensure Qdrant collection is initialized
        self.vector_repo.ensure_collection(collection_name, size=384)
        
        # 2. Split page documents individually to maintain precise page mapping
        chunk_start = time.time()
        all_chunks = []
        for idx, page in enumerate(pages):
            page_num = page.metadata.get("page", idx + 1)
            chunks = self.chunk_svc.split([page])
            for c_idx, chunk in enumerate(chunks):
                all_chunks.append({
                    "text": chunk.page_content,
                    "page_number": page_num,
                    "chunk_index": c_idx + 1
                })
                
        logger.info(f"Split document into {len(all_chunks)} chunks.")
        chunking_ms = int((time.time() - chunk_start) * 1000)
        
        if not all_chunks:
            logger.warning("Zero text chunks resolved. Skipping Qdrant vector indexing.")
            return {
                "chunking_ms": chunking_ms,
                "embedding_ms": 0,
                "indexing_ms": 0
            }

        # 3. Generate BGE embeddings in batch and construct PointStruct payloads
        embed_start = time.time()
        texts = [item["text"] for item in all_chunks]
        logger.info(f"Computing BGE embeddings in batch for {len(texts)} chunks...")
        vectors = self.embed_svc.embed_texts(texts)
        embedding_ms = int((time.time() - embed_start) * 1000)
        
        index_start = time.time()
        points = []
        for i, item in enumerate(all_chunks):
            text = item["text"]
            page_num = item["page_number"]
            chunk_idx = item["chunk_index"]
            vector = vectors[i]
            
            point_id = str(uuid.uuid4())
            
            # Construct metadata dictionary containing extra construction keys
            meta_dict = {"filename": filename}
            if extra_metadata:
                for key in ["drawing_number", "discipline", "sheet", "level", "revision"]:
                    if key in extra_metadata and extra_metadata[key] is not None:
                        meta_dict[key] = extra_metadata[key]
                        
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": text,
                        "project_id": project_id,
                        "document_id": document_id,
                        "revision_id": revision_id,
                        "page_number": page_num,
                        "chunk_index": chunk_idx,
                        "document_type": document_type,
                        "drawing_number": extra_metadata.get("drawing_number") if (extra_metadata and "drawing_number" in extra_metadata) else None,
                        "discipline": extra_metadata.get("discipline") if (extra_metadata and "discipline" in extra_metadata) else None,
                        "level": extra_metadata.get("level") if (extra_metadata and "level" in extra_metadata) else None,
                        "sheet": extra_metadata.get("sheet") if (extra_metadata and "sheet" in extra_metadata) else None,
                        "metadata": meta_dict
                    }
                )
            )
            
        # 4. Upsert vectors in bulk
        self.vector_repo.insert_vectors(collection_name, points)
        logger.info(f"Successfully loaded {len(points)} vector records into Qdrant.")
        indexing_ms = int((time.time() - index_start) * 1000)
        
        return {
            "chunking_ms": chunking_ms,
            "embedding_ms": embedding_ms,
            "indexing_ms": indexing_ms
        }

