"""
StackSense CLI - command-line interface for managing StackSense.
"""

import argparse
import sys
import json

from stacksense import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="stacksense",
        description="StackSense - AI Infrastructure Monitoring CLI",
    )
    parser.add_argument("--version", action="version", version=f"stacksense {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # stacksense dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Launch the monitoring dashboard")
    dash_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    dash_parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    dash_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # stacksense status
    subparsers.add_parser("status", help="Show current metrics summary")

    # stacksense export
    export_parser = subparsers.add_parser("export", help="Export metrics data")
    export_parser.add_argument("format", choices=["csv", "json"], help="Export format")
    export_parser.add_argument("-o", "--output", required=True, help="Output file path")
    export_parser.add_argument("--limit", type=int, help="Limit number of events")

    # stacksense db
    db_parser = subparsers.add_parser("db", help="Database management")
    db_sub = db_parser.add_subparsers(dest="db_command")
    db_sub.add_parser("init", help="Initialize database tables")
    db_sub.add_parser("health", help="Check database health")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "dashboard":
        _cmd_dashboard(args)
    elif args.command == "status":
        _cmd_status()
    elif args.command == "export":
        _cmd_export(args)
    elif args.command == "db":
        _cmd_db(args)


def _cmd_dashboard(args):
    try:
        from stacksense.dashboard.server import app

        print(f"Starting StackSense dashboard on http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
    except ImportError:
        print("Dashboard requires extra dependencies: pip install stacksense[dashboard]")
        sys.exit(1)


def _cmd_status():
    from stacksense import StackSense

    ss = StackSense()
    summary = ss.get_metrics()

    print("StackSense Status")
    print("=" * 40)
    print(f"  Total calls:  {summary.get('total_calls', 0)}")
    print(f"  Total tokens: {summary.get('total_tokens', 0)}")
    print(f"  Total cost:   ${summary.get('total_cost', 0):.4f}")

    by_provider = summary.get("by_provider", {})
    if by_provider:
        print("\n  By Provider:")
        for provider, data in by_provider.items():
            print(f"    {provider}: {data['calls']} calls, ${data['cost']:.4f}")


def _cmd_export(args):
    from stacksense import StackSense
    from stacksense.exporters import Exporter

    ss = StackSense()
    exporter = Exporter(ss.tracker)

    if args.format == "csv":
        exporter.to_csv(args.output, from_db=True, limit=args.limit)
    elif args.format == "json":
        exporter.to_json(args.output, from_db=True, limit=args.limit)

    print(f"Exported to {args.output}")


def _cmd_db(args):
    if args.db_command == "init":
        from stacksense.database.connection import get_db_manager

        db = get_db_manager(create_tables=True)
        print("Database tables created successfully")

    elif args.db_command == "health":
        from stacksense.database.connection import get_db_manager

        db = get_db_manager(create_tables=False)
        if db.health_check():
            print("Database is healthy")
        else:
            print("Database health check failed")
            sys.exit(1)

    else:
        print("Usage: stacksense db {init|health}")


if __name__ == "__main__":
    main()
