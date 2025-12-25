"""
Database Connection Management
SQLAlchemy database session and connection handling
"""

from typing import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from loguru import logger

from src.config.settings import get_settings

settings = get_settings()

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.database.connection_string,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.debug,  # Log SQL statements in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for ORM models
Base = declarative_base()


# Connection pool event listeners for monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Event listener for new database connections"""
    logger.debug("Database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Event listener for connection checkout from pool"""
    logger.debug("Database connection checked out from pool")


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI

    Usage:
        @app.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions

    Usage:
        with get_db_context() as db:
            result = db.query(Model).all()

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables
    Creates all tables defined in SQLAlchemy models
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check database connection health

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.debug("Database connection health check passed")
        return True
    except Exception as e:
        logger.error(f"Database connection health check failed: {e}")
        return False


def get_db_pool_status() -> dict:
    """
    Get database connection pool status

    Returns:
        dict: Pool status information
    """
    pool_status = {
        "pool_size": engine.pool.size(),
        "checked_in_connections": engine.pool.checkedin(),
        "checked_out_connections": engine.pool.overflow(),
        "total_connections": engine.pool.size() + engine.pool.overflow(),
    }
    return pool_status


class DatabaseManager:
    """Database manager class for advanced operations"""

    def __init__(self):
        self.engine = engine
        self.session_factory = SessionLocal

    def create_session(self) -> Session:
        """Create a new database session"""
        return self.session_factory()

    def execute_raw_sql(self, sql: str, params: dict = None) -> list:
        """
        Execute raw SQL query

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            list: Query results
        """
        with self.engine.connect() as connection:
            result = connection.execute(sql, params or {})
            return result.fetchall()

    def vacuum_analyze(self) -> None:
        """Run VACUUM ANALYZE on PostgreSQL database"""
        try:
            with self.engine.connect() as connection:
                connection.execute("VACUUM ANALYZE")
            logger.info("Database VACUUM ANALYZE completed")
        except Exception as e:
            logger.error(f"VACUUM ANALYZE failed: {e}")

    def refresh_materialized_view(self, view_name: str) -> None:
        """
        Refresh a materialized view

        Args:
            view_name: Name of the materialized view
        """
        try:
            with self.engine.connect() as connection:
                connection.execute(f"REFRESH MATERIALIZED VIEW {view_name}")
            logger.info(f"Materialized view {view_name} refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh materialized view {view_name}: {e}")

    def get_table_size(self, table_name: str) -> str:
        """
        Get the size of a table

        Args:
            table_name: Name of the table

        Returns:
            str: Table size in human-readable format
        """
        query = f"""
            SELECT pg_size_pretty(pg_total_relation_size('{table_name}')) as size
        """
        with self.engine.connect() as connection:
            result = connection.execute(query)
            return result.fetchone()[0]


# Create singleton database manager instance
db_manager = DatabaseManager()
