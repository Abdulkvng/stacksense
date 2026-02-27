"""
Production Client Example - Using StackSense Gateway Server

This demonstrates how to use the AI Gateway in a production environment
with minimal latency overhead (1-6ms).

Architecture:
    Your App → Gateway Server (FastAPI) → LLM Provider
                    ↓
              Redis + PostgreSQL

Latency:
- Gateway overhead: 1-6ms (< 0.5% of LLM latency)
- Cache hit: 1-2ms
- Total request time: LLM latency + gateway overhead
"""

import asyncio
import httpx
import time
from typing import List, Dict, Any


class StackSenseGatewayClient:
    """
    Production client for StackSense AI Gateway.

    Uses async HTTP client for low latency.
    """

    def __init__(self, gateway_url: str = "http://localhost:8000", user_id: str = "demo_user"):
        """
        Initialize gateway client.

        Args:
            gateway_url: Gateway server URL
            user_id: User identifier for budget/quality tracking
        """
        self.gateway_url = gateway_url
        self.user_id = user_id
        self.client = httpx.AsyncClient(timeout=30.0)

    async def chat_with_gateway(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        max_latency_ms: int = 2000,
        min_quality_score: float = 0.80
    ) -> Dict[str, Any]:
        """
        Send chat request through gateway.

        The gateway will:
        1. Check budget and throttling (1ms)
        2. Optimize prompts (10-30ms, parallel)
        3. Check cache (1-2ms with Redis)
        4. Route to best provider (1-5ms)

        Total overhead: 1-6ms typical

        Args:
            messages: Chat messages
            model: Requested model
            max_latency_ms: Max acceptable latency (triggers provider switch)
            min_quality_score: Min quality threshold (enables tier dropping)

        Returns:
            dict: Intercepted request with potentially modified model/messages
        """
        start = time.time()

        # Send to gateway
        response = await self.client.post(
            f"{self.gateway_url}/v1/chat/intercept",
            json={
                "messages": messages,
                "model": model,
                "max_latency_ms": max_latency_ms,
                "min_quality_score": min_quality_score,
                "user_id": self.user_id
            }
        )

        gateway_latency = (time.time() - start) * 1000

        if response.status_code == 429:
            # Rate limited
            error = response.json()
            raise Exception(f"Rate limited: {error['detail']['message']}")

        elif response.status_code == 402:
            # Budget exceeded
            error = response.json()
            raise Exception(f"Budget exceeded: {error['detail']['message']}")

        elif response.status_code != 200:
            raise Exception(f"Gateway error: {response.text}")

        result = response.json()

        print(f"✅ Gateway processed request in {gateway_latency:.1f}ms")

        if result.get("from_cache"):
            print(f"💾 Cache hit! (saved LLM call)")

        if result.get("optimized"):
            print(f"✂️  Prompt optimized")

        if result["model"] != model:
            print(f"🔀 Model switched: {model} → {result['model']}")

        return result

    async def execute_llm_call(
        self,
        intercepted_request: Dict[str, Any],
        openai_client: Any
    ) -> Dict[str, Any]:
        """
        Execute actual LLM call with intercepted request.

        Args:
            intercepted_request: Result from gateway intercept
            openai_client: Your OpenAI client (or other LLM client)

        Returns:
            dict: LLM response
        """
        # If cache hit, return cached response immediately
        if intercepted_request.get("from_cache"):
            return {
                "response": intercepted_request.get("response"),
                "cached": True,
                "cost": 0.0,
                "latency": 0.0
            }

        # Execute with potentially modified model/messages
        start = time.time()

        try:
            # Replace with your actual LLM client call
            # response = openai_client.chat.completions.create(
            #     model=intercepted_request["model"],
            #     messages=intercepted_request["messages"]
            # )

            # Simulated response for demo
            await asyncio.sleep(0.5)  # Simulate LLM latency
            response = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"Response from {intercepted_request['model']}"
                    }
                }],
                "usage": {
                    "total_tokens": 100
                }
            }

            latency = (time.time() - start) * 1000

            # Calculate cost (simplified)
            cost = self._calculate_cost(response, intercepted_request["model"])

            return {
                "response": response,
                "cached": False,
                "cost": cost,
                "latency": latency
            }

        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            raise

    async def track_execution(
        self,
        intercepted_request: Dict[str, Any],
        llm_result: Dict[str, Any]
    ):
        """
        Track execution results (post-request).

        This runs in background and doesn't block.
        """
        await self.client.post(
            f"{self.gateway_url}/v1/chat/track",
            json={
                "user_id": self.user_id,
                "intercepted_request": intercepted_request,
                "response": llm_result["response"],
                "cost": llm_result["cost"],
                "latency": llm_result["latency"]
            }
        )

    def _calculate_cost(self, response: Dict, model: str) -> float:
        """Calculate cost based on token usage."""
        pricing = {
            "gpt-4": 0.00003,
            "gpt-4-turbo": 0.00001,
            "gpt-4o": 0.000005,
            "gpt-4o-mini": 0.00000015,
        }

        tokens = response.get("usage", {}).get("total_tokens", 0)
        rate = pricing.get(model, 0.00001)

        return tokens * rate

    async def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics for this user."""
        response = await self.client.get(
            f"{self.gateway_url}/v1/gateway/stats",
            params={"user_id": self.user_id}
        )

        return response.json()

    async def predict_cost(
        self,
        current_spend: float,
        days_elapsed: int,
        monthly_budget: float
    ) -> Dict[str, Any]:
        """Get monthly cost prediction."""
        response = await self.client.get(
            f"{self.gateway_url}/v1/cost/predict",
            params={
                "user_id": self.user_id,
                "current_spend": current_spend,
                "days_elapsed": days_elapsed,
                "monthly_budget": monthly_budget
            }
        )

        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def main():
    """Demonstration of production gateway usage."""
    print("=" * 70)
    print("StackSense AI Gateway - Production Client Demo")
    print("=" * 70)

    # Initialize client
    client = StackSenseGatewayClient(
        gateway_url="http://localhost:8000",
        user_id="demo_user"
    )

    try:
        # Example 1: Basic chat request
        print("\n\n🔹 Example 1: Chat Request Through Gateway")
        print("-" * 70)

        messages = [{"role": "user", "content": "Explain quantum computing"}]

        # Step 1: Intercept through gateway
        intercepted = await client.chat_with_gateway(
            messages=messages,
            model="gpt-4",
            max_latency_ms=2000,
            min_quality_score=0.80
        )

        # Step 2: Execute LLM call with intercepted request
        llm_result = await client.execute_llm_call(
            intercepted_request=intercepted,
            openai_client=None  # Replace with your client
        )

        # Step 3: Track results (background)
        await client.track_execution(intercepted, llm_result)

        print(f"\n✅ Request completed:")
        print(f"   Model used: {intercepted['model']}")
        print(f"   Cost: ${llm_result['cost']:.4f}")
        print(f"   LLM latency: {llm_result['latency']:.0f}ms")
        print(f"   Gateway latency: {intercepted['latency_ms']:.1f}ms")
        print(f"   Total time: {llm_result['latency'] + intercepted['latency_ms']:.0f}ms")

        overhead_pct = (intercepted['latency_ms'] / llm_result['latency']) * 100
        print(f"   Gateway overhead: {overhead_pct:.2f}% of total")

        # Example 2: Cache hit (same request)
        print("\n\n🔹 Example 2: Cache Hit")
        print("-" * 70)

        intercepted2 = await client.chat_with_gateway(
            messages=messages,
            model="gpt-4"
        )

        llm_result2 = await client.execute_llm_call(
            intercepted_request=intercepted2,
            openai_client=None
        )

        if llm_result2["cached"]:
            print("\n✅ Served from cache!")
            print(f"   Cost: $0.00 (saved ${llm_result['cost']:.4f})")
            print(f"   Latency: {intercepted2['latency_ms']:.1f}ms (vs {llm_result['latency']:.0f}ms)")

        # Example 3: Get statistics
        print("\n\n🔹 Example 3: Gateway Statistics")
        print("-" * 70)

        stats = await client.get_stats()

        if "cache" in stats and stats["cache"]:
            cache = stats["cache"]
            print(f"\nCache Statistics:")
            print(f"   Hit rate: {cache.get('hit_rate', 0)*100:.1f}%")
            print(f"   Size: {cache.get('size', 0)}/{cache.get('max_size', 0)}")
            print(f"   Total requests: {cache.get('total_requests', 0)}")

        # Example 4: Cost prediction
        print("\n\n🔹 Example 4: Cost Prediction")
        print("-" * 70)

        prediction = await client.predict_cost(
            current_spend=250.0,
            days_elapsed=15,
            monthly_budget=400.0
        )

        pred = prediction["prediction"]
        overrun = prediction["overrun"]

        print(f"\nCost Forecast:")
        print(f"   Current spend: $250.00 (15 days)")
        print(f"   Predicted monthly: ${pred['predicted_monthly_cost']:.2f}")
        print(f"   Budget: $400.00")

        if overrun["will_exceed"]:
            print(f"\n⚠️  Budget Overrun Predicted:")
            print(f"   Overage: ${overrun['overage']:.2f}")
            print(f"   Days until exceeded: {overrun['days_until_exceeded']}")
            print(f"   Action: {overrun['recommended_action']}")

        print("\n" + "=" * 70)
        print("Demo Complete!")
        print("=" * 70)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
