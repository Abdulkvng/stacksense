"""
CLI command to run StackSense dashboard
"""

import click
from stacksense.dashboard.server import run_server
from stacksense.database import get_db_manager


@click.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=5000, type=int, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--db-url', default=None, help='Database URL (optional)')
def dashboard(host, port, debug, db_url):
    """Run StackSense dashboard server."""
    db_manager = None
    if db_url:
        from stacksense.database.connection import DatabaseManager
        db_manager = DatabaseManager(database_url=db_url)
        db_manager.create_tables()
    else:
        db_manager = get_db_manager()
    
    run_server(host=host, port=port, debug=debug, db_manager=db_manager)

