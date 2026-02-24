
"""
Simple StackSense Test - No API Keys Required
"""

import os

# Disable database for simplicity (uses in-memory storage)
os.environ["STACKSENSE_ENABLE_DB"] = "false"

print("=" * 60)
print("🧪 StackSense Simple Test")
print("=" * 60)

# Step 1: Import StackSense
print("\n1️⃣  Importing StackSense...")
try:
    from stacksense import StackSense
    print("   ✅ Import successful!")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Step 2: Initialize StackSense
print("\n2️⃣  Initializing StackSense...")
try:
    ss = StackSense(
        project_id="test-project",
        environment="development",
        debug=True
    )
    print(f"   ✅ Initialized for project: {ss.settings.project_id}")
except Exception as e:
    print(f"   ❌ Initialization failed: {e}")
    exit(1)

# Step 3: Track some fake API calls
print("\n3️⃣  Tracking fake API calls...")
try:
    # Simulate 3 API calls
    for i in range(3):
        ss.tracker.track_call(
            provider="openai",
            model="gpt-4",
            tokens={"input": 100 + i*10, "output": 50 + i*5},
            latency=1000 + i*100,
            success=True
        )
        print(f"   ✅ Tracked call {i+1}/3")
except Exception as e:
    print(f"   ❌ Tracking failed: {e}")
    exit(1)

# Step 4: Track a custom event
print("\n4️⃣  Tracking custom event...")
try:
    ss.track_event(
        event_type="test_event",
        provider="system",
        metadata={"test": True, "timestamp": "2024-01-15"}
    )
    print("   ✅ Custom event tracked!")
except Exception as e:
    print(f"   ❌ Event tracking failed: {e}")
    exit(1)

# Step 5: Get metrics
print("\n5️⃣  Retrieving metrics...")
try:
    metrics = ss.get_metrics()
    
    print(f"""
   📊 Metrics Summary:
      Total Calls:     {metrics['total_calls']}
      Total Tokens:    {metrics['total_tokens']:,}
      Total Cost:      ${metrics['total_cost']:.4f}
      Avg Cost/Call:   ${metrics['avg_cost_per_call']:.4f}
      Avg Latency:     {metrics['avg_latency']:.2f}ms
      Error Rate:      {metrics['error_rate']:.2f}%
      Providers:       {', '.join(metrics['providers'])}
    """)
    print("   ✅ Metrics retrieved successfully!")
except Exception as e:
    print(f"   ❌ Metrics retrieval failed: {e}")
    exit(1)

# Step 6: Get cost breakdown
print("\n6️⃣  Getting cost breakdown...")
try:
    breakdown = ss.get_cost_breakdown()
    print("   Cost by Provider:")
    for provider, cost in breakdown.items():
        print(f"      {provider:15s}: ${cost:.4f}")
    print("   ✅ Cost breakdown retrieved!")
except Exception as e:
    print(f"   ❌ Cost breakdown failed: {e}")
    exit(1)

# Step 7: Get performance stats
print("\n7️⃣  Getting performance stats...")
try:
    perf = ss.get_performance_stats()
    for provider, stats in perf.items():
        print(f"""
   Provider: {provider}
      Calls:          {stats['calls']}
      Avg Latency:    {stats['avg_latency']:.2f}ms
      Total Tokens:   {stats['total_tokens']:,}
      Avg Tokens:     {stats['avg_tokens_per_call']}
      Errors:         {stats['errors']}
      Error Rate:     {stats['error_rate']:.2f}%
        """)
    print("   ✅ Performance stats retrieved!")
except Exception as e:
    print(f"   ❌ Performance stats failed: {e}")
    exit(1)

# Step 8: View tracked events
print("\n8️⃣  Viewing tracked events...")
try:
    events = ss.tracker.get_events()
    print(f"   Total events tracked: {len(events)}")
    print("\n   Last 3 events:")
    for i, event in enumerate(events[-3:], 1):
        print(f"""
      Event {i}:
         Provider:  {event.get('provider', 'N/A')}
         Model:     {event.get('model', 'N/A')}
         Tokens:    {event.get('total_tokens', 0)}
         Cost:      ${event.get('cost', 0):.4f}
         Latency:   {event.get('latency', 0):.2f}ms
         Success:   {'✅' if event.get('success', True) else '❌'}
        """)
    print("   ✅ Events displayed!")
except Exception as e:
    print(f"   ❌ Event display failed: {e}")
    exit(1)

# Final summary
print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\n✅ StackSense is working correctly!")
print("\nNext steps:")
print("  • Try test_openai.py with real OpenAI API")
print("  • Enable database: export STACKSENSE_ENABLE_DB=true")
print("  • Run dashboard: pip install stacksense[dashboard]")
print("\n" + "=" * 60)
