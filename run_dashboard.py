#!/usr/bin/env python3
"""
Simple script to run the StackSense dashboard
"""
from stacksense.dashboard.server import run_server
from stacksense.database import get_db_manager

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting StackSense Dashboard")
    print("=" * 60)
    try:
        db_manager = get_db_manager()
        run_server(host="127.0.0.1", port=5000, debug=True, db_manager=db_manager)
    except KeyboardInterrupt:
        print("\n👋 Shutting down dashboard...")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        import traceback
        traceback.print_exc()


