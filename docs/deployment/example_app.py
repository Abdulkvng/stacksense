#!/usr/bin/env python3
"""
Example application using StackSense
This demonstrates how to use StackSense in a containerized environment
"""

import os
import time
from stacksense import StackSense
from stacksense.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Initialize StackSense
# Database is automatically configured from environment variables
ss = StackSense(
    api_key=os.getenv("STACKSENSE_API_KEY"),
    project_id=os.getenv("STACKSENSE_PROJECT_ID", "example-app"),
    environment=os.getenv("STACKSENSE_ENVIRONMENT", "production"),
    debug=os.getenv("STACKSENSE_DEBUG", "false").lower() == "true",
)

logger.info("StackSense initialized")
logger.info(f"Database enabled: {ss.settings.enable_database}")
if ss.settings.enable_database:
    logger.info(f"Database URL: {ss.settings.database_url or 'SQLite (default)'}")


def get_metrics_summary():
    """Get and display metrics summary."""
    try:
        metrics = ss.get_metrics(timeframe="24h", from_db=True)
        
        print("\n" + "="*50)
        print("StackSense Metrics Summary (Last 24h)")
        print("="*50)
        print(f"Total API Calls: {metrics['total_calls']}")
        print(f"Total Tokens: {metrics['total_tokens']:,}")
        print(f"Total Cost: ${metrics['total_cost']:.4f}")
        print(f"Avg Cost per Call: ${metrics['avg_cost_per_call']:.4f}")
        print(f"Avg Latency: {metrics['avg_latency']:.2f}ms")
        print(f"Error Rate: {metrics['error_rate']:.2f}%")
        print(f"Providers: {', '.join(metrics['providers']) if metrics['providers'] else 'None'}")
        print("="*50 + "\n")
        
        return metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return None


def get_cost_breakdown():
    """Get and display cost breakdown by provider."""
    try:
        breakdown = ss.get_cost_breakdown()
        
        if breakdown:
            print("\nCost Breakdown by Provider:")
            print("-" * 30)
            for provider, cost in breakdown.items():
                print(f"  {provider:15s}: ${cost:.4f}")
            print("-" * 30 + "\n")
        
        return breakdown
    except Exception as e:
        logger.error(f"Failed to get cost breakdown: {e}")
        return None


def main():
    """Main application entry point."""
    logger.info("Example application started")
    
    # Example: Track a custom event
    ss.track_event(
        event_type="app_start",
        provider="system",
        metadata={"version": "1.0.0", "environment": ss.settings.environment}
    )
    
    # Display metrics
    get_metrics_summary()
    get_cost_breakdown()
    
    # Health check
    if ss.db_manager:
        health = ss.db_manager.health_check()
        logger.info(f"Database health: {'OK' if health else 'FAILED'}")
    
    logger.info("Example application completed")


if __name__ == "__main__":
    main()

