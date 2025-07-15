from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, BigInteger, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, timezone

Base = declarative_base()

class NodeInfo(Base):
    """
    Model representing node information from Meshtastic devices.
    Maps to NODEINFO_APP message type.
    """
    __tablename__ = 'nodes'
    
    # Removed MySQL-specific table_args as they're not needed for SQLite

    # Primary key - node_id will be unique
    node_id = Column(BigInteger, primary_key=True, nullable=False)
    
    # Node information - using Text type for compatibility
    long_name = Column(Text, nullable=True)
    short_name = Column(Text, nullable=True) 
    hw_model_name = Column(String(32), nullable=True)
    hw_model_id = Column(Integer, nullable=True)
    
    # Tracking data - using UTC time
    first_seen = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_print = Column(DateTime, nullable=True)  # When this node last had a message printed

    def __repr__(self):
        return f"<NodeInfo(node_id={self.node_id}, short_name='{self.short_name}')>"
