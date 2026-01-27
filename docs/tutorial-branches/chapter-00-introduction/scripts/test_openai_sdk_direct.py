#!/usr/bin/env python3
"""
Test script based on official internal LLM documentation.
This should work identically locally and in Docker.

Based on the official example from internal docs.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import openai

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def test_chat_completion():
    """Test chat completion using OpenAI SDK directly."""

    # Get configuration from environment
    api_key = os.getenv("INTERNAL_LLM_API_KEY")
    base_url = os.getenv("INTERNAL_LLM_BASE_URL", "https://ai-incubator-api.pnnl.gov")
    model = os.getenv("INTERNAL_LLM_MODEL", "gpt-4o-birthright")

    print("=" * 70)
    print("OpenAI SDK Direct Test (Official Pattern)")
    print("=" * 70)

    if not api_key:
        print("❌ INTERNAL_LLM_API_KEY not set")
        return False

    print(f"\n📋 Configuration:")
    print(f"   Base URL: {base_url}")
    print(f"   Model: {model}")
    print(f"   API Key: {api_key[:8]}...{api_key[-4:]}")

    # Initialize client exactly as shown in official docs
    print("\n🔧 Initializing OpenAI client...")
    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        print("✅ Client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False

    # Test chat completion
    print("\n💬 Testing chat completion...")
    user_message = (
        "Hello! Please respond with 'Connection successful' if you can read this."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
            max_tokens=50,
        )

        print("✅ Chat completion successful!")
        print(f"\n📤 Request: {user_message}")
        print(f"📥 Response: {response.choices[0].message.content}")
        print(f"\n📊 Usage:")
        print(f"   - Prompt tokens: {response.usage.prompt_tokens}")
        print(f"   - Completion tokens: {response.usage.completion_tokens}")
        print(f"   - Total tokens: {response.usage.total_tokens}")

        return True

    except openai.AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print(
            f"   Check that your API key is valid and has permissions for model '{model}'"
        )
        return False
    except openai.NotFoundError as e:
        print(f"❌ Model not found: {e}")
        print(f"   Check that model '{model}' exists and is accessible")
        return False
    except openai.PermissionDeniedError as e:
        print(f"❌ Permission denied (403): {e}")
        print(f"   This may indicate:")
        print(f"   1. API key lacks permissions for this model")
        print(f"   2. IP address not whitelisted (likely in Docker)")
        print(f"   3. Model name is incorrect")
        return False
    except openai.APIConnectionError as e:
        print(f"❌ Connection error: {e}")
        print(f"   Cannot reach {base_url}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_embeddings():
    """Test embeddings using OpenAI SDK directly."""

    # Get configuration from environment
    api_key = os.getenv("INTERNAL_LLM_API_KEY")
    base_url = os.getenv("INTERNAL_LLM_BASE_URL", "https://ai-incubator-api.pnnl.gov")
    embedding_model = os.getenv(
        "INTERNAL_LLM_EMBEDDING_MODEL", "text-embedding-3-small-birthright"
    )

    print("\n" + "=" * 70)
    print("Testing Embeddings")
    print("=" * 70)

    if not api_key:
        print("❌ INTERNAL_LLM_API_KEY not set")
        return False

    print(f"\n📋 Configuration:")
    print(f"   Base URL: {base_url}")
    print(f"   Embedding Model: {embedding_model}")

    # Initialize client
    print("\n🔧 Initializing OpenAI client...")
    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        print("✅ Client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False

    # Test embeddings
    print("\n🔢 Testing embeddings...")
    test_text = "This is a test sentence for embeddings."

    try:
        embedding_response = client.embeddings.create(
            input=test_text, model=embedding_model
        )

        print("✅ Embedding successful!")
        print(f"\n📤 Input: {test_text}")
        print(
            f"📥 Embedding vector length: {len(embedding_response.data[0].embedding)}"
        )
        print(f"📊 First 5 values: {embedding_response.data[0].embedding[:5]}")

        return True

    except openai.AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except openai.NotFoundError as e:
        print(f"❌ Model not found: {e}")
        print(f"   Check that embedding model '{embedding_model}' exists")
        return False
    except openai.PermissionDeniedError as e:
        print(f"❌ Permission denied (403): {e}")
        print(f"   IP address may not be whitelisted (Docker issue)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("INTERNAL LLM SANITY CHECK (Official Pattern)")
    print("=" * 70)
    print(f"Running from: {os.getcwd()}")

    # Check environment
    in_docker = os.path.exists("/.dockerenv")
    print(f"Environment: {'🐳 Docker Container' if in_docker else '💻 Local Machine'}")

    # Run tests
    chat_success = test_chat_completion()
    embeddings_success = test_embeddings()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Chat Completion: {'✅ PASS' if chat_success else '❌ FAIL'}")
    print(f"Embeddings:      {'✅ PASS' if embeddings_success else '❌ FAIL'}")
    print("=" * 70)

    if chat_success and embeddings_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed. See details above.")
        if in_docker:
            print("\n💡 If tests work locally but fail in Docker:")
            print("   - This indicates an IP whitelisting issue")
            print("   - Contact your internal API admins to whitelist Docker IPs")
            print(
                "   - Or use host networking: network_mode: 'host' (not recommended on macOS)"
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
