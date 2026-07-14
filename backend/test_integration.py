import time
import requests
import threading
import json
from app.core.supabase import get_supabase_client

BASE_URL = "http://localhost:8000/api"
HEADERS = {"Authorization": "Bearer demo_token"}

def run_test():
    print("=== STARTING INTEGRATION TEST ===")
    
    # 1. Check/Create Project
    db = get_supabase_client()
    projects = db.table("projects").select("*").limit(1).execute().data
    if projects:
        project_id = projects[0]["id"]
        print(f"Reusing existing project ID: {project_id}")
    else:
        # Create a project
        proj_data = {
            "name": "Integration Test Project",
            "project_number": "PRJ-TEST-001",
            "status": "active"
        }
        res = db.table("projects").insert(proj_data).execute().data
        project_id = res[0]["id"]
        print(f"Created new test project ID: {project_id}")

    # 2. Start SSE listener in a background thread
    events_received = []
    sse_url = f"{BASE_URL}/documents/project/{project_id}/events"
    
    def listen_sse():
        print(f"SSE Listener: Connecting to {sse_url}")
        try:
            response = requests.get(sse_url, headers=HEADERS, stream=True)
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data:"):
                        payload_str = decoded[5:].strip()
                        try:
                            payload = json.loads(payload_str)
                            print(f"SSE Event Received: {payload}")
                            events_received.append(payload)
                        except Exception as parse_err:
                            print(f"SSE Parse Error: {parse_err} for line: {decoded}")
        except Exception as conn_err:
            print(f"SSE Connection error: {conn_err}")

    listener_thread = threading.Thread(target=listen_sse, daemon=True)
    listener_thread.start()
    
    # Wait for listener to connect
    time.sleep(2)
    
    file_content = f"This is a dummy construction specification file for testing real-time AI ingestion pipeline. Timestamp: {time.time()}"
    filename = f"spec_doc_{int(time.time())}.txt"
    files = {
        "file": (filename, file_content, "text/plain")
    }
    data = {
        "document_type": "specification",
        "revision_number": "A"
    }
    
    print("\n--- UPLOADING FIRST FILE ---")
    upload_url = f"{BASE_URL}/documents/project/{project_id}/upload"
    up_res = requests.post(upload_url, headers=HEADERS, files=files, data=data)
    print(f"Upload Status Code: {up_res.status_code}")
    assert up_res.status_code in [200, 201], f"Upload failed: {up_res.text}"
    
    res_data = up_res.json()
    revision_id = res_data["revision"]["id"]
    print(f"Uploaded Revision ID: {revision_id}")
    
    # Wait for ingestion to finish by polling the database status or listening to SSE ready event
    ready = False
    for _ in range(30):
        time.sleep(1)
        # Check database directly
        rev = db.table("document_revisions").select("*").eq("id", revision_id).execute().data
        if rev:
            status = rev[0]["processing_status"]
            print(f"Processing Status: {status}")
            if status == "ready":
                ready = True
                break
            if status == "failed":
                print(f"Ingestion failed: {rev[0]['error_message']}")
                break
                
    assert ready, "Ingestion did not reach ready state in 30 seconds."
    print("Ingestion successfully completed!")

    # Verify that we received the expected sequence of SSE events
    statuses_received = [e.get("processing_status") for e in events_received if e.get("revision_id") == revision_id]
    print(f"SSE events sequence: {statuses_received}")
    assert "parsing" in statuses_received, "Missing parsing status in SSE stream"
    assert "ready" in statuses_received, "Missing ready status in SSE stream"
    
    # Check that timings are recorded
    rev_record = db.table("document_revisions").select("processing_timings").eq("id", revision_id).execute().data
    timings = rev_record[0]["processing_timings"]
    print(f"Recorded Timings: {timings}")
    assert timings is not None, "Timings were not saved in the database."
    assert timings.get("total_ms") is not None, "Missing total_ms timing milestone"

    # 4. Upload EXACT same file again to the same project (Duplicate Check)
    print("\n--- UPLOADING SAME FILE AGAIN (SAME PROJECT) ---")
    filename_dup = f"spec_doc_dup_{int(time.time())}.txt"
    files_dup = {
        "file": (filename_dup, file_content, "text/plain")
    }
    dup_res = requests.post(upload_url, headers=HEADERS, files=files_dup, data=data)
    print(f"Duplicate Upload Status Code: {dup_res.status_code}")
    print(f"Response: {dup_res.text}")
    assert dup_res.status_code == 400, "Same project duplicate check failed to reject."
    assert "already indexed" in dup_res.text.lower(), "Expected duplicate indexed validation message."
    print("Duplicate file successfully rejected with HTTP 400!")

    # 5. Create a second project and upload same file (Cross-project duplicate vector cloning check)
    print("\n--- UPLOADING SAME FILE TO A SECOND PROJECT ---")
    proj_data_2 = {
        "name": "Second Integration Project",
        "project_number": "PRJ-TEST-002",
        "status": "active"
    }
    res_2 = db.table("projects").insert(proj_data_2).execute().data
    project_id_2 = res_2[0]["id"]
    print(f"Created second project ID: {project_id_2}")
    
    # Upload to project 2
    upload_url_2 = f"{BASE_URL}/documents/project/{project_id_2}/upload"
    files_proj2 = {
        "file": (filename, file_content, "text/plain")
    }
    t_start = time.time()
    proj2_res = requests.post(upload_url_2, headers=HEADERS, files=files_proj2, data=data)
    print(f"Project 2 Upload Status Code: {proj2_res.status_code}")
    assert proj2_res.status_code in [200, 201], f"Upload failed: {proj2_res.text}"
    
    proj2_rev_id = proj2_res.json()["revision"]["id"]
    
    # Ingestion should finish almost instantly (< 1 second) because it clones Qdrant vectors
    cloned_ready = False
    for _ in range(5):
        time.sleep(0.5)
        rev = db.table("document_revisions").select("*").eq("id", proj2_rev_id).execute().data
        if rev and rev[0]["processing_status"] == "ready":
            cloned_ready = True
            break
            
    assert cloned_ready, "Cloning cross-project duplicate failed or took too long."
    print(f"Cloned cross-project document became ready instantly!")
    
    # Clean up test database records
    print("\n=== CLEANING UP TEST DATA ===")
    # Cascade delete will handle revisions and metadata
    db.table("projects").delete().eq("id", project_id).execute()
    db.table("projects").delete().eq("id", project_id_2).execute()
    print("Clean up completed successfully.")
    
    print("\n=== INTEGRATION TEST PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_test()
