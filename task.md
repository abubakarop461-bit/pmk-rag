# Construction Document Intelligence Platform - Task Roadmap

## Phase 1: Architectural Foundation & Monorepo Setup
- [x] Create project layout and repository placeholders
- [x] Configure Next.js 15 (TypeScript, Tailwind, shadcn)
- [x] Configure FastAPI settings, config, lifespan connection checks, and CORS
- [x] Connect Supabase client & Qdrant vector database placeholders
- [x] Implement API health check endpoints
- [x] Verify frontend & backend communication
- [x] Create detailed Architecture Decision Record (`adr.md`)

## Phase 2: Project & Document Management (SaaS Foundation)
- [x] Implement database schema in Supabase (`supabase_schema.sql`)
- [x] Set up Supabase Auth on frontend and JWT token interceptor
- [x] Build backend security module to verify JWTs via Supabase Auth API
- [x] Build Project CRUD REST endpoints (with audit logging)
- [x] Build Document upload/delete and revision chain APIs
- [x] Create local file storage directory layout
- [x] Implement UI views: Login, Dashboard, Projects page, Upload dialog, and Version History dialog
- [x] Verify TS TypeScript compiling and Python module imports
- [x] Create repository CRUD validation script (`test_supabase_repo.py`)

## Phase 3A: AI Ingestion Foundation
- [x] Implement BaseJobQueue interface and LocalBackgroundTasksQueue wrapper
- [x] Build concrete parser plugins: PDF (PyMuPDF), DOCX (python-docx), XLSX (openpyxl), PPTX (python-pptx), TXT (plain text), and Image (placeholder)
- [x] Create ParserService dynamic extension router
- [x] Implement MetadataService extracting page count, OS stats, size, and language heuristics
- [x] Implement file validation rules (empty, max size, extensions, corruption, duplicate checksums)
- [x] Refactor IngestionService to return success immediately and execute worker task asynchronously
- [x] Update frontend documents table to display live processing status badges (`validating`, `parsing`, `metadata_extraction`) and upload timestamps
- [x] Verify TS typescript compiling and python imports
- [x] Create integration test script (`test_ingestion_foundation.py`)

## Phase 3B: AI Indexing (OCR, Chunking, Embeddings, Indexing)
- [x] Implement scanned page OCR fallback (PaddleOCR with Tesseract fallback)
- [x] Implement chunking configuration (RecursiveCharacterTextSplitter with metadata tracking)
- [x] Implement local BAAI BGE embedding generation (384d)
- [x] Configure Qdrant collection creation and vector payload indexing
- [x] Integrate document status states (`validating`, `parsing`, `ocr`, `chunking`, `embedding`, `indexing`)
- [x] Verify Python compile checks and Qdrant integration tests

## Phase 3C: Enterprise Retrieval Engine
- [x] Build QueryPreprocessingService, Query ExpansionService, and QueryIntentService
- [x] Build MetadataFilterService, HybridSearchService, and RerankerService
- [x] Build ContextBuilderService managing chunk merging, token budgets, and citations
- [x] Implement POST `/api/retrieval/search` endpoint returning timing profiles and explain tags
- [x] Design React diagnostics search testing console mapping all timings and blocks
- [x] Verify all integration tests run successfully with zero errors

## Phase 4: Chat & Enterprise RAG
- [x] Build conversation memory database schemas in Supabase and ChatRepository client mappings
- [x] Implement MemoryService supporting token budgets and dialogue summaries
- [x] Move all prompts into file-driven templates (`system_prompt.txt`, `construction_prompt.txt`, `citation_prompt.txt`, `no_context_prompt.txt`)
- [x] Implement AnswerValidationService checking for citations, relevance, and fallback refusals
- [x] Implement ChatAnalyticsService writing JSONL logs to local scratch archives
- [x] Implement PromptBuilderService, ChatService, and `/chat/stream` SSE endpoints
- [x] Build React Chat UI view with thread sidebar, streaming bubbles, confidence badges, and citation lists
- [x] Verify all integration tests run successfully with zero errors
