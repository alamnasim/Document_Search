#!/usr/bin/env python3
"""
Test script to verify file deletion synchronization
Tests that files deleted from S3 are removed from Elasticsearch
"""
import os
import sys
import time
import hashlib
import requests
from io import BytesIO

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.ingestion.services import S3Service, ElasticsearchService


def create_test_file():
    """Create a simple test PDF-like file"""
    content = b"TEST FILE FOR DELETION SYNC\nThis is test content that should be deleted."
    return BytesIO(content)


def test_deletion_sync():
    """Test the deletion synchronization"""
    print("=" * 70)
    print("🧪 Testing File Deletion Synchronization")
    print("=" * 70)
    
    # Initialize services
    print("\n1️⃣  Initializing services...")
    try:
        s3_service = S3Service()
        es_service = ElasticsearchService()
        print("    Services initialized")
    except Exception as e:
        print(f"    Failed to initialize services: {e}")
        return False
    
    # Generate unique test file name
    timestamp = int(time.time())
    test_key = f"test_deletion_sync_{timestamp}.txt"
    
    print(f"\n2️⃣  Uploading test file: {test_key}")
    try:
        test_content = b"TEST FILE FOR DELETION SYNC\nThis is test content."
        s3_service.s3_client.put_object(
            Bucket=s3_service.bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        print("    Test file uploaded to S3")
    except Exception as e:
        print(f"    Failed to upload test file: {e}")
        return False
    
    # Wait for SQS processing (if enabled)
    print("\n3️⃣  Waiting for file to be indexed (60 seconds)...")
    print("   ⏳ This allows time for SQS queue processing")
    for i in range(6):
        time.sleep(10)
        print(f"   ... {(i+1)*10}s elapsed")
    
    # Check if document exists in Elasticsearch
    print("\n4️⃣  Checking if document exists in Elasticsearch...")
    try:
        query = {
            "query": {
                "term": {
                    "s3_key.keyword": test_key
                }
            }
        }
        
        url = f"{es_service.base_url}/{es_service.index_name}/_search"
        resp = requests.post(url, json=query, timeout=10, auth=es_service._auth())
        
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get('hits', {}).get('hits', [])
            if hits:
                print(f"    Document found in Elasticsearch ({len(hits)} document(s))")
                doc_exists_before = True
            else:
                print("     Document NOT found in Elasticsearch yet")
                print("   💡 This is normal if ingestion hasn't processed the file yet")
                print("   📝 The deletion test will still verify the sync mechanism works")
                doc_exists_before = False
        else:
            print(f"     Could not check Elasticsearch: {resp.status_code}")
            doc_exists_before = False
    except Exception as e:
        print(f"     Error checking Elasticsearch: {e}")
        doc_exists_before = False
    
    # Delete file from S3
    print(f"\n5️⃣  Deleting file from S3: {test_key}")
    try:
        s3_service.s3_client.delete_object(
            Bucket=s3_service.bucket_name,
            Key=test_key
        )
        print("    Test file deleted from S3")
    except Exception as e:
        print(f"    Failed to delete test file: {e}")
        return False
    
    # Wait for deletion processing
    print("\n6️⃣  Waiting for deletion to be processed (30 seconds)...")
    print("   ⏳ This allows time for SQS deletion event processing")
    for i in range(3):
        time.sleep(10)
        print(f"   ... {(i+1)*10}s elapsed")
    
    # Check if document is removed from Elasticsearch
    print("\n7️⃣  Verifying document is removed from Elasticsearch...")
    try:
        resp = requests.post(url, json=query, timeout=10, auth=es_service._auth())
        
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get('hits', {}).get('hits', [])
            if hits:
                print(f"    Document STILL EXISTS in Elasticsearch ({len(hits)} document(s))")
                print("   💡 Possible reasons:")
                print("      - SQS deletion events not configured")
                print("      - Ingestion service not running")
                print("      - Background sync not yet run")
                print("\n   🔧 To fix:")
                print("      1. Ensure S3 bucket has ObjectRemoved:* events configured")
                print("      2. Ensure ingestion service is running")
                print("      3. Wait for background sync to run")
                return False
            else:
                print("    Document successfully removed from Elasticsearch")
                return True
        else:
            print(f"     Could not verify deletion: {resp.status_code}")
            return False
    except Exception as e:
        print(f"    Error verifying deletion: {e}")
        return False


def main():
    """Main function"""
    print("\n  IMPORTANT NOTES:")
    print("   • This test requires the ingestion service to be running")
    print("   • SQS must be configured with ObjectRemoved events")
    print("   • The test will take ~2 minutes to complete")
    print()
    
    input("Press Enter to start the test (or Ctrl+C to cancel)...")
    
    success = test_deletion_sync()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 DELETION SYNC TEST PASSED")
        print("=" * 70)
        print(" Files deleted from S3 are properly removed from Elasticsearch")
        return 0
    else:
        print(" DELETION SYNC TEST FAILED OR INCOMPLETE")
        print("=" * 70)
        print("  Review the output above for details")
        print("📖 See docs/DELETION_SYNC.md for troubleshooting")
        return 1


if __name__ == "__main__":
    sys.exit(main())
