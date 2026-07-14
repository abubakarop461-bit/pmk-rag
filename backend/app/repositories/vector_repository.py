from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue, MatchText
from app.repositories.base_repository import BaseRepository
from loguru import logger

class VectorRepository(BaseRepository):
    def __init__(self, qdrant_client):
        self.client = qdrant_client

    def ensure_collection(self, collection_name: str, size: int = 384):
        """
        Validates collection existence, initializing with Cosine metric and full-text indexes if missing.
        """
        try:
            collections = [col.name for col in self.client.get_collections().collections]
            if collection_name not in collections:
                logger.info(f"Creating Qdrant collection '{collection_name}' with vector size {size}...")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=size, distance=Distance.COSINE)
                )
                logger.info(f"Qdrant collection '{collection_name}' created.")
                
                # Build inverted full-text index on the payload 'text' field for keyword searches
                logger.info(f"Creating text index on '{collection_name}' field 'text'...")
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="text",
                    field_schema="text"
                )
                logger.info("Text index created.")
        except Exception as e:
            logger.error(f"Failed to verify or create Qdrant collection: {e}")
            raise RuntimeError(f"Qdrant initialization error: {e}")

    def insert_vectors(self, collection_name: str, points: list):
        """
        Performs bulk upsert of PointStruct vectors to Qdrant.
        """
        try:
            logger.info(f"Uploading {len(points)} points to Qdrant collection '{collection_name}'...")
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info("Points successfully upserted to Qdrant.")
        except Exception as e:
            logger.error(f"Failed to upload points to Qdrant: {e}")
            raise RuntimeError(f"Qdrant upsert error: {e}")

    def search_vectors(self, collection_name: str, query_vector: list, limit: int = 20, payload_filter: dict = None) -> list:
        """
        Queries Qdrant using similarity search and filters.
        """
        try:
            qdrant_filter = None
            if payload_filter:
                conditions = []
                for k, v in payload_filter.items():
                    if v is not None:
                        conditions.append(FieldCondition(key=k, match=MatchValue(value=v)))
                if conditions:
                    qdrant_filter = Filter(must=conditions)
                    
            res = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True
            )
            return res.points
        except Exception as e:
            logger.error(f"Similarity vector search failed: {e}")
            raise RuntimeError(f"Qdrant search error: {e}")

    def search_text(self, collection_name: str, query: str, limit: int = 20, payload_filter: dict = None) -> list:
        """
        Queries Qdrant using the full-text payload index (BM25 equivalent).
        """
        try:
            conditions = [FieldCondition(key="text", match=MatchText(text=query))]
            if payload_filter:
                for k, v in payload_filter.items():
                    if v is not None:
                        conditions.append(FieldCondition(key=k, match=MatchValue(value=v)))
                        
            # Scroll points matching the text conditions
            result, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(must=conditions),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            return result
        except Exception as e:
            logger.error(f"Full-text scroll search failed: {e}")
            raise RuntimeError(f"Qdrant text scroll error: {e}")

    def delete_document_vectors(self, collection_name: str, document_id: str):
        """
        Deletes all vector points associated with a specific document ID.
        """
        try:
            logger.info(f"Cleaning up Qdrant points for document_id: {document_id}")
            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
        except Exception as e:
            logger.warning(f"Failed to clean up Qdrant vectors for doc {document_id}: {e}")

    def get_points_by_revision(self, collection_name: str, revision_id: str) -> list:
        """Retrieves all vector points associated with a specific revision ID."""
        points = []
        offset = None
        while True:
            res, offset = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="revision_id",
                            match=MatchValue(value=revision_id)
                        )
                    ]
                ),
                limit=100,
                with_payload=True,
                with_vectors=True,
                offset=offset
            )
            points.extend(res)
            if offset is None:
                break
        return points

    def clone_document_vectors(
        self,
        collection_name: str,
        source_revision_id: str,
        target_project_id: str,
        target_document_id: str,
        target_revision_id: str,
        target_filename: str
    ) -> int:
        """
        Clones vector points from a source revision ID to a target document/revision,
        updating payloads for isolation.
        """
        import uuid
        old_points = self.get_points_by_revision(collection_name, source_revision_id)
        if not old_points:
            return 0
            
        new_points = []
        for pt in old_points:
            new_payload = dict(pt.payload)
            new_payload.update({
                "project_id": target_project_id,
                "document_id": target_document_id,
                "revision_id": target_revision_id,
                "filename": target_filename
            })
            if "metadata" in new_payload:
                new_payload["metadata"] = dict(new_payload["metadata"])
                new_payload["metadata"].update({
                    "filename": target_filename
                })
            
            new_points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=pt.vector,
                    payload=new_payload
                )
            )
            
        self.insert_vectors(collection_name, new_points)
        return len(new_points)

