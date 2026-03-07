#!/usr/bin/env python3
"""Make tracked API calls through StackSense"""

import os
import sys
import asyncio
import random
from datetime import datetime

sys.path.insert(0, '/Users/kvng/projects/stacksense')

os.environ.setdefault('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY', ''))

from openai import AsyncOpenAI
from stacksense.database import get_db_manager
from stacksense.database.models import Event

# Test prompts
TEST_PROMPTS = [
    "What is Python?",
    "Explain machine learning briefly.",
    "Write a short haiku about coding.",
    "What are REST APIs?",
    "Explain async programming.",
    "What is Docker?",
    "Describe NoSQL databases.",
    "How does OAuth work?",
    "What is CI/CD?",
    "Explain microservices.",
]

async def make_tracked_api_call(client, db_manager, prompt, call_num):
    """Make an API call and track it in StackSense database"""
    
    model = "gpt-4o-mini"
    
    try:
        print(f"📞 Call #{call_num}: {prompt[:50]}...")
        
        start_time = datetime.utcnow()
        start_ms = asyncio.get_event_loop().time() * 1000
        
        # Make the actual API call
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        
        end_ms = asyncio.get_event_loop().time() * 1000
        latency = end_ms - start_ms
        
        # Calculate cost (gpt-4o-mini: $0.150/1M input, $0.600/1M output)
        input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.150
        output_cost = (response.usage.completion_tokens / 1_000_000) * 0.600
        total_cost = input_cost + output_cost
        
        # Track in StackSense database
        with db_manager.get_session() as session:
            event = Event(
                project_id="stacksense-demo",
                environment="production",
                provider="openai",
                model=response.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cost=total_cost,
                latency=latency,
                success=True,
                timestamp=start_time
            )
            session.add(event)
            session.commit()
        
        print(f"   ✅ Tracked! {response.usage.total_tokens} tokens, ${total_cost:.6f}, {latency:.0f}ms")
        print()
        
        return {
            "success": True,
            "tokens": response.usage.total_tokens,
            "cost": total_cost,
            "latency": latency
        }
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        
        # Track failure
        with db_manager.get_session() as session:
            event = Event(
                project_id="stacksense-demo",
                environment="production",
                provider="openai",
                model=model,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost=0,
                latency=0,
                success=False,
                error=str(e),
                timestamp=datetime.utcnow()
            )
            session.add(event)
            session.commit()
        
        return {"success": False}

async def run_tracked_calls(num_calls=15):
    """Make tracked API calls"""
    
    client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'])
    db_manager = get_db_manager()
    
    print("=" * 80)
    print("🎯 MAKING TRACKED API CALLS THROUGH STACKSENSE")
    print("=" * 80)
    print()
    print(f"📊 Making {num_calls} tracked API calls...")
    print(f"💾 All calls will be logged to the StackSense dashboard")
    print(f"⏱️  Estimated time: ~{num_calls * 1.5:.0f} seconds")
    print()
    
    results = []
    total_cost = 0
    total_tokens = 0
    successful = 0
    
    for i in range(num_calls):
        prompt = random.choice(TEST_PROMPTS)
        
        result = await make_tracked_api_call(client, db_manager, prompt, i + 1)
        results.append(result)
        
        if result["success"]:
            successful += 1
            total_cost += result["cost"]
            total_tokens += result["tokens"]
        
        # Small delay between calls
        await asyncio.sleep(0.5)
    
    # Print summary
    print("=" * 80)
    print("✅ TRACKED API CALLS COMPLETE")
    print("=" * 80)
    print()
    print(f"📊 Results:")
    print(f"   Successful Calls: {successful}/{num_calls}")
    print(f"   Total Tokens: {total_tokens:,}")
    print(f"   Total Cost: ${total_cost:.4f}")
    print(f"   Avg Tokens/Call: {total_tokens/successful if successful else 0:.0f}")
    print(f"   Avg Cost/Call: ${total_cost/successful if successful else 0:.6f}")
    print()
    print("🎉 All calls tracked! Check dashboard at http://127.0.0.1:5000")
    print(f"   → Click 'Overview' to see updated metrics")
    print(f"   → Click '24h' timeframe button to refresh data")
    print()

if __name__ == "__main__":
    asyncio.run(run_tracked_calls(15))
