import json
import math
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

from singleton import SingletonMeta
from app.models.enum.response_status import ResponseStatus

from app.models.conversation.customer_data_model import (
    CustomerDataModel,
    CallDataModel,
    VehicleDataModel
)
from app.models.conversation.customer_data_response_model import (
    CustomerDataResponseModel,
    MetadataModel
)
from app.exceptions.conversation.conversation_exception import (
    ConversationException,
    ConversationAlreadyExistsException
)
from app.services.db_service import PostgresClient


# Get logger
logger = logging.getLogger(__name__)


class ConversationService(metaclass=SingletonMeta):
    def __init__(self):
        self.db_client = PostgresClient()

        # Initialize the db tables
        self._initialize_db()

    def _initialize_db(self):
        """
        Creates all necessary tables, types, and indexes if they don't already exist.
        """
        conn = None
        try:
            logger.info("Initializing database schema, if not exists...")
            conn = self.db_client.connect()
            if not conn:
                logger.critical("Failed to connect to DB for initialization.")
                return

            schema_sql = """
            -- 1. Create the ENUM type for customer status
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cust_type') THEN
                    CREATE TYPE cust_type AS ENUM ('New Customer', 'Returning Customer');
                END IF;
            END$$;

            -- 2. Create the customers table
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                phone_number VARCHAR(25) UNIQUE NOT NULL,
                first_name VARCHAR(100),
                customer_type cust_type DEFAULT 'New Customer'
            );

            -- 3. Create the calls table
            CREATE TABLE IF NOT EXISTS calls (
                call_id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(customer_id) ON DELETE CASCADE,
                created_time TIMESTAMPTZ,
                sid VARCHAR(100) UNIQUE,
                call_duration TEXT,
                sentiment VARCHAR(4),
                artifacts JSONB,
                summary TEXT,
                live_agent_transfer BOOLEAN,
                abandoned BOOLEAN,
                elead BOOLEAN
            );

            -- 4. Create the vehicles table
            CREATE TABLE IF NOT EXISTS vehicles (
                subject_id SERIAL PRIMARY KEY,
                call_id INTEGER REFERENCES calls(call_id) ON DELETE CASCADE,
                vehicle VARCHAR(100),
                model VARCHAR(100),
                requirements JSONB
            );

            -- 5. Create indexes for faster lookups
            CREATE INDEX IF NOT EXISTS idx_calls_customer_id ON calls (customer_id);
            CREATE INDEX IF NOT EXISTS idx_vehicles_call_id ON vehicles (call_id);
            """

            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
            logger.info("Database schema is ready.")

        except Exception as e:
            logger.error(f"Error during schema initialization: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                self.db_client.close()

    def save_conversation_data(
            self,
            customer_data: CustomerDataModel,
            call_data: CallDataModel,
            vehicle_data: VehicleDataModel
    ) -> int:
        """
        Logs a complete call as a single transaction.

        Args:
            customer_data (CustomerDataModel): The customer data to log
            call_data (CallDataModel): The call data to log
            vehicle_data (VehicleDataModel): The vehicle data to log
        """
        conn = None
        try:
            logger.info('Started logging the call details')

            # Establish connection for this transaction
            conn = self.db_client.connect()

            if not conn:
                raise ConversationException(detail="Could not connect to database.")

            # Create a cursor for this transaction
            with conn.cursor() as cur:
                sql_customer = """
                               INSERT INTO customers (phone_number, \
                                                      first_name, \
                                                      customer_type)
                               VALUES (%s, %s, %s) ON CONFLICT (phone_number) 
                DO \
                               UPDATE SET
                                   first_name = EXCLUDED.first_name, \
                                   customer_type = EXCLUDED.customer_type \
                                   RETURNING customer_id; \
                               """

                # Save the customer data to the DB
                cur.execute(sql_customer, (
                    customer_data.phone_number,
                    customer_data.first_name,
                    customer_data.customer_type
                ))

                # Get the returned customer_id
                customer_id = cur.fetchone()[0]
                logger.debug(f"Processed customer_id: {customer_id}")

                # Insert the Call, using the customer_id
                sql_call = """
                           INSERT INTO calls (customer_id, \
                                              created_time, \
                                              sid, \
                                              call_duration, \
                                              sentiment, \
                                              artifacts, \
                                              summary, \
                                              live_agent_transfer, \
                                              abandoned, \
                                              elead)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING call_id; \
                           """

                # Convert artifacts to json string
                artifacts_list = [artifact.model_dump() for artifact in call_data.artifacts]
                artifacts_json = json.dumps(artifacts_list)

                # Save the call data to the DB
                cur.execute(sql_call, (
                    customer_id,
                    call_data.created_time,
                    call_data.sid,
                    call_data.duration,
                    call_data.sentiment,
                    artifacts_json,
                    call_data.summary,
                    call_data.transferred,
                    call_data.abandoned,
                    call_data.e_lead
                ))

                # Get the returned call_id
                call_id = cur.fetchone()[0]
                logger.debug(f"Logged call_id: {call_id}")

                # Insert the Call Subject using the call_id
                sql_subject = """
                              INSERT INTO vehicles (call_id, \
                                                    vehicle, \
                                                    model, \
                                                    requirements)
                              VALUES (%s, %s, %s, %s); \
                              """

                # Convert requirements list to json string
                requirements_json = json.dumps(vehicle_data.requirements)

                # Save the vehicle data to the DB
                cur.execute(sql_subject, (
                    call_id,
                    vehicle_data.vehicle,
                    vehicle_data.model,
                    requirements_json
                ))
                logger.info("Logged call subject.")

            # Commit the transaction
            conn.commit()
            logger.info(f"Successfully committed call data for SID: {call_data.sid}")

            return customer_id

        except psycopg2.Error as ex:
            if conn:
                conn.rollback()  # Rollback transaction on error

            error_message = f"Error during saving conversation data: {ex}"
            logger.error(error_message)

            if 'duplicate key value violates unique constraint' in str(ex):
                raise ConversationAlreadyExistsException(
                    detail="Call with SID already exists. Please try again.",
                )
            raise ConversationException(
                detail=error_message,
            )
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error in save_conversation_data: {e}")
            raise

        finally:
            if conn:
                self.db_client.close()

    def get_conversation_data(self, page: int, per_page: int) -> CustomerDataResponseModel:
        """
        Retrieves all consolidated data (customer, call, and subject)

        Args:
            page (int): Number of pages to return
            per_page (int): Number of items per page

        Returns:
            CustomerDataResponseModel: Response containing all joined data for the page
        """
        # Calculate offset
        offset = (page - 1) * per_page

        conn = None
        try:
            sql_query = """
                SELECT
                    -- Customer columns
                    c.customer_id, \
                    c.phone_number, \
                    c.first_name, \
                    c.customer_type,

                    -- Call columns
                    cl.created_time, \
                    cl.sid, \
                    cl.call_duration,
                    cl.sentiment, \
                    cl.artifacts, \
                    cl.summary, \
                    cl.live_agent_transfer,
                    cl.abandoned, \
                    cl.elead,

                    -- Vehicle columns
                    cs.vehicle, \
                    cs.model, \
                    cs.requirements,

                    -- Total count window function
                    COUNT(*) OVER() AS total_items
                FROM calls cl \
                         JOIN \
                     customers c ON cl.customer_id = c.customer_id \
                         JOIN \
                     vehicles cs ON cl.call_id = cs.call_id
                ORDER BY cl.created_time DESC
                    LIMIT %s
                OFFSET %s; \
                """
            logger.info(f"Fetching page {page} of conversation data ({per_page} items per page).")

            # Establish connection and use RealDictCursor
            conn = self.db_client.connect()
            if not conn:
                raise ConversationException(detail="Could not connect to database.")

            results = []
            total_items = 0

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Execute the query with LIMIT and OFFSET parameters
                cur.execute(sql_query, (per_page, offset))

                # Fetch all results for the page
                rows = cur.fetchall()

            if rows:
                # Get total_items from the *first row*
                total_items = rows[0]["total_items"]

                # Build the results list (and remove the 'total_items' field)
                for row in rows:
                    del row["total_items"]
                    results.append(row)
                logger.info(f"Successfully fetched {len(results)} items for page {page}.")
            else:
                logger.warning(f"No data found for page {page}.")

            # Calculate total pages
            total_pages = 0
            if total_items > 0:
                total_pages = math.ceil(total_items / per_page)

            #  Create the metadata model
            metadata = MetadataModel(
                total_items=total_items,
                total_pages=total_pages,
                current_page=page,
                per_page=per_page
            )

            return CustomerDataResponseModel(
                data=results,
                metadata=metadata,
                status=ResponseStatus.SUCCESS,
            )

        except psycopg2.Error as ex:
            logger.error(f"Error fetching paginated data (page={page}, per_page={per_page}): {ex}")
            raise ConversationException(
                detail=f"Error fetching paginated data: {ex}"
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred during paginated data retrieval: {e}")
            raise
        finally:
            if conn:
                self.db_client.close()


conversation_service = ConversationService()