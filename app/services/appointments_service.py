import logging
import psycopg2

from typing import Dict, Any, Optional
from psycopg2.extras import DictCursor
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

    def create_appointment(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Creates a new appointment record.
        """
        conn = None
        try:
            # Connect to the DB
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Insert appointment using explicit SQL
            sql_query = """
                        INSERT INTO appointments (customer_name, \
                                                  customer_phone_number, \
                                                  appointment_date, \
                                                  appointment_time, \
                                                  vehicle_details, \
                                                  service, \
                                                  remarks)
                        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id; \
                        """

            # Execute the query
            with conn.cursor() as cur:
                cur.execute(sql_query, (
                    data.get('customer_name'),
                    data.get('customer_phone_number'),
                    data.get('appointment_date'),
                    data.get('appointment_time'),
                    data.get('vehicle_details'),
                    data.get('service'),
                    data.get('remarks')
                ))
                appointment_id = cur.fetchone()[0]

            conn.commit()
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
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Select appointment using explicit SQL
            sql_query = """
                        SELECT id, \
                               customer_name, \
                               customer_phone_number, \
                               appointment_date, \
                               appointment_time, \
                               vehicle_details, \
                               service, \
                               remarks, \
                               created_at
                        FROM appointments
                        WHERE customer_phone_number = %s; \
                        """

            # Execute the query
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql_query, (phone_number,))
                result = cur.fetchone()

            if not result:
                raise AppointmentNotFoundError(
                    detail=f"Phone: {phone_number} does not have any appointments"
                )
            return dict(result)

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
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Extract the customer phone number
            phone_number = data['customer_phone_number']

            # Build dynamic UPDATE query based on provided fields
            update_fields = []
            values = []
            for key, value in data.items():
                if key != 'customer_phone_number' and value is not None:
                    update_fields.append(f"{key} = %s")
                    values.append(value)

            # Check for valid fields
            if not update_fields:
                logger.warning(f"No fields to update for phone number {phone_number}")
                return True

            # Add phone number for WHERE clause
            values.append(phone_number)

            # Formulate the SQL query
            sql_query = f"""
                UPDATE appointments
                SET {', '.join(update_fields)}
                WHERE customer_phone_number = %s
                RETURNING id;
            """

            # Execute the query
            with conn.cursor() as cur:
                cur.execute(sql_query, tuple(values))
                result = cur.fetchone()
            conn.commit()

            if not result:
                raise AppointmentNotFoundError(
                    detail=f"Phone: {phone_number} does not have any appointments to update with."
                )

            logger.info(f"Successfully updated appointment for {phone_number}")
            return True

        except (DatabaseConnectionException, psycopg2.Error) as e:
            if conn:
                conn.rollback()
            error_message = (
                f"There was an error establishing connection to the DB during updating an appointment: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseConnectionException(error_message)

        except AppointmentNotFoundError as e:
            if conn:
                conn.rollback()
            logger.error(
                f"There was an error occurred while updating an appointment: {str(e)}"
            )
            raise

        except Exception as e:
            if conn:
                conn.rollback()
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
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            # Delete appointment using explicit SQL
            sql_query = """
                        DELETE \
                        FROM appointments
                        WHERE customer_phone_number = %s RETURNING id; \
                        """

            # Execute the query
            with conn.cursor() as cur:
                cur.execute(sql_query, (phone_number,))
                result = cur.fetchone()
            conn.commit()

            if not result:
                raise AppointmentNotFoundError(
                    detail=f"Phone: {phone_number} does not have any appointments to delete."
                )

            logger.info(f"Successfully deleted appointment for {phone_number}")
            return True

        except (DatabaseConnectionException, psycopg2.Error) as e:
            if conn:
                conn.rollback()
            error_message = (
                f"There was an error establishing connection to the DB during deleting an appointment: {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseInitializationException(error_message)

        except AppointmentNotFoundError as e:
            if conn:
                conn.rollback()
            logger.error(
                f"There was an error occurred while deleting an appointment: {str(e)}"
            )
            raise

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"There was an error occurred while deleting an appointment: {str(e)}")
            raise

        finally:
            if conn:
                conn.close()


appointment_service = AppointmentService()
