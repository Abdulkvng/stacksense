"""
AI Gateway Performance Benchmark

Compares latency between:
1. No gateway (baseline)
2. Sync gateway (naive implementation)
3. Async gateway (optimized)
4. Async gateway with Redis
"""

import asyncio
import time
import statistics
from typing import List, Dict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stacksense.gateway.interceptor import AIGateway
from stacksense.gateway.interceptor_async import AsyncAIGateway


def benchmark_no_gateway(messages: List[Dict], model: str, iterations: int = 100):
    """Baseline: No gateway overhead."""
    latencies = []

    for _ in range(iterations):
        start = time.time()

        # Just pass through
        result = {
            "model": model,
            "messages": messages
        }

        latency = (time.time() - start) * 1000
        latencies.append(latency)

    return latencies


def benchmark_sync_gateway(messages: List[Dict], model: str, iterations: int = 100):
    """Sync gateway (naive implementation)."""
    gateway = AIGateway(
        enable_cache=True,
        enable_optimization=True,
        enable_smart_routing=False  # Disabled for fair comparison
    )

    latencies = []

    for _ in range(iterations):
        start = time.time()

        result = gateway.intercept(messages, model)

        latency = (time.time() - start) * 1000
        latencies.append(latency)

    return latencies


async def benchmark_async_gateway(messages: List[Dict], model: str, iterations: int = 100):
    """Async gateway (optimized with parallel execution)."""
    gateway = AsyncAIGateway(
        enable_cache=True,
        enable_optimization=True,
        enable_smart_routing=False  # Disabled for fair comparison
    )

    latencies = []

    for _ in range(iterations):
        start = time.time()

        result = await gateway.intercept(messages, model)

        latency = (time.time() - start) * 1000
        latencies.append(latency)

    return latencies


async def benchmark_async_gateway_cached(messages: List[Dict], model: str, iterations: int = 100):
    """Async gateway with cache hits."""
    gateway = AsyncAIGateway(
        enable_cache=True,
        enable_optimization=True,
        enable_smart_routing=False
    )

    # Prime the cache
    await gateway.intercept(messages, model)

    latencies = []

    for _ in range(iterations):
        start = time.time()

        # Should be cache hit
        result = await gateway.intercept(messages, model)

        latency = (time.time() - start) * 1000
        latencies.append(latency)

    return latencies


async def benchmark_concurrent_requests(
    messages: List[Dict],
    model: str,
    concurrency: int = 100
):
    """Benchmark concurrent requests."""
    gateway = AsyncAIGateway(
        enable_cache=True,
        enable_optimization=True,
        enable_smart_routing=False
    )

    start = time.time()

    # Create concurrent tasks
    tasks = [
        gateway.intercept(messages, model)
        for _ in range(concurrency)
    ]

    # Run all in parallel
    results = await asyncio.gather(*tasks)

    total_time = (time.time() - start) * 1000
    throughput = concurrency / (total_time / 1000)

    return total_time, throughput


def calculate_stats(latencies: List[float]) -> Dict:
    """Calculate latency statistics."""
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    return {
        "min": min(latencies),
        "max": max(latencies),
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p50": sorted_latencies[int(n * 0.50)],
        "p95": sorted_latencies[int(n * 0.95)],
        "p99": sorted_latencies[int(n * 0.99)],
        "stdev": statistics.stdev(latencies) if len(latencies) > 1 else 0
    }


def print_results(name: str, latencies: List[float]):
    """Print benchmark results."""
    stats = calculate_stats(latencies)

    print(f"\n{name}:")
    print(f"  Iterations: {len(latencies)}")
    print(f"  Mean:       {stats['mean']:.2f}ms")
    print(f"  Median:     {stats['median']:.2f}ms")
    print(f"  P50:        {stats['p50']:.2f}ms")
    print(f"  P95:        {stats['p95']:.2f}ms")
    print(f"  P99:        {stats['p99']:.2f}ms")
    print(f"  Min:        {stats['min']:.2f}ms")
    print(f"  Max:        {stats['max']:.2f}ms")
    print(f"  StdDev:     {stats['stdev']:.2f}ms")


