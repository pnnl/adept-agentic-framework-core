#!/usr/bin/env python3
"""
Test LangChain ChatOpenAI with internal LLM to diagnose 403 errors.
This mimics exactly what the application does.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


async def test_chatopen_ai():
    """Test ChatOpenAI with internal LLM configuration."""

    api_key = os.getenv("INTERNAL_LLM_API_KEY")
    base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    model = os.getenv("INTERNAL_LLM_MODEL")

    print("=" * 60)
    print("LangChain ChatOpenAI Internal LLM Test")
    print("=" * 60)

    if not all([api_key, base_url, model]):
        print("❌ Missing required environment variables")
        sys.exit(1)

    print(f"\n📋 Configuration:")
    print(f"   Base URL: {base_url}")
    print(f"   Model: {model}")
    print(f"   API Key (first 8): {api_key[:8]}...")

    # Test 1: Basic ChatOpenAI with just api_key and base_url
    print(f"\n" + "=" * 60)
    print("Test 1: ChatOpenAI with api_key + base_url")
    print("=" * 60)
    try:
        llm1 = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        print(f"✅ ChatOpenAI instance created")
        print(f"   Model: {llm1.model_name}")
        print(f"   OpenAI API Base: {llm1.openai_api_base}")

        print(f"\n   Making API call...")
        response = await llm1.ainvoke([HumanMessage(content="Hello, test")])
        print(f"✅ SUCCESS! Response: {response.content[:100]}...")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {str(e)[:200]}...")
        import traceback

        traceback.print_exc()

    # Test 2: ChatOpenAI with default_headers (might cause conflict)
    print(f"\n" + "=" * 60)
    print("Test 2: ChatOpenAI with api_key + base_url + default_headers")
    print("=" * 60)
    try:
        llm2 = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            default_headers={"Authorization": f"Bearer {api_key}"},
        )
        print(f"✅ ChatOpenAI instance created")
        print(f"   Model: {llm2.model_name}")
        print(f"   OpenAI API Base: {llm2.openai_api_base}")

        print(f"\n   Making API call...")
        response = await llm2.ainvoke([HumanMessage(content="Hello, test")])
        print(f"✅ SUCCESS! Response: {response.content[:100]}...")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {str(e)[:200]}...")
        print(f"   This might indicate duplicate Authorization headers")
        import traceback

        traceback.print_exc()

    # Test 3: Debug the actual URL being called
    print(f"\n" + "=" * 60)
    print("Test 3: Inspecting LangChain's URL construction")
    print("=" * 60)
    llm3 = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    print(f"   Model: {llm3.model_name}")
    print(f"   Base URL: {llm3.openai_api_base}")


if __name__ == "__main__":
    asyncio.run(test_chatopen_ai())
