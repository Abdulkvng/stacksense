"""
Database connection and session management
"""

import os
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import StaticPool

from stacksense.database.models import Base
from stacksense.logger.logger import get_logger


class DatabaseManager:
    """
    Manages database connections and sessions.
    """
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        echo: bool = False,
        enable_pooling: bool = True,
    ):
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection URL
                          - SQLite: sqlite:///path/to/db.sqlite
                          - PostgreSQL: postgresql://user:pass@host:port/dbname
            echo: Enable SQL query logging
            enable_pooling: Enable connection pooling (disabled for SQLite)
        """
        self.logger = get_logger(__name__)
        
        # Default to SQLite if no URL provided
        if not database_url:
            db_path = os.getenv(
                "STACKSENSE_DB_PATH",
                os.path.join(os.getcwd(), "stacksense.db")
            )
            database_url = f"sqlite:///{db_path}"
            enable_pooling = False  # SQLite doesn't need pooling
        
        self.database_url = database_url
        self.echo = echo
        
        # Create engine
        engine_kwargs = {
            "echo": echo,
        }
        
        # SQLite-specific configuration
        if database_url.startswith("sqlite"):
            engine_kwargs.update({
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            })
        else:
            # PostgreSQL/other databases
            if enable_pooling:
                engine_kwargs.update({
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_pre_ping": True,  # Verify connections before using
                })
        
        self.engine = create_engine(database_url, **engine_kwargs)
        
        # Create session factory
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )
        
        self.logger.info(f"Database initialized: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    
    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        self.logger.info("Database tables created")
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
        self.logger.warning("Database tables dropped")
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session context manager.
        
        Usage:
            with db_manager.get_session() as session:
                # Use session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """
        Get a database session directly (caller must close).
        
        Returns:
            Database session
        """
        return self.SessionLocal()
    
    def health_check(self) -> bool:
        """
        Check database connection health.
        
        Returns:
            True if connection is healthy
        """
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(
    database_url: Optional[str] = None,
    echo: bool = False,
    create_tables: bool = True,
) -> DatabaseManager:
    """
    Get or create the global database manager instance.
    
    Args:
        database_url: Database connection URL
        echo: Enable SQL query logging
        create_tables: Automatically create tables if they don't exist
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url=database_url, echo=echo)
        if create_tables:
            _db_manager.create_tables()
    
    return _db_manager


def reset_db_manager() -> None:
    """Reset the global database manager (useful for testing)."""
    global _db_manager
    _db_manager = None

