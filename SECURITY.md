# 🔐 Security & Secrets Policy

## Confirmed: No secrets are pushed to this repository.

The following sensitive files and directories are **excluded** by `.gitignore` and are **absent from all 133 tracked files**:

| File / Directory | Status |
|---|---|
| `.env` | ❌ Not tracked ✅ |
| `.venv/` | ❌ Not tracked ✅ |
| `node_modules/` | ❌ Not tracked ✅ |
| `qdrant_db/` | ❌ Not tracked ✅ |
| `*.log` files | ❌ Not tracked ✅ |

---

## What IS committed (safe)

| File | Purpose |
|---|---|
| `.env.example` | Template only — contains no real keys or tokens |
| `backend/requirements.txt` | Python package list — no secrets |
| `frontend/package.json` | Node package list — no secrets |
| `docker-compose.yml` | Local Qdrant config — no secrets |

---

## .gitignore Coverage

The `.gitignore` at the repository root explicitly excludes:

```
# Environment & Secrets
.env
.env.*
!.env.example
*.local

# Python runtime
__pycache__/
*.py[cod]
.venv/
*.log

# Node
node_modules/
.next/
build/
out/

# Local data stores
qdrant_db/
test_qdrant_db/
local_storage/
logs/
```

---

## How to configure secrets locally

1. Copy the safe template:
   ```bash
   cp .env.example .env
   ```

2. Fill in your real credentials in `.env`:
   ```env
   OPENROUTER_API_KEY=your_real_key_here
   SUPABASE_URL=https://your-project.supabase.co/rest/v1/
   SUPABASE_ANON_KEY=your_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   LLM_MODEL=qwen/qwen3-8b
   LLM_PROVIDER=openrouter
   DEMO_MODE=false
   ```

3. The `.env` file will **never** be committed — it is protected by `.gitignore`.

---

## Verification

To confirm no secrets exist in git history at any point:

```bash
git log --all --full-history -- .env
# Should return empty — .env was never committed
```

```bash
git diff origin/main HEAD --stat
# Should return empty — local and remote are identical
```
