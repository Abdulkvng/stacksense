#!/usr/bin/env python3
"""Populate StackSense dashboard with test data"""

import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, '/Users/kvng/projects/stacksense')

from stacksense.database import get_db_manager
from stacksense.database.models import Event, User

# Sample test data
PROVIDERS = ["openai", "openai", "openai", "anthropic"]
MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-haiku", "claude-3-sonnet"]
}

def create_test_events(db_manager, num_events=50):
    """Create test events in the database"""
    
    print("=" * 80)
    print("📊 POPULATING STACKSENSE DASHBOARD WITH TEST DATA")
    print("=" * 80)
    print()
    
    with db_manager.get_session() as session:
        # Get test user
        user = session.query(User).filter(User.email == "test@stacksense.dev").first()
        if not user:
            print("❌ Test user not found. Creating...")
            user = User(
                email="test@stacksense.dev",
                name="Test User",
                is_active=True
            )
            session.add(user)
            session.commit()
            print(f"✅ Created test user: {user.email}")
        
        print(f"📝 Creating {num_events} test events...")
        print()
        
        total_cost = 0
        total_tokens = 0
        
        # Create events over the last 24 hours
        now = datetime.utcnow()
        
        for i in range(num_events):
            provider = random.choice(PROVIDERS)
            model = random.choice(MODELS[provider])
            
            # Random timestamps over last 24 hours
            hours_ago = random.uniform(0, 24)
            timestamp = now - timedelta(hours=hours_ago)
            
            # Generate realistic token counts
            prompt_tokens = random.randint(10, 200)
            completion_tokens = random.randint(20, 150)
            total = prompt_tokens + completion_tokens
            
            # Calculate cost based on provider/model
            if provider == "openai":
                if "gpt-4o" in model:
                    cost = (prompt_tokens / 1_000_000) * 5.00 + (completion_tokens / 1_000_000) * 15.00
                else:  # gpt-4o-mini, gpt-3.5-turbo
                    cost = (prompt_tokens / 1_000_000) * 0.150 + (completion_tokens / 1_000_000) * 0.600
            else:  # anthropic
                if "haiku" in model:
                    cost = (prompt_tokens / 1_000_000) * 0.25 + (completion_tokens / 1_000_000) * 1.25
                else:
                    cost = (prompt_tokens / 1_000_000) * 3.00 + (completion_tokens / 1_000_000) * 15.00
            
            # Random latency
            latency = random.uniform(200, 3000)
            
            # Random success (98% success rate)
            success = random.random() > 0.02
            
            event = Event(
                project_id="test-project",
                environment="production",
                provider=provider,
                model=model,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=total,
                cost=cost,
                latency=latency,
                success=success,
                timestamp=timestamp
            )
            
            session.add(event)
            
            total_cost += cost
            total_tokens += total
            
            if (i + 1) % 10 == 0:
                print(f"  ✅ Created {i + 1}/{num_events} events...")
        
        session.commit()
        
        print()
        print("=" * 80)
        print("✅ DATA POPULATION COMPLETE")
        print("=" * 80)
        print()
        print(f"📊 Summary:")
        print(f"   Total Events: {num_events}")
        print(f"   Total Tokens: {total_tokens:,}")
        print(f"   Total Cost: ${total_cost:.4f}")
        print(f"   Avg Cost/Event: ${total_cost/num_events:.6f}")
        print(f"   Time Range: Last 24 hours")
        print()
        print("🎉 Dashboard ready! Visit http://127.0.0.1:5000")
        print()

if __name__ == "__main__":
    db_manager = get_db_manager()
    create_test_events(db_manager, num_events=50)
