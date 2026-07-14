# Enterprise AI Document Intelligence Platform

A full-stack RAG (Retrieval-Augmented Generation) platform built for construction document management and intelligent Q&A.

---

## Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, TypeScript, Vanilla CSS |
| **Backend** | FastAPI (Python 3.11+) |
| **Vector DB** | Qdrant |
| **Database** | Supabase (PostgreSQL) |
| **Embeddings** | sentence-transformers |
| **Reranker** | cross-encoder |
| **OCR** | PaddleOCR / Tesseract fallback |
| **LLM** | OpenRouter / Ollama / vLLM (configurable) |

---

## Features

- 📄 **Multi-format Ingestion** — PDF, DOCX, XLSX, PPTX, IFC, images
- 🔍 **Hybrid Search** — Dense + BM25 sparse retrieval with cross-encoder reranking
- 🤖 **Streaming RAG Chat** — Real-time SSE token streaming
- 🏗️ **Construction Intelligence** — Document classification, revision management
- ☁️ **Cloud Connectors** — Google Drive, SharePoint, OneDrive (pluggable)
- 🔐 **Auth** — Supabase JWT authentication
- 📊 **Analytics** — Chat analytics, answer validation, confidence scoring
- 🩺 **Health API** — `/api/health` startup validation for all services

---

## Project Structure

```
pmk-rag/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/              # Route handlers
│   │   ├── services/         # Business logic
│   │   ├── repositories/     # Data access
│   │   ├── parsers/          # Document parsers
│   │   ├── search/           # Retrieval & reranking
│   │   └── core/             # Config, security, DB clients
│   ├── requirements.txt
│   └── supabase_schema.sql
├── frontend/                 # Next.js application
│   ├── app/
│   │   ├── page.tsx          # Dashboard
│   │   ├── projects/[id]/    # Project detail + uploads
│   │   ├── chat/             # RAG chat interface
│   │   ├── retrieval/        # Semantic search
│   │   └── settings/         # Cloud connectors
│   └── lib/
│       ├── api-client.ts     # Axios client
│       └── supabase-client.ts
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/abubakarop461-bit/pmk-rag.git
cd pmk-rag
cp .env.example .env
# Fill in your credentials in .env
```

### 2. Start Qdrant

```bash
docker-compose up -d
```

### 3. Backend

```bash
cd backend
python -m venv ../.venv
../.venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # or create it manually
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
OPENROUTER_API_KEY=your_key
SUPABASE_URL=https://your-project.supabase.co/rest/v1/
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key
QDRANT_HOST=localhost
QDRANT_PORT=6333
LLM_MODEL=qwen/qwen3-8b
LLM_PROVIDER=openrouter   # openrouter | ollama | vllm
DEMO_MODE=false
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Service health check |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/documents/project/{id}` | List documents |
| POST | `/api/documents/project/{id}/upload` | Upload document |
| POST | `/api/retrieval/search` | Hybrid semantic search |
| POST | `/api/chat/stream` | SSE streaming RAG chat |
| GET | `/api/chat/sessions?project_id=` | List chat sessions |
| POST | `/api/chat/session` | Create chat session |

---

## License

MIT
