import psycopg2
from loguru import logger

DB_HOST = "db.qusjpjbvniesgdupvzet.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "X2FouqcznNEG49rh"

def run_migration():
    logger.info("Connecting to PostgreSQL to create 'document_revisions' table...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 1. Create document_revisions table
        logger.info("Executing CREATE TABLE query for 'document_revisions'...")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS document_revisions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
            revision_number VARCHAR(50) NOT NULL,
            checksum VARCHAR(255),
            storage_path TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        cursor.execute(create_table_sql)
        logger.info("[SUCCESS] 'document_revisions' table created successfully.")
        
        cursor.close()
        conn.close()
        logger.info("[SUCCESS] Migrations completed.")
        
    except Exception as e:
        logger.error(f"[FAILURE] Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
