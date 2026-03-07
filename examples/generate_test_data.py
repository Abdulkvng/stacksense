#!/usr/bin/env python3
"""Generate test data for StackSense dashboard monitoring"""

import os
import sys
import asyncio
import random
from datetime import datetime

sys.path.insert(0, '/Users/kvng/projects/stacksense')

os.environ['OPENAI_API_KEY'] = 'REDACTED_KEY'

from openai import AsyncOpenAI

# Test scenarios
TEST_PROMPTS = [
    "What is Python?",
    "Explain machine learning in simple terms.",
    "Write a haiku about coding.",
    "What are the benefits of cloud computing?",
    "Describe a REST API.",
    "What is async programming?",
    "Explain Docker containers.",
    "What is the difference between SQL and NoSQL?",
    "How does OAuth work?",
    "What is CI/CD?",
]

MODELS = [
    "gpt-4o-mini",
    "gpt-4o-mini",  # Use mini more often (cheaper)
    "gpt-4o-mini",
]

async def make_api_call(client, prompt, model, call_num):
    """Make a single API call and track it"""
    try:
        start = datetime.now()
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        
        end = datetime.now()
        latency = (end - start).total_seconds() * 1000
        
        # Calculate cost
        input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.150
        output_cost = (response.usage.completion_tokens / 1_000_000) * 0.600
        total_cost = input_cost + output_cost
        
        print(f"✅ Call #{call_num}: {model}")
        print(f"   Prompt: {prompt[:50]}...")
        print(f"   Tokens: {response.usage.total_tokens}")
        print(f"   Cost: ${total_cost:.6f}")
        print(f"   Latency: {latency:.0f}ms")
        print()
        
        return {
            "success": True,
            "model": model,
            "tokens": response.usage.total_tokens,
            "cost": total_cost,
            "latency": latency
        }
        
    except Exception as e:
        print(f"❌ Call #{call_num} failed: {e}")
        return {"success": False}

async def run_test_suite(num_calls=20):
    """Run multiple API calls to generate test data"""
    client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'])
    
    print("=" * 80)
    print("🚀 GENERATING TEST DATA FOR STACKSENSE DASHBOARD")
    print("=" * 80)
    print()
    print(f"📊 Running {num_calls} API calls...")
    print(f"⏱️  This will take about {num_calls * 1.5:.0f} seconds")
    print()
    
    results = []
    total_cost = 0
    total_tokens = 0
    successful = 0
    
    for i in range(num_calls):
        prompt = random.choice(TEST_PROMPTS)
        model = random.choice(MODELS)
        
        result = await make_api_call(client, prompt, model, i + 1)
        results.append(result)
        
        if result["success"]:
            successful += 1
            total_cost += result["cost"]
            total_tokens += result["tokens"]
        
        # Small delay between calls
        await asyncio.sleep(0.5)
    
    # Print summary
    print("=" * 80)
    print("📈 TEST DATA GENERATION COMPLETE")
    print("=" * 80)
    print()
    print(f"✅ Successful Calls: {successful}/{num_calls}")
    print(f"💰 Total Cost: ${total_cost:.4f}")
    print(f"🎯 Total Tokens: {total_tokens:,}")
    print(f"📊 Avg Tokens/Call: {total_tokens/successful if successful else 0:.0f}")
    print(f"💵 Avg Cost/Call: ${total_cost/successful if successful else 0:.6f}")
    print()
    print("🎉 Dashboard data generated! Check http://127.0.0.1:5000")
    print()

if __name__ == "__main__":
    asyncio.run(run_test_suite(20))
