"""Quick test to verify the server integration works."""

import asyncio
import requests
import time

def test_server():
    """Test the API endpoints."""
    base_url = "http://localhost:8000"
    
    # Check health
    print("1. Testing health check...")
    try:
        r = requests.get(f"{base_url}/health", timeout=2)
        print(f"   ✓ Health check: {r.json()}")
    except Exception as e:
        print(f"   ✗ Server not running: {e}")
        print("   Start it with: python server.py")
        return
    
    # Create a test job
    print("\n2. Creating test job...")
    job_data = {
        "query": "test dental clinics",
        "engine": "ddg",
        "backend": "scrapling",
        "check_mx": False,
    }
    
    try:
        r = requests.post(f"{base_url}/jobs", json=job_data)
        r.raise_for_status()
        job = r.json()
        job_id = job["id"]
        print(f"   ✓ Job created: {job_id}")
        print(f"   Status: {job['status']}")
        
        # Poll for updates
        print("\n3. Polling for stats updates...")
        for i in range(10):
            time.sleep(1)
            r = requests.get(f"{base_url}/jobs/{job_id}/status")
            job = r.json()
            stats = job["stats"]
            
            print(f"   [{i+1}] Status: {job['status']}, "
                  f"Pages: {stats['pages_crawled']}, "
                  f"Emails: {stats['new_emails']}/{stats['total_emails']}")
            
            if job['status'] in ['completed', 'failed', 'stopped']:
                print(f"\n   Job finished with status: {job['status']}")
                break
        
        # Stop the job if still running
        if job['status'] == 'running':
            print("\n4. Stopping job...")
            r = requests.delete(f"{base_url}/jobs/{job_id}")
            print("   ✓ Job stopped")
        
        print("\n✓ Test complete! Integration is working.")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_server()
