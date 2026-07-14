import os
import sys
import psycopg2
from loguru import logger

# Add backend folder path to sys.path
backend_path = r"c:\Users\HP\OneDrive\Desktop\pmk-RAG\backend"
sys.path.append(backend_path)

DB_HOST = "db.qusjpjbvniesgdupvzet.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "X2FouqcznNEG49rh"

def run_migration():
    logger.info("Connecting to PostgreSQL database to execute migrations...")
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
        
        # Load SQL file content and create tables first
        sql_path = os.path.join(backend_path, "supabase_schema.sql")
        logger.info(f"Reading SQL schema from: {sql_path}")
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
            
        logger.info("Executing base database schema queries...")
        cursor.execute(sql_content)
        
        # Alter projects table to add missing columns expected by Pydantic schemas
        logger.info("Executing ALTER TABLE queries on 'projects' table to add missing schema fields...")
        alter_queries = [
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_number VARCHAR(255);",
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS client_name VARCHAR(255);",
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';",
            "ALTER TABLE projects ADD COLUMN IF NOT EXISTS created_by UUID;"
        ]
        for q in alter_queries:
            cursor.execute(q)
        logger.info("[SUCCESS] Missing columns added to 'projects' table successfully.")
        
        # Verify projects table
        cursor.execute("SELECT id FROM projects WHERE name = 'Test Project';")
        res = cursor.fetchone()
        if res:
            logger.info(f"Test Project already exists in database. ID: {res[0]}")
        else:
            logger.info("Inserting sample 'Test Project'...")
            cursor.execute(
                "INSERT INTO projects (name, project_number, client_name, description, status) "
                "VALUES ('Test Project', 'PRJ-TEST-01', 'Internal Test Client', 'Local development test sandbox.', 'active') "
                "RETURNING id;"
            )
            inserted_id = cursor.fetchone()[0]
            logger.info(f"[SUCCESS] Sample 'Test Project' created with ID: {inserted_id}")
            
        cursor.close()
        conn.close()
        logger.info("[SUCCESS] Database migrations completed.")
        
    except Exception as e:
        logger.error(f"[FAILURE] Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
