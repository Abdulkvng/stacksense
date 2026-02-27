"""
StackSense AI Gateway - Integration Example

Demonstrates complete integration of the AI Gateway into your application.
"""

import os
import time
from typing import List, Dict, Any

# Import StackSense AI Gateway components
from stacksense.gateway import (
    AIGateway,
    SmartRouter,
    PromptOptimizer,
    CostPredictor,
    RequestThrottler,
    SemanticCache,
    QualityTracker
)

# Simulated OpenAI client (replace with actual)
class MockOpenAIClient:
    """Mock OpenAI client for demonstration."""

    def chat_completion_create(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Simulate API call."""
        time.sleep(0.5)  # Simulate latency

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": f"This is a response from {model}."
                }
            }],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 25,
                "total_tokens": 75
            }
        }


def calculate_cost(response: Dict[str, Any], model: str) -> float:
    """Calculate cost based on token usage."""
    pricing = {
        "gpt-4": 0.00003,  # $0.03 per 1k tokens
        "gpt-4-turbo": 0.00001,
        "gpt-4o": 0.000005,
        "gpt-4o-mini": 0.00000015,
        "claude-3-opus": 0.000015,
        "claude-3-sonnet": 0.000003,
        "claude-3-haiku": 0.00000025,
    }

    total_tokens = response.get("usage", {}).get("total_tokens", 0)
    rate = pricing.get(model, 0.00001)

    return total_tokens * rate


class StackSenseChat:
    """
    AI Chat client with StackSense Gateway integration.

    This demonstrates how to wrap your existing LLM client
    with the StackSense AI Gateway for runtime control.
    """

    def __init__(
        self,
        db_session=None,
        user_id: str = "demo_user",
        openai_client=None
    ):
        """
        Initialize chat client with AI Gateway.

        Args:
            db_session: Database session (optional)
            user_id: User identifier
            openai_client: OpenAI client (or your LLM client)
        """
        self.user_id = user_id
        self.client = openai_client or MockOpenAIClient()

        # Initialize AI Gateway with all features
        self.gateway = AIGateway(
            db_session=db_session,
            user_id=user_id,
            enable_cache=True,
            enable_optimization=True,
            enable_smart_routing=True
        )

        print(f"✅ StackSense AI Gateway initialized for user: {user_id}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        max_latency_ms: int = 2000,
        min_quality_score: float = 0.80
    ) -> Dict[str, Any]:
        """
        Send chat request through AI Gateway.

        Args:
            messages: Chat messages
            model: Requested model
            max_latency_ms: Max acceptable latency (triggers provider switch)
            min_quality_score: Min quality (enables tier dropping)

        Returns:
            dict: Response with metadata
        """
        print(f"\n📨 Request: model={model}, messages={len(messages)}")

        # Step 1: Intercept request through gateway
        intercepted = self.gateway.intercept(
            messages=messages,
            model=model,
            max_latency_ms=max_latency_ms,
            min_quality_score=min_quality_score
        )

        # Step 2: Handle blocking/throttling
        if "error" in intercepted:
            print(f"🚫 Request blocked: {intercepted['message']}")
            return {
                "error": True,
                "message": intercepted["message"],
                "retry_after": intercepted.get("retry_after")
            }

        # Step 3: Check cache hit
        if intercepted.get("from_cache"):
            print(f"💾 Cache hit! (saved ${intercepted.get('cost', 0):.4f})")
            return {
                "response": intercepted["response"],
                "cached": True,
                "cost": 0.0,
                "model": model
            }

        # Step 4: Execute with potentially modified model/messages
        selected_model = intercepted["model"]
        optimized_messages = intercepted["messages"]

        if selected_model != model:
            print(f"🔀 Model switched: {model} → {selected_model}")

        if intercepted.get("optimized"):
            print(f"✂️  Prompt optimized: Token reduction applied")

        # Make actual API call
        start_time = time.time()

        try:
            response = self.client.chat_completion_create(
                model=selected_model,
                messages=optimized_messages
            )

            latency = (time.time() - start_time) * 1000  # ms
            actual_cost = calculate_cost(response, selected_model)

            print(f"✅ Response received: {latency:.0f}ms, ${actual_cost:.4f}")

            # Step 5: Track performance (enables learning)
            self.gateway.post_execution_tracking(
                request=intercepted,
                response=response,
                actual_cost=actual_cost,
                latency=latency
            )

            return {
                "response": response["choices"][0]["message"]["content"],
                "cached": False,
                "cost": actual_cost,
                "latency": latency,
                "model_used": selected_model,
                "model_switched": selected_model != model,
                "prompt_optimized": intercepted.get("optimized", False),
                "budget_action": intercepted.get("budget_action")
            }

        except Exception as e:
            print(f"❌ Request failed: {e}")
            return {
                "error": True,
                "message": str(e)
            }

    def get_cost_prediction(
        self,
        current_spend: float,
        days_elapsed: int,
        monthly_budget: float
    ) -> Dict[str, Any]:
        """Get monthly cost prediction and budget status."""
        predictor = CostPredictor()

        # Predict end-of-month cost
        prediction = predictor.predict_monthly_cost(
            current_spend=current_spend,
            days_elapsed=days_elapsed
        )

        # Check budget overrun
        overrun = predictor.check_budget_overrun(
            current_spend=current_spend,
            monthly_budget=monthly_budget,
            days_elapsed=days_elapsed
        )

        return {
            "prediction": prediction,
            "overrun": overrun
        }

    def get_quality_report(self) -> Dict[str, Any]:
        """Get quality metrics for all models."""
        tracker = self.gateway.quality_tracker

        if not tracker:
            return {"error": "Quality tracking not enabled"}

        # Get leaderboard (best value models)
        leaderboard = tracker.get_quality_leaderboard()

        # Get all metrics
        all_metrics = tracker.get_all_metrics()

        return {
            "leaderboard": leaderboard,
            "all_metrics": all_metrics
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        cache = self.gateway.cache

        if not cache:
            return {"error": "Cache not enabled"}

        stats = cache.get_stats()

        # Calculate estimated savings
        estimated_savings = stats["hits"] * 0.002  # Rough estimate

        return {
            **stats,
            "estimated_savings": estimated_savings
        }


def main():
    """Demonstration of AI Gateway features."""

    print("=" * 60)
    print("StackSense AI Gateway - Integration Demo")
    print("=" * 60)

    # Initialize chat client
    chat = StackSenseChat(user_id="demo_user")

    # Example 1: Basic chat (with caching)
    print("\n\n🔹 Example 1: Basic Chat Request")
    print("-" * 60)

    result1 = chat.chat(
        messages=[{"role": "user", "content": "What is a prime number?"}],
        model="gpt-4"
    )

    if not result1.get("error"):
        print(f"Response: {result1['response'][:100]}...")

    # Example 2: Same request (cache hit)
    print("\n\n🔹 Example 2: Same Request (Cache Hit)")
    print("-" * 60)

    result2 = chat.chat(
        messages=[{"role": "user", "content": "What is a prime number?"}],
        model="gpt-4"
    )

    if result2.get("cached"):
        print("✅ Served from cache!")

    # Example 3: Quality-based tier dropping
    print("\n\n🔹 Example 3: Quality-Based Tier Dropping")
    print("-" * 60)

    result3 = chat.chat(
        messages=[{"role": "user", "content": "Explain photosynthesis"}],
        model="gpt-4",
        min_quality_score=0.70  # Low threshold = more downgrades
    )

    if result3.get("model_switched"):
        print(f"✅ Tier dropped to save costs!")

    # Example 4: Cost prediction
    print("\n\n🔹 Example 4: Cost Prediction")
    print("-" * 60)

    prediction = chat.get_cost_prediction(
        current_spend=250.0,
        days_elapsed=15,
        monthly_budget=400.0
    )

    pred = prediction["prediction"]
    overrun = prediction["overrun"]

    print(f"Current spend: $250.00 (15 days elapsed)")
    print(f"Predicted monthly cost: ${pred['predicted_monthly_cost']:.2f}")
    print(f"Monthly budget: $400.00")
    print(f"Will exceed: {overrun['will_exceed']}")

    if overrun["will_exceed"]:
        print(f"⚠️  Predicted overage: ${overrun['overage']:.2f} ({overrun['overage_percent']:.1f}%)")
        print(f"Recommended action: {overrun['recommended_action']}")

    # Example 5: Cache statistics
    print("\n\n🔹 Example 5: Cache Statistics")
    print("-" * 60)

    cache_stats = chat.get_cache_stats()

    if "error" not in cache_stats:
        print(f"Cache hit rate: {cache_stats['hit_rate']*100:.1f}%")
        print(f"Cache size: {cache_stats['size']}/{cache_stats['max_size']}")
        print(f"Estimated savings: ${cache_stats['estimated_savings']:.2f}")

    # Example 6: Quality report
    print("\n\n🔹 Example 6: Quality Report")
    print("-" * 60)

    quality = chat.get_quality_report()

    if "error" not in quality and quality["leaderboard"]:
        print("Top models by cost-per-quality:")
        for i, model in enumerate(quality["leaderboard"][:3], 1):
            print(f"{i}. {model['model']}")
            print(f"   Quality: {model['avg_quality']:.2f} ({model['quality_rating']})")
            print(f"   Cost/Quality: ${model['cost_per_quality']:.4f}")

    print("\n" + "=" * 60)
    print("Demo complete! 🎉")
    print("=" * 60)


if __name__ == "__main__":
    main()
