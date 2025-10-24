# Vault PKI Agent - Streaming Implementation

This document explains the streaming capabilities added to the Vault PKI Agent using AWS Strands Agent SDK's `stream_async` method.

## Overview

The `VaultPKIAgent` now supports two query methods:

1. **`query(user_prompt: str) -> str`** - Regular method that returns the complete response
2. **`query_stream(user_prompt: str) -> AsyncIterator[Dict[str, Any]]`** - Streaming method that yields events in real-time

## Streaming Method Benefits

- **Real-time feedback**: See responses as they're generated
- **Tool visibility**: Monitor which tools are being used
- **Better UX**: Responsive interfaces that don't appear frozen
- **Error handling**: Early detection of issues during processing

## Event Types

The streaming method yields various event types based on the Strands Agent SDK:

### Lifecycle Events
- `init_event_loop`: True when event loop initializes
- `start_event_loop`: True when event loop cycle starts
- `complete`: True when a cycle completes
- `result`: Contains final AgentResult

### Text Generation Events
- `data`: Text chunks from the model's output (stream these to user)
- `delta`: Raw delta content from the model

### Tool Events
- `current_tool_use`: Information about tools being used:
  - `name`: Tool name (e.g., "list_certificates")
  - `input`: Tool input parameters
  - `toolUseId`: Unique identifier

### Error Events
- `error`: Custom error event format
- `message`: Error message text

## Usage Examples

### Basic Streaming
```python
agent = VaultPKIAgent()

async for event in agent.query_stream("List all PKI secrets engines"):
    if "data" in event:
        print(event["data"], end="")  # Stream text output
    elif "current_tool_use" in event:
        tool_name = event["current_tool_use"].get("name")
        if tool_name:
            print(f"\\n🔧 Using tool: {tool_name}")
    elif "result" in event:
        print("\\n✅ Query completed")
```

### Advanced Event Handling
```python
agent = VaultPKIAgent()
full_response = ""

async for event in agent.query_stream("Show certificates expiring in 30 days"):
    # Lifecycle tracking
    if event.get("init_event_loop"):
        print("🔄 Initializing...")
    elif event.get("start_event_loop"):
        print("▶️ Starting processing...")
    
    # Text streaming
    elif "data" in event:
        text_chunk = event["data"]
        print(text_chunk, end="", flush=True)
        full_response += text_chunk
    
    # Tool monitoring
    elif "current_tool_use" in event:
        tool_info = event["current_tool_use"]
        tool_name = tool_info.get("name")
        tool_input = tool_info.get("input", {})
        
        if tool_name:
            print(f"\\n🔧 Using {tool_name}")
            if tool_input:
                print(f"   Input: {tool_input}")
    
    # Completion
    elif event.get("complete"):
        print("\\n✅ Cycle completed")
    elif "result" in event:
        print("\\n🎯 Final result received")
    
    # Error handling
    elif "error" in event:
        print(f"\\n❌ Error: {event['message']}")
        break

print(f"\\nFull response: {full_response}")
```

### Web Application Integration

For web applications using FastAPI or similar:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/query-stream")
async def query_stream_endpoint(query: str):
    agent = VaultPKIAgent()
    
    async def generate_response():
        async for event in agent.query_stream(query):
            if "data" in event:
                # Send text chunks as Server-Sent Events
                yield f"data: {event['data']}\\n\\n"
            elif "current_tool_use" in event and event["current_tool_use"].get("name"):
                # Send tool usage information
                tool_name = event["current_tool_use"]["name"]
                yield f"event: tool\\ndata: Using {tool_name}\\n\\n"
            elif "result" in event:
                yield f"event: complete\\ndata: Query completed\\n\\n"
    
    return StreamingResponse(
        generate_response(), 
        media_type="text/event-stream"
    )
```

### Real-time Chat Interface

```python
async def chat_with_streaming(user_input: str):
    agent = VaultPKIAgent()
    
    print(f"User: {user_input}")
    print("Agent: ", end="")
    
    async for event in agent.query_stream(user_input):
        if "data" in event:
            print(event["data"], end="", flush=True)
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            tool_name = event["current_tool_use"]["name"]
            print(f" [Using {tool_name}] ", end="")
    
    print()  # New line after complete response
```

## Error Handling

The streaming method includes robust error handling:

```python
async for event in agent.query_stream(user_prompt):
    if "error" in event:
        # Handle custom error events
        print(f"Error: {event['message']}")
        break
    # ... handle other events
```

## Performance Considerations

- **First Response Time**: Streaming typically shows first results faster than waiting for complete response
- **Memory Usage**: Events are processed one at a time, reducing memory footprint
- **User Experience**: Users see immediate feedback instead of waiting for complete processing

## Testing

Run the examples:

```bash
# Test the main agent file
python src/agent/vault_pki_agent.py

# Run comprehensive streaming examples
python examples/streaming_example.py
```

## Implementation Details

The streaming implementation:
1. Creates the same agent configuration as the regular method
2. Uses `agent.stream_async()` instead of `agent.invoke_async()`
3. Yields each event directly to the caller
4. Includes error handling in the event stream format

This approach provides maximum flexibility while maintaining compatibility with the existing agent architecture.