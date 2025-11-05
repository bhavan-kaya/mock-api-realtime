import logging
import psycopg2

from typing import Dict, Any, Optional
from psycopg2.errors import UniqueViolation

from app.exceptions.appointment.appointment_exceptions import (
    AppointmentNotFoundError,
    AppointmentAlreadyExistsError
)
from app.exceptions.database.database_connection_exception import DatabaseConnectionException
from app.exceptions.database.database_initialization_exception import DatabaseInitializationException
from app.services.db_service import PostgresClient
from singleton import SingletonMeta


# Get logger
logger = logging.getLogger(__name__)


# Define the DB table name
TABLE_NAME = "appointments"


class AppointmentService(metaclass=SingletonMeta):
    """
    Service layer for managing appointments, handling business logic
    and database operations.
    """
    def __init__(self):
        self.db_client = PostgresClient()
        self.table_name = TABLE_NAME

        # Initialize the db tables
        self._initialize_db()

    def _initialize_db(self):
        """
        Creates the 'appointments' table if it doesn't already exist.
        The phone number is set to UNIQUE to help enforce requirement #1.
        """
        conn = None
        try:
            logger.info(f"Initializing database schema for {self.table_name}...")
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseInitializationException(
                    detail="Failed to connect to DB."
                )

            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id UUID PRIMARY KEY,
                customer_name VARCHAR(255) NOT NULL,
                customer_phone_number VARCHAR(20) NOT NULL UNIQUE,
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                vehicle_details VARCHAR(255),
                service VARCHAR(255),
                remarks TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """

            with conn.cursor() as cur:
                cur.execute(create_table_query)
            conn.commit()
            logger.info(f"Table '{self.table_name}' initialized successfully.")

        except psycopg2.Error as ex:
            if conn:
                conn.rollback()
            logger.error(f'Error while creating table for table:{self.table_name}: {str(ex)}')
            raise DatabaseInitializationException(
                detail=f'There was an error during schema initialization for table:{self.table_name}: {str(ex)}'
            )
        except Exception as e:
            error_message = (
                f"There was an error during schema initialization for table:{self.table_name}: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseInitializationException(detail=error_message)

        finally:
            if conn:
                conn.close()

    def create_appointment(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Creates a new appointment record.
        """
        conn = None
        try:
            # Connect to the DB
            conn = self.db_client
            conn.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Perform the create operation
            appointment_id = conn.create(self.table_name, data)
            logger.info(f"Successfully created record for {data['customer_phone_number']}")
            return appointment_id

        except UniqueViolation:
            # Rollback the changes
            if conn:
                conn.rollback()
            error_message = f"Error: Appointment already exists for phone {data['customer_phone_number']}"
            logger.error(error_message)
            raise AppointmentAlreadyExistsError(detail=error_message)

        except (DatabaseConnectionException, psycopg2.Error) as e:
            # Rollback the changes
            if conn:
                conn.rollback()
            error_message = f"There was a DB error occurred during establishing the connection: {str(e)}"
            logger.error(error_message)
            raise DatabaseConnectionException(detail=error_message)

        except Exception as e:
            # Rollback the changes
            if conn:
                conn.rollback()
            logger.error(f"There was an error occurred while creating an appointment: {str(e)}")
            raise

        finally:
            if conn:
                conn.close()

    def get_appointment_by_phone_number(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves an appointment record based on the phone number.
        """
        conn = None
        try:
            # Connect to the DB
            conn = self.db_client
            conn.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Create filters using the phone number
            filters = {"customer_phone_number": phone_number}

            # Perform the GET operation
            records = conn.read(self.table_name, filters)
            if not records:
                raise AppointmentNotFoundError(
                    detail=f"Phone: {phone_number} does not have any appointments"
                )
            return records[0]

        except (DatabaseConnectionException, psycopg2.Error) as e:
            error_message = (
                f"There was an error establishing connection to the DB during fetching an appointment "
                f"by phone number {phone_number}: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseConnectionException(error_message)

        except AppointmentNotFoundError as e:
            logger.error(
                f"There was an error occurred while fetching an appointment : {str(e)}"
            )
            raise

        except Exception as e:
            logger.error(
                f"There was an error occurred while fetching appointment by phone number {phone_number}: {str(e)}"
            )
            raise

        finally:
            if conn:
                conn.close()

    def update_appointment(self, data: Dict[str, Any]) -> Optional[bool]:
        """
        Updates an existing appointment record identified by phone number.
        """
        conn = None
        try:
            # Connect to the DB
            conn = self.db_client
            conn.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Create filters using the phone number
            phone_number = data['customer_phone_number']
            filters = {"customer_phone_number": phone_number}

            # Perform the update operation
            updated_record = self.db_client.update(
                table=self.table_name,
                data=data,
                filters=filters
            )
            if not updated_record:
                raise AppointmentNotFoundError(
                    detail=f"Phone: {phone_number} does not have any appointments to update with."
                )
            return True

        except (DatabaseConnectionException, psycopg2.Error) as e:
            error_message = (
                f"There was an error establishing connection to the DB during updating an appointment: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseConnectionException(error_message)

        except AppointmentNotFoundError as e:
            logger.error(
                f"There was an error occurred while updating an appointment: {str(e)}"
            )
            raise

        except Exception as e:
            logger.error(
                f"There was an error occurred while updating an appointment: {str(e)}"
            )
            raise

        finally:
            if conn:
                conn.close()

    def delete_appointment_by_phone_number(self, phone_number: str) -> bool:
        """
        Deletes an appointment record based on the phone number.
        """
        conn = None
        try:
            # Connect to the DB
            conn = self.db_client
            conn.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Create filters using the phone number
            filters = {"customer_phone_number": phone_number}

            # Perform the delete operation
            success = conn.delete(
                table=self.table_name,
                filters=filters
            )
            if not success:
                raise AppointmentNotFoundError(
                    detail=f"Phone: {phone_number} does not have any appointments to delete."
                )

            return success

        except (DatabaseConnectionException, psycopg2.Error) as e:
            error_message = (
                f"There was an error establishing connection to the DB during deleting an appointment: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseInitializationException(error_message)

        except AppointmentNotFoundError as e:
            logger.error(
                f"There was an error occurred while deleting an appointment: {str(e)}"
            )
            raise

        except Exception as e:
            logger.error(f"There was an error occurred while deleting an appointment: {str(e)}")
            raise

        finally:
            if conn:
                conn.close()


appointment_service = AppointmentService()
