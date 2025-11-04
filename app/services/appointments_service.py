import logging
from typing import Dict, Any, Optional

from app.services.db_service import PostgresClient
from app.exceptions import (
    AppointmentNotFoundError,
    AppointmentAlreadyExistsError,
    AppointmentDataError
)
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
            logger.info("Initializing database schema, if not exists...")
            conn = self.db_client.connect()
            if not conn:
                logger.critical("Failed to connect to DB for initialization.")
                return

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

        except Exception as e:
            conn.rollback()
            logger.critical(f"Error initializing table '{self.table_name}': {e}")

        finally:
            if conn:
                conn.close()

    def create_appointment(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Creates a new appointment record.
        """
        self.db_client.connect()
        try:
            # Check for existing appointment
            filters = {"customer_phone_number": data['customer_phone_number']}

            existing_records = self.db_client.read(self.table_name, filters)
            if existing_records:
                logger.error(f"Error: Appointment already exists for phone {data['customer_phone_number']}")
                raise AppointmentAlreadyExistsError(
                    detail="An appointment with this phone number already exists!"
                )

            # If no record, proceed with creation
            record_id = self.db_client.create(self.table_name, data)
            if not record_id:
                logger.error(
                    f"There was a problem creating an appointment for phone {data['customer_phone_number']}"
                )
                raise AppointmentDataError(
                    "There was a problem creating an appointment. Please try again later."
                )

            # Fetch and return the newly created record
            new_records = self.db_client.read(self.table_name, {"id": record_id})
            logger.info(f"Successfully created record for {data['customer_phone_number']}")
            return new_records[0]

        except (AppointmentAlreadyExistsError, AppointmentDataError):
            raise
        except Exception as e:
            logger.info(f"Error creating record: {e}")
            raise

        finally:
            self.db_client.close()

    def get_appointment_by_phone_number(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves an appointment record based on the phone number.
        """
        self.db_client.connect()
        try:
            filters = {"customer_phone_number": phone_number}

            records = self.db_client.read(self.table_name, filters)
            if not records:
                logger.error(f"No record found for phone: {phone_number}")
                raise AppointmentNotFoundError(
                    detail="An appointment with this phone number does not exist!"
                )
            return records[0]

        except AppointmentNotFoundError:
            raise
        except Exception as e:
            logger.info(f"Error getting record: {e}")
            raise

        finally:
            self.db_client.close()

    def update_appointment(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Updates an existing appointment record identified by phone number.
        """
        self.db_client.connect()
        try:
            phone_number = data['customer_phone_number']
            update_filters = {"customer_phone_number": phone_number}

            # Check if record exists
            existing_records = self.db_client.read(self.table_name, update_filters)
            if not existing_records:
                logger.error(f"No appointment found for phone {phone_number} to update.")
                raise AppointmentNotFoundError(
                    detail="An appointment with this phone number does not exist!"
                )

            # If record exists, proceed with update
            success = self.db_client.update(self.table_name, data, update_filters)
            if not success:
                logger.error(f"There was a problem updating an appointment for phone {phone_number}.")
                raise AppointmentDataError(
                    detail="There was a problem updating an appointment. Please try again later."
                )

            # Fetch and return the updated record
            updated_records = self.db_client.read(self.table_name, update_filters)
            logger.info(f"Successfully updated record for {phone_number}")
            return updated_records[0]

        except (AppointmentNotFoundError, AppointmentDataError):
            raise
        except Exception as e:
            logger.info(f"Error updating record: {e}")
            raise

        finally:
            self.db_client.close()

    def delete_appointment_by_phone_number(self, phone_number: str) -> Dict[str, str]:
        """
        Deletes an appointment record based on the phone number.
        """
        self.db_client.connect()
        try:
            filters = {"customer_phone_number": phone_number}

            success = self.db_client.delete(self.table_name, filters)
            if not success:
                logger.error(f"No appointment found for phone {phone_number} to update.")
                raise AppointmentNotFoundError(
                    detail="An appointment with this phone number does not exist!"
                )

            logger.info(f"No record found to delete for phone: {phone_number}")
            return {
                'phone_number': phone_number,
                'deleted': success,
                'status': 'success' if success else 'failed'
            }

        except AppointmentNotFoundError:
            raise
        except Exception as e:
            logger.info(f"Error deleting record: {e}")
            raise

        finally:
            self.db_client.close()


appointment_service = AppointmentService()
