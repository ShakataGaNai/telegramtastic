import logging
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from .models import NodeInfo

logger = logging.getLogger('telegramtastic.repository')

class NodeRepository:
    """Repository for NodeInfo database operations"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    def save_or_update_node(self, node_id, short_name=None, long_name=None, hw_model_name=None, hw_model_id=None):
        """
        Save a new node or update an existing one in the database
        
        Args:
            node_id (int): The unique node ID
            short_name (str, optional): The short name of the node
            long_name (str, optional): The long name of the node
            hw_model_name (str, optional): The hardware model name
            hw_model_id (int, optional): The hardware model ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = self.session_factory()
        try:
            # Check if node already exists
            node = session.query(NodeInfo).filter_by(node_id=node_id).first()
            
            if node:
                # Node exists, update it if any data has changed
                updated = False
                
                if short_name is not None and node.short_name != short_name:
                    node.short_name = short_name
                    updated = True
                
                if long_name is not None and node.long_name != long_name:
                    node.long_name = long_name
                    updated = True
                
                if hw_model_name is not None and node.hw_model_name != hw_model_name:
                    node.hw_model_name = hw_model_name
                    updated = True
                
                if hw_model_id is not None and node.hw_model_id != hw_model_id:
                    node.hw_model_id = hw_model_id
                    updated = True
                
                if updated:
                    # If any field was updated, log the update
                    node.last_seen = datetime.now(timezone.utc)
                    logger.info(f"Updated node {node_id} ({short_name}) in SQLite database")
                else:
                    # Just update the last_seen timestamp
                    node.last_seen = datetime.now(timezone.utc)
                    logger.debug(f"Updated last_seen for node {node_id}")
            else:
                # Node doesn't exist, create it
                new_node = NodeInfo(
                    node_id=node_id,
                    short_name=short_name,
                    long_name=long_name,
                    hw_model_name=hw_model_name,
                    hw_model_id=hw_model_id
                )
                session.add(new_node)
                logger.info(f"Added new node {node_id} ({short_name}) to SQLite database")
            
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"SQLite database error while saving node {node_id}: {e}")
            return False
        finally:
            session.close()
    
    def get_node_by_id(self, node_id):
        """Get a node by its ID"""
        session = self.session_factory()
        try:
            return session.query(NodeInfo).filter_by(node_id=node_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error while retrieving node {node_id}: {e}")
            return None
        finally:
            session.close()
    
    def can_print_message(self, node_id, rate_limit_seconds):
        """
        Check if a node can print a message based on rate limiting
        
        Args:
            node_id (int): The node ID to check
            rate_limit_seconds (int): Minimum seconds between prints
            
        Returns:
            bool: True if the node can print a message, False otherwise
        """
        session = self.session_factory()
        try:
            node = session.query(NodeInfo).filter_by(node_id=node_id).first()
            
            if not node:
                # Node doesn't exist in database, create it and allow printing
                return True
            
            if node.last_print is None:
                # Node has never printed a message, allow printing
                return True
            
            # Check if enough time has passed since last print
            now = datetime.now(timezone.utc)
            # Handle timezone-naive datetime from database
            last_print = node.last_print
            if last_print.tzinfo is None:
                last_print = last_print.replace(tzinfo=timezone.utc)
            time_since_last_print = (now - last_print).total_seconds()
            
            return time_since_last_print >= rate_limit_seconds
            
        except SQLAlchemyError as e:
            logger.error(f"Database error while checking print rate limit for node {node_id}: {e}")
            # In case of database error, allow printing to avoid blocking messages
            return True
        finally:
            session.close()
    
    def update_last_print(self, node_id):
        """
        Update the last_print timestamp for a node
        
        Args:
            node_id (int): The node ID to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        session = self.session_factory()
        try:
            node = session.query(NodeInfo).filter_by(node_id=node_id).first()
            
            if not node:
                # Node doesn't exist, create it with current timestamp
                new_node = NodeInfo(
                    node_id=node_id,
                    last_print=datetime.now(timezone.utc)
                )
                session.add(new_node)
                logger.info(f"Created new node {node_id} with last_print timestamp")
            else:
                # Update existing node
                node.last_print = datetime.now(timezone.utc)
                logger.debug(f"Updated last_print for node {node_id}")
            
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error while updating last_print for node {node_id}: {e}")
            return False
        finally:
            session.close()
