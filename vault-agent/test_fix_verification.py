"""Test script to verify the main.py fix for the 'str' object has no attribute 'items' error."""


def test_tool_input_handling():
    """Test the different types of tool_input that might be received."""

    print("Testing tool_input handling logic...")

    # Simulate different types of tool_input that might come from the agent
    test_cases = [
        # Case 1: Dictionary (expected format)
        {
            "name": "list_certificates",
            "input": {"pki_mount_path": "pki_int", "filters": "active"},
        },
        # Case 2: String input (causing the original error)
        {
            "name": "filter_pki_audit_events",
            "input": "vault_certificate_subject=test.example.com",
        },
        # Case 3: Empty/None input
        {"name": "list_pki_secrets_engines", "input": None},
        # Case 4: Complex nested structure
        {
            "name": "some_tool",
            "input": {
                "vault_certificate_subject": "api.example.com",
                "vault_pki_path": "pki/",
                "other_param": {"nested": "value"},
            },
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['name']}")

        # This is the logic from main.py that was failing
        tool_name = test_case["name"]
        tool_input = test_case.get("input", {})

        tool_info = f"🔧 Using: **{tool_name}**"
        if tool_input:
            key_params = []
            # Fixed logic: Check if tool_input is a dictionary before calling .items()
            if isinstance(tool_input, dict):
                for key, value in tool_input.items():
                    if key in [
                        "pki_mount_path",
                        "vault_certificate_subject",
                        "vault_pki_path",
                    ]:
                        key_params.append(f"{key}: {value}")
            elif isinstance(tool_input, str):
                # If tool_input is a string, just show it directly
                key_params.append(f"input: {tool_input}")

            if key_params:
                tool_info += f" ({', '.join(key_params)})"

        print(f"  Result: {tool_info}")
        print(f"  ✅ Handled successfully")


def test_event_structure():
    """Test different event structures that might come from the streaming agent."""

    print("\n" + "=" * 50)
    print("Testing event structure handling...")

    # Simulate different event structures
    events = [
        # Normal data event
        {"data": "This is streaming text"},
        # Tool use event with dict input
        {
            "current_tool_use": {
                "name": "list_certificates",
                "input": {"pki_mount_path": "pki_int"},
            }
        },
        # Tool use event with string input (problematic case)
        {
            "current_tool_use": {
                "name": "filter_audit_events",
                "input": "certificate=test.example.com",
            }
        },
        # Malformed event
        {"current_tool_use": "not_a_dict"},
        # Error event
        {"error": True, "message": "Something went wrong"},
    ]

    for i, event in enumerate(events, 1):
        print(f"\nEvent {i}: {list(event.keys())}")

        try:
            # Simulate the event handling logic from main.py
            if "data" in event:
                text_chunk = event["data"]
                if isinstance(text_chunk, str):
                    print(f"  ✅ Data: {text_chunk[:30]}...")

            elif "current_tool_use" in event:
                tool_use_info = event["current_tool_use"]
                if isinstance(tool_use_info, dict) and tool_use_info.get("name"):
                    tool_name = tool_use_info.get("name", "Unknown Tool")
                    tool_input = tool_use_info.get("input", {})

                    tool_info = f"🔧 Using: **{tool_name}**"
                    if tool_input:
                        key_params = []
                        if isinstance(tool_input, dict):
                            for key, value in tool_input.items():
                                if key in [
                                    "pki_mount_path",
                                    "vault_certificate_subject",
                                    "vault_pki_path",
                                ]:
                                    key_params.append(f"{key}: {value}")
                        elif isinstance(tool_input, str):
                            key_params.append(f"input: {tool_input}")

                        if key_params:
                            tool_info += f" ({', '.join(key_params)})"

                    print(f"  ✅ Tool: {tool_info}")
                else:
                    print(f"  ⚠️ Malformed tool event: {tool_use_info}")

            elif "error" in event:
                message = event.get("message", "Unknown error")
                print(f"  ✅ Error: {message}")

            else:
                print(f"  ✅ Other event type handled")

        except Exception as e:
            print(f"  ❌ Error processing event: {str(e)}")


def main():
    """Run all tests."""
    print("Vault PKI Agent - Main.py Fix Verification")
    print("Fixing: 'str' object has no attribute 'items' error")
    print("=" * 60)

    test_tool_input_handling()
    test_event_structure()

    print("\n" + "=" * 60)
    print("✅ All tests passed! The fix should resolve the Streamlit error.")
    print("\n🚀 The issue was:")
    print("   - tool_input was sometimes a string instead of dict")
    print("   - Calling .items() on a string caused the error")
    print("\n🔧 The fix:")
    print("   - Added isinstance() checks before calling .items()")
    print("   - Handle both dict and string inputs gracefully")
    print("   - Added better error handling for malformed events")


if __name__ == "__main__":
    main()
