
#!/usr/bin/env python3
"""StackSense + OpenAI API Test"""
import os
import sys
import pytest


if not os.getenv("OPENAI_API_KEY"):
    pytest.skip("OPENAI_API_KEY not set; skipping OpenAI integration test", allow_module_level=True)

print("=" * 60)
print("🤖 StackSense + OpenAI API Test")
print("=" * 60)

# Check for API key
print("\n1️⃣  Checking for OpenAI API key...")
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("   ❌ OPENAI_API_KEY not found!")
    print("\n   Set it with:")
    print("   export OPENAI_API_KEY='sk-proj-your-key-here'")
    sys.exit(1)

print(f"   ✅ API key found: {api_key[:15]}...{api_key[-4:]}")

# Import OpenAI
print("\n2️⃣  Importing OpenAI SDK...")
try:
    import openai
    print(f"   ✅ OpenAI SDK imported")
except ImportError:
    print("   ❌ OpenAI not installed!")
    print("   Install: pip install openai")
    sys.exit(1)

# Initialize StackSense
print("\n3️⃣  Initializing StackSense...")
os.environ["STACKSENSE_ENABLE_DB"] = "false"

from stacksense import StackSense

ss = StackSense(
    project_id="openai-test",
    environment="development",
    debug=True
)
print("   ✅ StackSense initialized")

# Wrap OpenAI client
print("\n4️⃣  Wrapping OpenAI client with monitoring...")
client = ss.monitor(openai.OpenAI(api_key=api_key))
print("   ✅ Client wrapped - API calls will be tracked!")

# Make API call
print("\n5️⃣  Making API call to GPT-3.5-Turbo...")
print("   Asking: 'Say hello in exactly 5 words'")

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Say hello in exactly 5 words"}
        ],
        max_tokens=50
    )
    
    answer = response.choices[0].message.content
    tokens = response.usage.total_tokens
    
    print(f"\n   🤖 GPT-3.5: {answer}")
    print(f"   📊 Tokens: {tokens}")
    print("   ✅ API call successful!")
    
except Exception as e:
    print(f"\n   ❌ API call failed: {e}")
    sys.exit(1)

# Second API call
print("\n6️⃣  Making second API call...")
print("   Asking: 'What is 2+2? Just the number.'")

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "What is 2+2? Answer with just the number."}
        ],
        max_tokens=10
    )
    
    answer = response.choices[0].message.content
    
    print(f"\n   🤖 GPT-3.5: {answer}")
    print("   ✅ Second call successful!")
    
except Exception as e:
    print(f"\n   ❌ Second call failed: {e}")

# Get metrics
print("\n7️⃣  Viewing StackSense metrics...")
metrics = ss.get_metrics()

print(f"""
   📊 StackSense Tracked:
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Total Calls:      {metrics['total_calls']}
   Total Tokens:     {metrics['total_tokens']:,}
   Total Cost:       ${metrics['total_cost']:.6f}
   Avg Cost/Call:    ${metrics['avg_cost_per_call']:.6f}
   Avg Latency:      {metrics['avg_latency']:.0f}ms
   Error Rate:       {metrics['error_rate']:.1f}%
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

# View events
print("\n8️⃣  Recent events:")
events = ss.tracker.get_events()

for i, event in enumerate(events, 1):
    print(f"""
   Call {i}:
      Model:    {event.get('model', 'N/A')}
      Tokens:   {event.get('total_tokens', 0)} (in: {event.get('tokens', {}).get('input', 0)}, out: {event.get('tokens', {}).get('output', 0)})
      Cost:     ${event.get('cost', 0):.6f}
      Latency:  {event.get('latency', 0):.0f}ms
    """)

print("=" * 60)
print("🎉 OPENAI TEST COMPLETE!")
print("=" * 60)
print(f"""
✅ Successfully tracked {metrics['total_calls']} real OpenAI API calls!
💰 Total cost: ${metrics['total_cost']:.6f}
⚡ Avg latency: {metrics['avg_latency']:.0f}ms

🚀 StackSense is working perfectly with OpenAI!
""")
print("=" * 60)