async def main():
    """Run benchmarks."""
    print("=" * 70)
    print("AI Gateway Performance Benchmark")
    print("=" * 70)

    # Test data
    messages = [
        {"role": "user", "content": "Explain quantum computing in simple terms"}
    ]
    model = "gpt-4"
    iterations = 100

    print(f"\nConfiguration:")
    print(f"  Messages: {len(messages)}")
    print(f"  Model: {model}")
    print(f"  Iterations: {iterations}")

    # Benchmark 1: No gateway (baseline)
    print("\n" + "-" * 70)
    print("Running Benchmark 1: No Gateway (Baseline)")
    print("-" * 70)

    latencies_baseline = benchmark_no_gateway(messages, model, iterations)
    print_results("No Gateway (Baseline)", latencies_baseline)

    # Benchmark 2: Sync gateway
    print("\n" + "-" * 70)
    print("Running Benchmark 2: Sync Gateway")
    print("-" * 70)

    latencies_sync = benchmark_sync_gateway(messages, model, iterations)
    print_results("Sync Gateway", latencies_sync)

    baseline_mean = statistics.mean(latencies_baseline)
    sync_mean = statistics.mean(latencies_sync)
    overhead_sync = sync_mean - baseline_mean
    print(f"\n  Overhead: +{overhead_sync:.2f}ms ({(overhead_sync/baseline_mean*100):.1f}% slower)")

    # Benchmark 3: Async gateway
    print("\n" + "-" * 70)
    print("Running Benchmark 3: Async Gateway (Optimized)")
    print("-" * 70)

    latencies_async = await benchmark_async_gateway(messages, model, iterations)
    print_results("Async Gateway", latencies_async)

    async_mean = statistics.mean(latencies_async)
    overhead_async = async_mean - baseline_mean
    speedup = sync_mean / async_mean
    print(f"\n  Overhead: +{overhead_async:.2f}ms ({(overhead_async/baseline_mean*100):.1f}% slower)")
    print(f"  Speedup vs Sync: {speedup:.2f}x faster")

    # Benchmark 4: Async gateway with cache hits
    print("\n" + "-" * 70)
    print("Running Benchmark 4: Async Gateway (Cache Hits)")
    print("-" * 70)

    latencies_cached = await benchmark_async_gateway_cached(messages, model, iterations)
    print_results("Async Gateway (Cached)", latencies_cached)

    cached_mean = statistics.mean(latencies_cached)
    overhead_cached = cached_mean - baseline_mean
    cache_speedup = async_mean / cached_mean
    print(f"\n  Overhead: +{overhead_cached:.2f}ms ({(overhead_cached/baseline_mean*100):.1f}% slower)")
    print(f"  Speedup vs Uncached: {cache_speedup:.2f}x faster")

    # Benchmark 5: Concurrent requests
    print("\n" + "-" * 70)
    print("Running Benchmark 5: Concurrent Requests (100 concurrent)")
    print("-" * 70)

    total_time, throughput = await benchmark_concurrent_requests(messages, model, 100)

    print(f"\nConcurrent Requests (n=100):")
    print(f"  Total time: {total_time:.2f}ms")
    print(f"  Throughput: {throughput:.1f} req/s")

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    print(f"\nLatency Comparison:")
    print(f"  No Gateway:       {baseline_mean:.2f}ms (baseline)")
    print(f"  Sync Gateway:     {sync_mean:.2f}ms (+{overhead_sync:.2f}ms)")
    print(f"  Async Gateway:    {async_mean:.2f}ms (+{overhead_async:.2f}ms)")
    print(f"  Async (Cached):   {cached_mean:.2f}ms (+{overhead_cached:.2f}ms)")

    print(f"\nPerformance Gains:")
    print(f"  Async vs Sync:    {speedup:.2f}x faster")
    print(f"  Cache vs Uncached: {cache_speedup:.2f}x faster")

    print(f"\nThroughput:")
    print(f"  Concurrent (n=100): {throughput:.1f} req/s")

    # Comparison to LLM latency
    typical_llm_latency = 2000  # 2 seconds
    overhead_pct_async = (async_mean / typical_llm_latency) * 100
    overhead_pct_cached = (cached_mean / typical_llm_latency) * 100

    print(f"\nImpact on Total Request Time:")
    print(f"  Typical LLM latency: {typical_llm_latency}ms")
    print(f"  Async gateway overhead: {overhead_pct_async:.2f}% of total")
    print(f"  Cached gateway overhead: {overhead_pct_cached:.2f}% of total")

    print("\n" + "=" * 70)
    print("Benchmark Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
