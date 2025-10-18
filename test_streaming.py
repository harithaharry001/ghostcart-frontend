#!/usr/bin/env python3
"""
Test script for streaming chat endpoint.

Usage:
    python test_streaming.py "Find me AirPods under $200"
"""
import requests
import sys
import json

def test_streaming_chat(message: str):
    """Test the streaming chat endpoint."""

    url = "http://localhost:8000/api/chat/stream"
    params = {
        "message": message,
        "user_id": "user_demo_001"
    }

    print(f"📨 Sending message: {message}")
    print(f"🔗 Connecting to: {url}")
    print("=" * 70)

    try:
        # Stream response
        response = requests.post(url, params=params, stream=True, timeout=60)

        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return

        # Process SSE stream
        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')

            # Parse SSE format
            if line.startswith('event:'):
                event_type = line.split(':', 1)[1].strip()
                print(f"\n📡 Event: {event_type}")

            elif line.startswith('data:'):
                data_json = line.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_json)

                    # Handle different event types
                    if event_type == 'connected':
                        print(f"   ✅ Connected! Session: {data.get('session_id')}")

                    elif event_type == 'agent_thinking':
                        print(f"   🤔 {data.get('message')}")

                    elif event_type == 'agent_chunk':
                        # Print text chunks as they arrive
                        print(data.get('text', ''), end='', flush=True)

                    elif event_type == 'tool_use':
                        print(f"\n   🔧 Tool: {data.get('tool_name')}")
                        print(f"      Input: {data.get('tool_input')}")

                    elif event_type == 'complete':
                        print(f"\n\n   ✅ Complete!")
                        print(f"      Session: {data.get('session_id')}")
                        print(f"      Flow: {data.get('flow_type')}")
                        print(f"      Response length: {len(data.get('response', ''))}")

                    elif event_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")

                except json.JSONDecodeError:
                    print(f"   Data: {data_json}")

        print("\n" + "=" * 70)
        print("✅ Stream complete")

    except requests.exceptions.Timeout:
        print("❌ Timeout - server took too long to respond")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the server running?")
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_streaming.py \"Your message here\"")
        print("\nExample:")
        print('  python test_streaming.py "Find me AirPods under $200"')
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    test_streaming_chat(message)
