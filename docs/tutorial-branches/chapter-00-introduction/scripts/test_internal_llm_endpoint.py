#!/usr/bin/env python3
"""
Test script to validate internal LLM endpoint authentication.
This script helps debug 403 Forbidden errors by showing exactly what's being sent.
"""

import os
import sys
from pathlib import Path
import httpx
import json
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def test_internal_llm():
    """Test the internal LLM endpoint with minimal request."""

    # Get credentials from environment
    api_key = os.getenv("INTERNAL_LLM_API_KEY")
    base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    model = os.getenv("INTERNAL_LLM_MODEL")

    print("=" * 60)
    print("Internal LLM Endpoint Test")
    print("=" * 60)

    if not all([api_key, base_url, model]):
        print("❌ Missing required environment variables:")
        print(f"   INTERNAL_LLM_API_KEY: {'✓' if api_key else '✗'}")
        print(f"   INTERNAL_LLM_BASE_URL: {'✓' if base_url else '✗'}")
        print(f"   INTERNAL_LLM_MODEL: {'✓' if model else '✗'}")
        sys.exit(1)

    print(f"\n📋 Configuration:")
    print(f"   Base URL: {base_url}")
    print(f"   Model: {model}")
    print(f"   API Key (first 8 chars): {api_key[:8]}...")

    # Construct the full endpoint URL
    # OpenAI-compatible endpoints typically use /v1/chat/completions or /chat/completions
    test_urls = [
        f"{base_url}/chat/completions",
        f"{base_url}/v1/chat/completions",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello, this is a test."}],
        "max_tokens": 10,
    }

    print(f"\n📤 Request Headers:")
    print(f"   Authorization: Bearer {api_key[:8]}...{api_key[-4:]}")
    print(f"   Content-Type: application/json")

    print(f"\n📦 Request Payload:")
    print(f"   {json.dumps(payload, indent=2)}")

    # Try each possible endpoint
    for url in test_urls:
        print(f"\n🔍 Testing endpoint: {url}")
        print("-" * 60)

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

                print(f"   Status Code: {response.status_code}")
                print(f"   Response Headers:")
                for key, value in response.headers.items():
                    print(f"      {key}: {value}")

                print(f"\n   Response Body:")
                try:
                    print(f"      {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"      {response.text[:500]}")

                if response.status_code == 200:
                    print(f"\n✅ SUCCESS! Endpoint is working.")
                    return True
                elif response.status_code == 403:
                    print(f"\n❌ 403 Forbidden - Authentication issue")
                    print(f"   Possible causes:")
                    print(f"   1. Invalid API key")
                    print(f"   2. API key lacks permissions for this model")
                    print(f"   3. IP address not whitelisted")
                    print(f"   4. Authentication method incorrect (Bearer vs API-Key)")
                elif response.status_code == 404:
                    print(f"\n❌ 404 Not Found - Wrong endpoint URL")
                    continue  # Try next URL
                else:
                    print(f"\n⚠️  Unexpected status code")

        except httpx.ConnectError as e:
            print(f"   ❌ Connection Error: {e}")
        except httpx.TimeoutException as e:
            print(f"   ❌ Timeout: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n" + "=" * 60)
    print("❌ All endpoints failed. Check configuration and permissions.")
    print("=" * 60)
    return False


if __name__ == "__main__":
    success = test_internal_llm()
    sys.exit(0 if success else 1)
