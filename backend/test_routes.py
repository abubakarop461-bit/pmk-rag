import requests
import json

BASE_URL = "http://localhost:8000/api"
HEADERS = {"Authorization": "Bearer demo_token"}

def run_route_tests():
    print("=== RUNNING API ROUTE RESOLUTION TESTS ===")
    
    # 1. GET /api/health
    print("\n1. Testing GET /api/health...")
    res = requests.get(f"{BASE_URL}/health")
    print(f"Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print(f"Response: {res.json()}")

    # 2. GET /api/projects
    print("\n2. Testing GET /api/projects...")
    res = requests.get(f"{BASE_URL}/projects", headers=HEADERS)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200
    print(f"Found {len(res.json())} projects.")

    # 3. Create a temporary project to test individual details
    print("\nCreating test project...")
    proj_payload = {
        "name": "Route Validation Project",
        "project_number": "PRJ-ROUTE-999",
        "status": "active"
    }
    res = requests.post(f"{BASE_URL}/projects", headers=HEADERS, json=proj_payload)
    print(f"Create Project Status: {res.status_code}")
    assert res.status_code == 201
    project_id = res.json()["id"]
    print(f"Created Project ID: {project_id}")

    # 4. GET /api/projects/{id}
    print(f"\n4. Testing GET /api/projects/{project_id}...")
    res = requests.get(f"{BASE_URL}/projects/{project_id}", headers=HEADERS)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200
    assert res.json()["id"] == project_id

    # 5. GET /api/documents/project/{id}
    print(f"\n5. Testing GET /api/documents/project/{project_id}...")
    res = requests.get(f"{BASE_URL}/documents/project/{project_id}", headers=HEADERS)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200
    print(f"Documents list: {res.json()}")

    # 6. POST /api/documents/project/{id}/upload
    print(f"\n6. Testing POST /api/documents/project/{project_id}/upload...")
    files = {
        "file": ("route_doc.txt", "This is a temporary document for route validation.", "text/plain")
    }
    data = {
        "document_type": "contract",
        "revision_number": "A"
    }
    res = requests.post(f"{BASE_URL}/documents/project/{project_id}/upload", headers=HEADERS, files=files, data=data)
    print(f"Upload Status: {res.status_code}")
    assert res.status_code in [200, 201]
    
    # Wait a couple of seconds for background parsing to finish
    import time
    time.sleep(3)

    # 7. POST /api/retrieval/search
    print("\n7. Testing POST /api/retrieval/search...")
    search_payload = {
        "query": "route validation",
        "project_id": project_id,
        "filters": None,
        "enable_hybrid": True,
        "alpha": 0.5
    }
    res = requests.post(f"{BASE_URL}/retrieval/search", headers=HEADERS, json=search_payload)
    print(f"Search Status: {res.status_code}")
    assert res.status_code == 200
    print(f"Search Results: {len(res.json())} chunks found.")

    # 8. POST /api/chat/stream
    print("\n8. Testing POST /api/chat/stream...")
    
    # 8a. Create a chat session first
    session_payload = {
        "project_id": project_id,
        "title": "Route Validation Chat"
    }
    res = requests.post(f"{BASE_URL}/chat/session", headers=HEADERS, json=session_payload)
    print(f"Create Chat Session Status: {res.status_code}")
    assert res.status_code in [200, 201]
    session_id = res.json()["id"]
    
    # 8b. Run stream
    stream_payload = {
        "session_id": session_id,
        "project_id": project_id,
        "query": "Hello, this is a test message to verify the streaming RAG chat API endpoint."
    }
    res = requests.post(f"{BASE_URL}/chat/stream", headers=HEADERS, json=stream_payload, stream=True)
    print(f"Stream Status: {res.status_code}")
    assert res.status_code == 200
    # Read first chunk of stream to confirm it works
    first_chunk = next(res.iter_lines())
    print(f"First streamed line: {first_chunk.decode('utf-8')}")

    # Clean up test project
    print("\nCleaning up test project...")
    res = requests.delete(f"{BASE_URL}/projects/{project_id}", headers=HEADERS)
    print(f"Delete Status: {res.status_code}")
    assert res.status_code == 204
    
    print("\n=== ALL API ROUTES RESOLVED SUCCESSFULLY AND RETURNED EXPECTED STATUS CODES ===")

if __name__ == "__main__":
    run_route_tests()
