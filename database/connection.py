import os
import logging
import sys
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base

logger = logging.getLogger('telegramtastic.connection')

def get_db_connection_string():
    """Construct the database connection string for SQLite"""
    # Get the database file path from environment variable or use a default
    db_path = os.getenv('SQLITE_DATABASE_PATH', os.path.join(os.path.dirname(__file__), '../data/telegramtastic.db'))
    
    # Make sure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    logger.info(f"Using SQLite database at: {db_path}")
    
    # SQLite connection string format
    return f"sqlite:///{db_path}"

def setup_database():
    """Set up the database connection and return a session factory"""
    connection_string = get_db_connection_string()
    
    try:
        # Create engine with SQLite-compatible settings
        engine = create_engine(
            connection_string,
            connect_args={"check_same_thread": False},  # Allow multi-threading access to SQLite
            poolclass=pool.StaticPool  # Use a static pool for SQLite
        )
        
        # Add event listener for connection pool checkout errors
        @event.listens_for(engine, "connect")
        def connect(dbapi_connection, connection_record):
            logger.info("Database connection established")
            # Enable foreign key support for SQLite
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        # Create all tables if they don't exist
        Base.metadata.create_all(engine)
        
        # Run database migrations
        migrate_database(engine)
        
        # Create a session factory
        session_factory = scoped_session(sessionmaker(bind=engine))
        
        logger.info("SQLite database connection successful")
        return session_factory
    
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {e}")
        return None

def migrate_database(engine):
    """Apply database migrations for schema changes"""
    try:
        with engine.connect() as conn:
            # Check if last_print column exists
            result = conn.execute(text("PRAGMA table_info(nodes)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'last_print' not in columns:
                logger.info("Adding last_print column to nodes table")
                conn.execute(text("ALTER TABLE nodes ADD COLUMN last_print DATETIME"))
                conn.commit()
                logger.info("Database migration completed: added last_print column")
            else:
                logger.debug("Database schema is up to date")
                
    except SQLAlchemyError as e:
        logger.error(f"Database migration failed: {e}")
        raise