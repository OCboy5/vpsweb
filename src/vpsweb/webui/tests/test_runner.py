#!/usr/bin/env python3
"""
Simple API Test Runner for VPSWeb Repository Web UI

Quick test runner to verify API endpoints are working correctly.
"""

import sys
import requests
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


def test_api_endpoints():
    """Test basic API endpoints"""
    base_url = "http://localhost:8000"

    print("🧪 Testing VPSWeb API Endpoints")
    print("=" * 50)

    # Test health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Status: {response.json()['status']}")
            print(f"   Version: {response.json()['version']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        print("   Make sure the server is running: python -m src.vpsweb.webui.main")
        return False

    # Test poems endpoint
    try:
        response = requests.get(f"{base_url}/api/v1/poems/", timeout=5)
        if response.status_code == 200:
            print("✅ Poems list endpoint works")
            poems = response.json()
            print(f"   Found {len(poems)} poems")
        else:
            print(f"❌ Poems endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Poems endpoint failed: {e}")

    # Test creating a poem
    try:
        poem_data = {
            "poet_name": "Test Poet",
            "poem_title": "Test Poem for API",
            "source_language": "English",
            "original_text": "This is a test poem created via API.",
        }

        response = requests.post(f"{base_url}/api/v1/poems/", json=poem_data, timeout=5)
        if response.status_code == 200:
            print("✅ Create poem endpoint works")
            poem = response.json()
            poem_id = poem["id"]
            print(f"   Created poem ID: {poem_id}")

            # Test getting the poem
            response = requests.get(f"{base_url}/api/v1/poems/{poem_id}", timeout=5)
            if response.status_code == 200:
                print("✅ Get poem by ID works")
            else:
                print(f"❌ Get poem failed: {response.status_code}")

        else:
            print(f"❌ Create poem failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"❌ Create poem failed: {e}")

    # Test statistics endpoint
    try:
        response = requests.get(f"{base_url}/api/v1/statistics/overview", timeout=5)
        if response.status_code == 200:
            print("✅ Statistics overview works")
            stats = response.json()
            print(f"   Total poems: {stats.get('total_poems', 0)}")
            print(f"   Total translations: {stats.get('total_translations', 0)}")
        else:
            print(f"❌ Statistics endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Statistics endpoint failed: {e}")

    # Test API docs
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API documentation accessible")
        else:
            print(f"❌ API docs failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API docs failed: {e}")

    print("\n" + "=" * 50)
    print("🎉 API Tests Complete!")
    print("\n📚 API Documentation: http://localhost:8000/docs")
    print("🔧 Interactive API: http://localhost:8000/redoc")
    print("📊 Repository: http://localhost:8000")

    return True


if __name__ == "__main__":
    print("🚀 Starting VPSWeb API Tests...")
    print("Make sure the server is running:")
    print("   python -m src.vpsweb.webui.main")
    print()

    success = test_api_endpoints()
    sys.exit(0 if success else 1)
