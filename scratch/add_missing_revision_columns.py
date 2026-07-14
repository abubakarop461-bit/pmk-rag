import psycopg2
from loguru import logger

DB_HOST = "db.qusjpjbvniesgdupvzet.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "X2FouqcznNEG49rh"

def run_migration():
    logger.info("Connecting to PostgreSQL to add missing columns to 'document_revisions'...")
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
        
        # Add mime_type, file_size, and processing_status columns
        logger.info("Executing ALTER TABLE to add missing columns...")
        alter_queries = [
            "ALTER TABLE document_revisions ADD COLUMN IF NOT EXISTS mime_type VARCHAR(255);",
            "ALTER TABLE document_revisions ADD COLUMN IF NOT EXISTS file_size BIGINT;",
            "ALTER TABLE document_revisions ADD COLUMN IF NOT EXISTS processing_status VARCHAR(50);"
        ]
        for q in alter_queries:
            cursor.execute(q)
            
        logger.info("[SUCCESS] Missing columns added to 'document_revisions' successfully.")
        
        cursor.close()
        conn.close()
        logger.info("[SUCCESS] Migrations completed.")
        
    except Exception as e:
        logger.error(f"[FAILURE] Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
