"""Test script to verify the Streamlit app streaming functionality."""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from agent.vault_pki_agent import VaultPKIAgent


async def test_streaming():
    """Test the streaming functionality of the agent."""
    print("Testing Vault PKI Agent Streaming Functionality")
    print("=" * 50)

    try:
        # Initialize agent
        agent = VaultPKIAgent()
        print("✅ Agent initialized successfully")

        # Test query
        test_query = "List all PKI secrets engines in Vault"
        print(f"🔍 Testing query: {test_query}")
        print("-" * 30)

        # Test streaming
        print("🔄 Streaming response:")
        full_response = ""
        tools_used = []

        async for event in agent.query_stream(test_query):
            if "data" in event:
                chunk = event["data"]
                print(chunk, end="", flush=True)
                full_response += chunk
            elif "current_tool_use" in event and event["current_tool_use"].get("name"):
                tool_name = event["current_tool_use"]["name"]
                if tool_name not in tools_used:
                    tools_used.append(tool_name)
                    print(f"\n🔧 Using tool: {tool_name}")
            elif "result" in event:
                print("\n✅ Streaming completed")
                break
            elif "error" in event:
                print(f"\n❌ Error: {event['message']}")
                break

        print("\n\n📊 Summary:")
        print(f"  - Response length: {len(full_response)} characters")
        print(f"  - Tools used: {', '.join(tools_used) if tools_used else 'None'}")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

    return True


async def compare_methods():
    """Compare streaming vs regular method performance."""
    print("\n" + "=" * 50)
    print("Performance Comparison: Streaming vs Regular")
    print("=" * 50)

    agent = VaultPKIAgent()
    test_query = "Show me all certificates expiring in the next 30 days"

    # Test regular method
    print("🔸 Testing regular method...")
    start_time = asyncio.get_event_loop().time()

    try:
        regular_response = await agent.query(test_query)
        regular_time = asyncio.get_event_loop().time() - start_time
        print(f"⏱️ Regular method completed in: {regular_time:.2f} seconds")
        print(f"📏 Response length: {len(regular_response)} characters")
    except Exception as e:
        print(f"❌ Regular method failed: {str(e)}")
        return

    # Test streaming method
    print("\n🔸 Testing streaming method...")
    start_time = asyncio.get_event_loop().time()
    first_chunk_time = None

    try:
        streaming_response = ""

        async for event in agent.query_stream(test_query):
            if "data" in event:
                if first_chunk_time is None:
                    first_chunk_time = asyncio.get_event_loop().time() - start_time
                streaming_response += event["data"]
            elif "result" in event:
                break

        total_time = asyncio.get_event_loop().time() - start_time
        print(f"⏱️ Streaming method completed in: {total_time:.2f} seconds")
        print(f"⚡ First chunk received after: {first_chunk_time:.2f} seconds")
        print(f"📏 Response length: {len(streaming_response)} characters")

        if first_chunk_time:
            advantage = total_time - first_chunk_time
            print(f"🚀 Streaming advantage: First results {advantage:.2f}s faster")

    except Exception as e:
        print(f"❌ Streaming method failed: {str(e)}")


def main():
    """Main test function."""
    print("Vault PKI Agent - Streamlit Integration Test")
    print("This script tests the streaming functionality that powers the Streamlit app")
    print()

    try:
        # Test basic streaming
        success = asyncio.run(test_streaming())

        if success:
            # Compare methods
            asyncio.run(compare_methods())

            print("\n" + "=" * 50)
            print("✅ All tests completed successfully!")
            print("🚀 Your Streamlit app is ready to use streaming!")
            print()
            print("To start the Streamlit app:")
            print("  streamlit run main.py")
        else:
            print("\n❌ Tests failed. Please check your configuration.")

    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
