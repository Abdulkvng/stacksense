"""
Entry point for running the StackSense dashboard as a module.

Usage:
    python -m stacksense.dashboard
"""

from stacksense.dashboard import run_server

if __name__ == "__main__":
    run_server(debug=True)
