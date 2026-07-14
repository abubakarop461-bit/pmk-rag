import argparse
import sys
from loguru import logger
from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()

# Import backend modules
from llm_provider import OpenRouterLLMProvider
from rag_backend import (
    get_embeddings,
    get_qdrant_client,
    get_vector_store,
    ingest_pdf,
    retrieve_context
)

def main():
    parser = argparse.ArgumentParser(description="CLI Tool for RAG Prototype (OpenRouter + Qdrant)")
    parser.add_argument("--ingest", type=str, help="Path to PDF file to ingest and index")
    parser.add_argument("--query", type=str, help="Question to ask the database")
    parser.add_argument("--model", type=str, default="qwen/qwen3-8b", help="OpenRouter model name")
    
    args = parser.parse_args()
    
    if not args.ingest and not args.query:
        parser.print_help()
        sys.exit(1)
        
    # 1. Initialize Qdrant Client
    db_client, db_mode = get_qdrant_client()
    logger.info(f"Connected to Qdrant database in '{db_mode}' mode.")
    
    # 2. Get embeddings and setup vector store
    try:
        embeddings = get_embeddings()
        vector_store = get_vector_store(db_client, embeddings, collection_name="rag_documents")
    except Exception as e:
        logger.error(f"Database connection or vector store setup failed: {e}")
        print(f"Database setup error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 3. Perform ingestion if requested
    if args.ingest:
        logger.info(f"Ingesting PDF: '{args.ingest}'")
        try:
            chunks = ingest_pdf(args.ingest, vector_store)
            print(f"\n[SUCCESS] Successfully indexed '{args.ingest}'. Created and stored {chunks} chunks in Qdrant.")
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            print(f"Error during ingestion: {e}", file=sys.stderr)
            sys.exit(1)
            
    # 4. Perform query if requested
    if args.query:
        logger.info(f"Running query: '{args.query}' using model '{args.model}'")
        try:
            # Retrieve top-5 contexts
            docs = retrieve_context(args.query, vector_store, k=5)
            if not docs:
                print("\nNot found in the provided documents.")
                sys.exit(0)
                
            # Build context text block
            context_blocks = []
            for doc in docs:
                filename = doc.metadata.get("filename", "Unknown")
                page = doc.metadata.get("page", "Unknown")
                context_blocks.append(f"[File: {filename}, Page: {page}]\n{doc.page_content}")
            context_text = "\n\n".join(context_blocks)
            
            # Setup LLM Provider
            llm_provider = OpenRouterLLMProvider(model_name=args.model)
            if not llm_provider.api_key:
                print("\n[ERROR] Error: OPENROUTER_API_KEY environment variable is not configured.", file=sys.stderr)
                print("Please set the key in your terminal or create a local '.env' file.", file=sys.stderr)
                sys.exit(1)
                
            # Stream answer to console
            print("\n[ANSWER]: ", end="", flush=True)
            for chunk in llm_provider.stream_answer(args.query, context_text):
                print(chunk, end="", flush=True)
            print("\n")
            
            # Print citations
            print("=" * 60)
            print("CITATIONS & SOURCES")
            print("=" * 60)
            for idx, doc in enumerate(docs):
                filename = doc.metadata.get("filename", "Unknown")
                page = doc.metadata.get("page", "Unknown")
                dtype = doc.metadata.get("doc_type", "general")
                total_chks = doc.metadata.get("total_chunks", 0)
                chk_idx = doc.metadata.get("chunk_index", 0)
                
                print(f"[{idx+1}] File: {filename} (Page {page}) [Type: {dtype.upper()}]")
                print(f"    Chunk Index: {chk_idx + 1}/{total_chks} | Doc ID: {doc.metadata.get('document_id')}")
                print(f"    Excerpt: \"{doc.page_content.strip().replace(chr(10), ' ')}\"")
                print("-" * 60)
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            print(f"Error during query execution: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
