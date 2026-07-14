import psycopg2
from loguru import logger

DB_HOST = "db.qusjpjbvniesgdupvzet.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "X2FouqcznNEG49rh"

def run_migration():
    logger.info("Connecting to PostgreSQL to alter 'documents' columns...")
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
        
        # Drop NOT NULL constraint on storage_path
        logger.info("Dropping NOT NULL constraint on 'documents.storage_path'...")
        cursor.execute("ALTER TABLE documents ALTER COLUMN storage_path DROP NOT NULL;")
        logger.info("[SUCCESS] Constraint dropped successfully.")
        
        cursor.close()
        conn.close()
        logger.info("[SUCCESS] Migrations completed.")
        
    except Exception as e:
        logger.error(f"[FAILURE] Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
