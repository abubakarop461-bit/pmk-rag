import os
import uuid
import datetime
from typing import List, Tuple
from loguru import logger

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document

# Global cache for embeddings to prevent reloading
_embeddings_instance = None

def get_embeddings() -> HuggingFaceEmbeddings:
    """Gets or initializes the HuggingFaceEmbeddings singleton."""
    global _embeddings_instance
    if _embeddings_instance is None:
        logger.info("Loading local embedding model BAAI/bge-small-en-v1.5...")
        # BGE embeddings work best with normalize_embeddings=True
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        logger.info("Embedding model loaded successfully.")
    return _embeddings_instance

_qdrant_client_instance = None
_db_mode = None

def get_qdrant_client(url: str = "http://localhost:6333", path: str = "./qdrant_db") -> Tuple[QdrantClient, str]:
    """
    Attempts to connect to a Qdrant Docker container.
    If unavailable, falls back to local on-disk DB.
    Returns (QdrantClient, mode_description).
    Uses a global module-level singleton to ensure only ONE instance is ever created during the process runtime.
    """
    global _qdrant_client_instance, _db_mode
    if _qdrant_client_instance is None:
        try:
            logger.info(f"Attempting to connect to Qdrant Docker server at {url}...")
            client = QdrantClient(url=url, timeout=3.0)
            # Test connection
            client.get_collections()
            logger.info("Successfully connected to Qdrant Docker container.")
            _qdrant_client_instance = client
            _db_mode = "Docker Server"
        except Exception as e:
            logger.warning(f"Qdrant server at {url} is not running: {e}. Falling back to local disk storage.")
            logger.info(f"Initializing local persistent Qdrant database at {path}...")
            _qdrant_client_instance = QdrantClient(path=path)
            _db_mode = "Local Persistent Disk"
    return _qdrant_client_instance, _db_mode

def get_vector_store(client: QdrantClient, embeddings: HuggingFaceEmbeddings, collection_name: str = "documents") -> QdrantVectorStore:
    """
    Initializes QdrantVectorStore, creating the collection manually with 384 dimensions
    (matching BAAI/bge-small-en-v1.5) if it does not exist.
    """
    try:
        # Check if collection exists
        try:
            exists = client.collection_exists(collection_name)
        except AttributeError:
            collections = client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            
        if not exists:
            logger.info(f"Collection '{collection_name}' not found. Creating it manually with 384 dimensions...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Collection '{collection_name}' created successfully.")
    except Exception as e:
        logger.error(f"Error checking/creating Qdrant collection: {e}")
        raise

    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings
    )

def infer_doc_type(filename: str) -> str:
    """Infors the document type based on filename keywords."""
    name_lower = filename.lower()
    if "contract" in name_lower:
        return "contract"
    elif "spec" in name_lower or "specification" in name_lower:
        return "specification"
    elif "drawing" in name_lower:
        return "drawing"
    elif "boq" in name_lower or "quantity" in name_lower:
        return "BOQ"
    elif "rfi" in name_lower:
        return "RFI"
    elif "report" in name_lower:
        return "report"
    else:
        return "general"

def ingest_pdf(file_path: str, vector_store: QdrantVectorStore) -> int:
    """
    Loads, splits, enriches metadata, and indexes a PDF file.
    Returns the number of chunks added.
    """
    filename = os.path.basename(file_path)
    logger.info(f"Starting ingestion for file: {filename}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Load document
    loader = PyPDFLoader(file_path)
    try:
        raw_documents = loader.load()
    except Exception as e:
        logger.error(f"Failed to parse PDF with PyPDFLoader: {e}")
        raise RuntimeError(f"Failed to parse PDF: {e}")
        
    logger.info(f"Loaded {len(raw_documents)} raw pages from {filename}")
    
    # Split document
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(raw_documents)
    total_chunks = len(chunks)
    logger.info(f"Split {filename} into {total_chunks} chunks.")
    
    # Enrich metadata
    # Use deterministic document UUID based on filename and size
    file_size = os.path.getsize(file_path)
    document_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{filename}-{file_size}"))
    upload_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc_type = infer_doc_type(filename)
    
    enriched_chunks = []
    for idx, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        
        # Build enriched metadata dictionary
        # Preserve PyPDFLoader keys (source, page)
        enriched_metadata = {
            "source": chunk.metadata.get("source", file_path),
            "page": chunk.metadata.get("page", 0) + 1,  # standard page is 0-indexed in PyPDF, let's make it 1-indexed for display
            "chunk_id": chunk_id,
            "document_id": document_id,
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "language": "en",
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "filename": filename,
            "upload_date": upload_date,
            "doc_type": doc_type
        }
        
        # Update chunk metadata
        chunk.metadata = enriched_metadata
        enriched_chunks.append(chunk)
        
    # Index to Qdrant
    if enriched_chunks:
        logger.info(f"Indexing {len(enriched_chunks)} chunks to Qdrant...")
        vector_store.add_documents(enriched_chunks)
        logger.info(f"Indexing completed for {filename}.")
        
    return total_chunks

def retrieve_context(query: str, vector_store: QdrantVectorStore, k: int = 5) -> List[Document]:
    """Retrieves the top-k relevant chunks from Qdrant."""
    logger.info(f"Retrieving top-{k} chunks for query: '{query}'")
    try:
        results = vector_store.similarity_search(query, k=k)
        logger.info(f"Retrieved {len(results)} chunks.")
        return results
    except Exception as e:
        logger.error(f"Error during context retrieval: {e}")
        raise
