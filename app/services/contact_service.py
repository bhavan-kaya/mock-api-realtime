import uuid
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.errors import UniqueViolation
from app.services.db_service import PostgresClient
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.exceptions.database.database_connection_exception import DatabaseConnectionException
from app.exceptions.database.database_initialization_exception import DatabaseInitializationException
from singleton import SingletonMeta

# Get logger
logger = logging.getLogger(__name__)

# Define the DB table name
TABLE_NAME = "users_contact_info"


class ContactAlreadyExistsException(Exception):
    """Exception raised when contact already exists"""
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(self.detail)


class ContactNotFoundException(Exception):
    """Exception raised when contact is not found"""
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(self.detail)


class ContactInfoService(metaclass=SingletonMeta):
    """
    Service layer for managing contact information, handling business logic
    and database operations.
    """
    def __init__(self):
        self.db_client = PostgresClient()
        self.table_name = TABLE_NAME
        
        # Initialize the db tables
        self._initialize_db()
    
    def _initialize_db(self):
        """
        Creates the 'users_contact_info' table if it doesn't already exist.
        """
        conn = None
        try:
            logger.info(f"Initializing database schema for {self.table_name}...")
            
            # Create a new connection for initialization
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseInitializationException(
                    detail="Failed to connect to database for initialization"
                )
            
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_name VARCHAR(255) NOT NULL,
                contact_number VARCHAR(20) NOT NULL UNIQUE,
                date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            create_index_query = f"""
            CREATE INDEX IF NOT EXISTS idx_contact_number ON {self.table_name}(contact_number);
            """

            with conn.cursor() as cur:
                cur.execute(create_table_query)
                cur.execute(create_index_query)
            
            conn.commit()
            logger.info(f"Table '{self.table_name}' initialized successfully.")

        except psycopg2.Error as ex:
            if conn:
                conn.rollback()
            logger.error(f'Error while creating table for {self.table_name}: {str(ex)}')
            raise DatabaseInitializationException(
                detail=f'There was an error during schema initialization for {self.table_name}: {str(ex)}'
            )
        except Exception as e:
            if conn:
                conn.rollback()
            error_message = (
                f"There was an error during schema initialization for {self.table_name}: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseInitializationException(detail=error_message)
        finally:
            # Always close the connection after initialization
            if conn:
                conn.close()
                logger.debug("Database connection closed after initialization")
    
    def save_contact_info(
        self, 
        customer_name: str, 
        contact_number: str, 
        date: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Save contact information to users_contact_info table.
        If phone number already exists, updates the record instead of creating a new one.
        
        Args:
            customer_name: Name of the customer
            contact_number: Contact phone number
            date: Date of contact (defaults to current datetime)
        
        Returns:
            ID of the created/updated record or None if failed
        """
        if date is None:
            date = datetime.now()
        
        conn = None
        try:
            # Create a new connection for this operation
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database")

            # Check if contact already exists
            check_query = f"""
                SELECT id FROM {self.table_name} 
                WHERE contact_number = %s;
            """
            
            with conn.cursor() as cur:
                cur.execute(check_query, (contact_number,))
                existing_record = cur.fetchone()
            
            if existing_record:
                # Update existing record
                logger.info(f"Contact number {contact_number} already exists. Updating record...")
                update_query = f"""
                    UPDATE {self.table_name}
                    SET customer_name = %s,
                        date = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE contact_number = %s
                    RETURNING id;
                """
                
                with conn.cursor() as cur:
                    cur.execute(update_query, (customer_name, date, contact_number))
                    contact_id = cur.fetchone()[0]
                
                conn.commit()
                logger.info(f"Contact info updated successfully for: {contact_number}")
                return str(contact_id)
            else:
                # Create new record
                logger.info(f"Creating new contact for: {contact_number}")
                insert_query = f"""
                    INSERT INTO {self.table_name} (
                        customer_name,
                        contact_number,
                        date
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """
                
                with conn.cursor() as cur:
                    cur.execute(insert_query, (customer_name, contact_number, date))
                    contact_id = cur.fetchone()[0]
                
                conn.commit()
                logger.info(f"Contact info saved successfully with ID: {contact_id}")
                return str(contact_id)
                
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            error_message = f"Database error while saving contact info: {str(e)}"
            logger.error(error_message)
            raise DatabaseConnectionException(detail=error_message)
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save contact info: {str(e)}")
            raise
        
        finally:
            # Always close the connection
            if conn:
                conn.close()
                logger.debug("Database connection closed after save operation")

    def get_customer_by_contact(self, contact_number: str) -> Optional[Dict[str, Any]]:
        """
        Get customer information by contact number
        
        Args:
            contact_number: Contact phone number to search
        
        Returns:
            Dictionary containing customer info or None if not found
        """
        conn = None
        try:
            # Create a new connection for this operation
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database")

            # Retrieves the contact details with summary from the previous conversation
            sql_query = f"""
                SELECT 
                    u.id,
                    u.customer_name,
                    u.contact_number,
                    u.date,
                    u.created_at,
                    u.updated_at,
                    s.summary
                FROM {self.table_name} u
                LEFT JOIN customers cu 
                    ON cu.phone_number = u.contact_number
                LEFT JOIN calls c 
                    ON c.customer_id = cu.customer_id
                LEFT JOIN summaries s 
                    ON s.call_id = c.call_id
                WHERE u.contact_number = %s
                ORDER BY c.created_time DESC
            """
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query, (contact_number,))
                result = cur.fetchone()
            
            if not result:
                logger.info(f"No customer found with contact number: {contact_number}")
                return None
            
            logger.info(f"Found customer: {result['customer_name']}")
            return dict(result)
        
        except psycopg2.Error as e:
            error_message = (
                f"Database error while fetching customer by contact {contact_number}: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseConnectionException(detail=error_message)
        
        except Exception as e:
            logger.error(f"Failed to get customer info: {str(e)}")
            raise
        
        finally:
            # Always close the connection
            if conn:
                conn.close()
                logger.debug("Database connection closed after get operation")
    
    def get_customer_name(self, contact_number: str) -> Optional[str]:
        """
        Get customer name by contact number
        
        Args:
            contact_number: Contact phone number to search
        
        Returns:
            Customer name or None if not found
        """
        customer = self.get_customer_by_contact(contact_number)
        return customer.get('customer_name') if customer else None

    def get_all_contacts(self) -> List[Dict[str, Any]]:
        """
        Get all contact information from the database
        
        Returns:
            List of dictionaries containing all contact records
        """
        conn = None
        try:
            # Create a new connection for this operation
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database")

            sql_query = f"""
                SELECT id,
                       customer_name,
                       contact_number,
                       date,
                       created_at,
                       updated_at
                FROM {self.table_name}
                ORDER BY created_at DESC;
            """
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query)
                results = cur.fetchall()
            
            logger.info(f"Retrieved {len(results)} contacts")
            return [dict(row) for row in results]
        
        except psycopg2.Error as e:
            error_message = f"Database error while fetching all contacts: {str(e)}"
            logger.error(error_message)
            raise DatabaseConnectionException(detail=error_message)
        
        except Exception as e:
            logger.error(f"Failed to get all contacts: {str(e)}")
            raise
        
        finally:
            # Always close the connection
            if conn:
                conn.close()
                logger.debug("Database connection closed after get all operation")

    def update_contact_by_phone(
        self, 
        contact_number: str, 
        customer_name: Optional[str] = None,
        new_contact_number: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> bool:
        """
        Update contact information by phone number
        
        Args:
            contact_number: Current contact phone number
            customer_name: New customer name (optional)
            new_contact_number: New phone number (optional)
            date: New date (optional)
        
        Returns:
            True if updated successfully, False otherwise
        """
        conn = None
        try:
            # Build update data with only provided fields
            update_fields = []
            values = []
            
            if customer_name is not None:
                update_fields.append("customer_name = %s")
                values.append(customer_name)
            if new_contact_number is not None:
                update_fields.append("contact_number = %s")
                values.append(new_contact_number)
            if date is not None:
                update_fields.append("date = %s")
                values.append(date)
            
            if not update_fields:
                logger.warning(f"No update data provided for {contact_number}")
                return False
            
            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add phone number for WHERE clause
            values.append(contact_number)
            
            # Create a new connection for this operation
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database")

            sql_query = f"""
                UPDATE {self.table_name}
                SET {', '.join(update_fields)}
                WHERE contact_number = %s
                RETURNING id;
            """
            
            with conn.cursor() as cur:
                cur.execute(sql_query, tuple(values))
                result = cur.fetchone()
            
            conn.commit()
            
            if not result:
                raise ContactNotFoundException(
                    detail=f"No contact found to update for: {contact_number}"
                )
            
            logger.info(f"Contact updated successfully for: {contact_number}")
            return True
        
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            error_message = f"Database error while updating contact: {str(e)}"
            logger.error(error_message)
            raise DatabaseConnectionException(detail=error_message)
        
        except ContactNotFoundException:
            if conn:
                conn.rollback()
            raise
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to update contact: {str(e)}")
            raise
        
        finally:
            # Always close the connection
            if conn:
                conn.close()
                logger.debug("Database connection closed after update operation")

    def delete_contact_by_phone(self, contact_number: str) -> bool:
        """
        Delete contact information by phone number
        
        Args:
            contact_number: Contact phone number to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        conn = None
        try:
            # Create a new connection for this operation
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database")

            sql_query = f"""
                DELETE FROM {self.table_name}
                WHERE contact_number = %s
                RETURNING id;
            """
            
            with conn.cursor() as cur:
                cur.execute(sql_query, (contact_number,))
                result = cur.fetchone()
            
            conn.commit()
            
            if not result:
                raise ContactNotFoundException(
                    detail=f"No contact found to delete for: {contact_number}"
                )
            
            logger.info(f"Contact deleted successfully for: {contact_number}")
            return True
        
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            error_message = f"Database error while deleting contact: {str(e)}"
            logger.error(error_message)
            raise DatabaseConnectionException(detail=error_message)
        
        except ContactNotFoundException:
            if conn:
                conn.rollback()
            raise
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to delete contact: {str(e)}")
            raise
        
        finally:
            # Always close the connection
            if conn:
                conn.close()
                logger.debug("Database connection closed after delete operation")


# Create singleton instance
contact_service = ContactInfoService()