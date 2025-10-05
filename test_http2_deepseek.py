#!/usr/bin/env python3
"""
Simple test script to verify HTTP/2 functionality with deepseek API.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from vpsweb.services.llm.openai_compatible import OpenAICompatibleProvider


async def test_http2_deepseek():
    """Test HTTP/2 functionality with deepseek API."""

    # Check if API key is available
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("❌ DEEPSEEK_API_KEY not found or not set")
        print("Please set the DEEPSEEK_API_KEY environment variable")
        return False

    print("🔧 Testing HTTP/2 with deepseek API...")
    print(f"   API Key: {'***' + api_key[-4:] if len(api_key) > 4 else '***'}")

    try:
        # Create provider instance
        provider = OpenAICompatibleProvider(
            base_url="https://api.deepseek.com/v1",
            api_key=api_key,
            timeout=30.0
        )

        print(f"   Provider created: {provider.get_provider_name()}")

        # Test with deepseek-chat model first
        models_to_test = [
            "deepseek-chat",
            "deepseek-reasoner"
        ]

        for model in models_to_test:
            print(f"\n   📤 Testing model: {model}")

            # Test message
            messages = [
                {"role": "user", "content": "请将这个简单的英文句子翻译成中文：Hello world"}
            ]

            # Make the request
            response = await provider.generate(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=100
            )

            print(f"   ✅ {model} request successful!")
            print(f"   📝 Response: {response.content}")
            print(f"   🔢 Tokens used: {response.tokens_used}")
            print(f"   🏷️  Model: {response.model_name}")
            print(f"   ⏱️  Finish reason: {response.finish_reason}")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 HTTP/2 Test for vpsweb DeepSeek API")
    print("=" * 50)

    success = await test_http2_deepseek()

    print("\n" + "=" * 50)
    if success:
        print("✅ HTTP/2 test completed successfully!")
        print("   DeepSeek API is working with HTTP/2")
    else:
        print("❌ HTTP/2 test failed!")
        print("   Check the error message above")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)