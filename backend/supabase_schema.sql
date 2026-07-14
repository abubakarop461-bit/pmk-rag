-- 1. Projects Table (Root Entity)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Documents Table (Scoped under Project, Supports Versioning/Revisions)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- 'contract', 'BOQ', 'drawing', 'NCR', 'specification', 'RFI', 'method_statement', 'bim_model', 'other'
    revision VARCHAR(10) NOT NULL DEFAULT 'A', -- Versioning support (e.g. A, B, C, etc.)
    storage_path TEXT NOT NULL,          -- Relative local path or cloud URL
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_project_document_revision UNIQUE(project_id, document_name, revision)
);

-- 3. Document Metadata Table (Key-Value Schema for dynamic taxonomies)
CREATE TABLE IF NOT EXISTS document_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    meta_key VARCHAR(100) NOT NULL,
    meta_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_document_meta_key UNIQUE(document_id, meta_key)
);

-- 4. Chat Sessions Table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID,                        -- Maps to Supabase auth.users.id
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Chat Messages Table (With JSONB Citations)
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,           -- 'user', 'assistant'
    content TEXT NOT NULL,
    citations JSONB,                     -- Array of {document_name, page_number, text_excerpt}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Audit Logs Table (Tracks user operations)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,                        -- ID of the user performing the action
    action VARCHAR(100) NOT NULL,        -- 'user_login', 'file_upload', 'file_deletion', 'document_indexing', 'chat_query', 'gdrive_sync', 'sharepoint_sync'
    details JSONB NOT NULL DEFAULT '{}'::jsonb, -- Action-specific JSON metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Chat Analytics Table (Dual-storage tracking)
CREATE TABLE IF NOT EXISTS chat_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    user_query TEXT NOT NULL,
    detected_intent VARCHAR(100),
    retrieval_confidence VARCHAR(50),
    answer_confidence VARCHAR(50),
    retrieved_chunk_ids TEXT[],         -- List of PointStruct UUID string references
    prompt_length INTEGER,
    completion_length INTEGER,
    token_usage INTEGER,
    retrieval_latency NUMERIC,
    llm_latency NUMERIC,
    total_latency NUMERIC,
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Connector Accounts Table
CREATE TABLE IF NOT EXISTS connector_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,            -- 'google_drive', 'sharepoint', 'onedrive'
    account_email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'connected',   -- 'connected', 'expired', 'disconnected'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. Connector Credentials Table (Splits sensitive tokens from metadata)
CREATE TABLE IF NOT EXISTS connector_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES connector_accounts(id) ON DELETE CASCADE UNIQUE,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Connector Folders Table
CREATE TABLE IF NOT EXISTS connector_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES connector_accounts(id) ON DELETE CASCADE,
    folder_id VARCHAR(255) NOT NULL,          -- Cloud provider folder ID
    folder_name VARCHAR(255),
    sync_enabled BOOLEAN DEFAULT TRUE,
    last_delta_token TEXT,                     -- Stores Delta link / StartPageToken for incremental changes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Connector Webhooks Table
CREATE TABLE IF NOT EXISTS connector_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES connector_accounts(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    subscription_id VARCHAR(255) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    expiration TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'active',      -- 'active', 'expired'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. Connector Sync Jobs Table
CREATE TABLE IF NOT EXISTS connector_sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES connector_accounts(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,               -- 'running', 'completed', 'failed'
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    files_added INTEGER DEFAULT 0,
    files_updated INTEGER DEFAULT 0,
    files_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. Connector Sync Logs Table
CREATE TABLE IF NOT EXISTS connector_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES connector_sync_jobs(id) ON DELETE CASCADE,
    file_id VARCHAR(255) NOT NULL,             -- Cloud provider file ID
    filename VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,               -- 'added', 'updated', 'deleted'
    status VARCHAR(50) NOT NULL,               -- 'success', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
