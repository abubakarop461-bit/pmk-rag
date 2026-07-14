import psycopg2
from loguru import logger

DB_HOST = "db.qusjpjbvniesgdupvzet.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "X2FouqcznNEG49rh"

def run_migration():
    logger.info("Connecting to PostgreSQL to alter 'document_revisions' table...")
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
        
        # Add processing_timings column
        logger.info("Executing ALTER TABLE to add 'processing_timings' column...")
        cursor.execute("ALTER TABLE document_revisions ADD COLUMN IF NOT EXISTS processing_timings JSONB;")
        logger.info("[SUCCESS] 'processing_timings' column added successfully.")
        
        cursor.close()
        conn.close()
        logger.info("[SUCCESS] Migrations completed.")
        
    except Exception as e:
        logger.error(f"[FAILURE] Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
