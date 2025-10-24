"""Example demonstrating streaming capabilities of the Vault PKI Agent."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from agent.vault_pki_agent import VaultPKIAgent


async def streaming_example():
    """Example showing how to use the streaming query method."""

    # Load environment variables
    load_dotenv()

    # Initialize the agent
    agent = VaultPKIAgent()

    # Example queries to test streaming
    queries = [
        "List all PKI secrets engines in Vault",
        "Show me all certificates expiring in the next 30 days",
        "Find any revoked certificates",
        "Who issued the certificate test.example.com",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 60}")
        print(f"Query {i}: {query}")
        print("=" * 60)

        # Process streaming response
        try:
            full_response = ""
            async for event in agent.query_stream(query):
                # Handle different event types based on Strands Agent SDK documentation

                if "init_event_loop" in event and event["init_event_loop"]:
                    print("🔄 Event loop initialized")

                elif "start_event_loop" in event and event["start_event_loop"]:
                    print("▶️ Event loop cycle starting")

                elif "data" in event:
                    # Stream text output in real-time
                    text_chunk = event["data"]
                    print(text_chunk, end="", flush=True)
                    full_response += text_chunk

                elif "current_tool_use" in event and event["current_tool_use"].get(
                    "name"
                ):
                    # Show tool usage
                    tool_name = event["current_tool_use"]["name"]
                    tool_input = event["current_tool_use"].get("input", {})
                    print(f"\n🔧 Using tool: {tool_name}")
                    if tool_input:
                        print(f"   Input: {tool_input}")

                elif "complete" in event and event["complete"]:
                    print("\n✅ Cycle completed")

                elif "result" in event:
                    print("\n🎯 Final result received")

                elif "error" in event:
                    print(f"\n❌ Error: {event['message']}")
                    break

            print(f"\n\n📝 Full Response Length: {len(full_response)} characters")

        except Exception as e:
            print(f"\n❌ Exception occurred: {str(e)}")

        # Wait a bit between queries for better readability
        if i < len(queries):
            await asyncio.sleep(1)


async def compare_methods():
    """Compare regular query vs streaming query methods."""

    print("\n" + "=" * 80)
    print("COMPARISON: Regular Query vs Streaming Query")
    print("=" * 80)

    load_dotenv()
    agent = VaultPKIAgent()

    query = "List all PKI secrets engines in Vault"

    # Test regular query method
    print("\n🔸 Regular Query Method:")
    print("-" * 40)
    start_time = asyncio.get_event_loop().time()

    try:
        regular_response = await agent.query(query)
        regular_time = asyncio.get_event_loop().time() - start_time
        print(f"Response: {regular_response}")
        print(f"⏱️ Time taken: {regular_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Error in regular query: {str(e)}")

    # Test streaming query method
    print("\n🔸 Streaming Query Method:")
    print("-" * 40)
    start_time = asyncio.get_event_loop().time()

    try:
        streaming_response = ""
        first_chunk_time = None

        async for event in agent.query_stream(query):
            if "data" in event:
                if first_chunk_time is None:
                    first_chunk_time = asyncio.get_event_loop().time() - start_time
                    print(
                        f"⚡ First chunk received after: {first_chunk_time:.2f} seconds"
                    )

                chunk = event["data"]
                print(chunk, end="", flush=True)
                streaming_response += chunk
            elif "result" in event:
                break

        total_streaming_time = asyncio.get_event_loop().time() - start_time
        print(f"\n⏱️ Total streaming time: {total_streaming_time:.2f} seconds")

        if first_chunk_time:
            print(
                f"📊 Advantage: Streaming showed first results {total_streaming_time - first_chunk_time:.2f}s faster"
            )

    except Exception as e:
        print(f"❌ Error in streaming query: {str(e)}")


async def main():
    """Main function to run examples."""

    print("Vault PKI Agent - Streaming Examples")
    print("=" * 50)

    try:
        # Run streaming example
        await streaming_example()

        # Compare methods
        await compare_methods()

    except KeyboardInterrupt:
        print("\n\n⏹️ Stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
