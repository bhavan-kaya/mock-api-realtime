import json
import logging
import math
from datetime import time, timedelta

import psycopg2
from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from app.exceptions.conversation.conversation_exception import (
    ConversationAlreadyExistsException
)
from app.exceptions.database.database_connection_exception import DatabaseConnectionException
from app.exceptions.database.database_initialization_exception import DatabaseInitializationException
from app.models.conversation.customer_data_model import (
    CustomerDataModel,
    CallDataModel,
    VehicleDataModel,
    ConversationSummaryModel,
    SentimentDataModel
)
from app.models.conversation.customer_data_request_model import CustomerDataRequestModel
from app.models.conversation.customer_data_response_model import (
    CustomerDataResponseModel,
    MetadataModel
)
from app.models.enum.response_status import ResponseStatus
from app.services.db_service import PostgresClient
from singleton import SingletonMeta


# Get logger
logger = logging.getLogger(__name__)


class ConversationService(metaclass=SingletonMeta):
    def __init__(self):
        """
        Initializes the ConversationService and its database client.
        The PostgresClient is assumed to manage its own connection pool.
        """
        self.db_client = PostgresClient()
        self._initialize_db()

    def _initialize_db(self):
        """
        Creates all necessary tables, types, and indexes if they don't already exist.
        This schema is designed to match the CustomerDataRequestModel.
        """
        conn = None
        try:
            logger.info("Initializing database schema for conversations...")
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseInitializationException(
                    detail="Failed to connect to DB."
                )

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
                call_duration INTERVAL,
                artifacts JSONB,
                live_agent_transfer BOOLEAN,
                abandoned BOOLEAN,
                elead BOOLEAN
            );

            -- 4. Create the vehicles table
            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id SERIAL PRIMARY KEY,
                call_id INTEGER UNIQUE REFERENCES calls(call_id) ON DELETE CASCADE,
                vehicle VARCHAR(100),
                model VARCHAR(100),
                requirements JSONB
            );

            -- 5. NEW: Create the summaries table
            CREATE TABLE IF NOT EXISTS summaries (
                summary_id SERIAL PRIMARY KEY,
                call_id INTEGER UNIQUE REFERENCES calls(call_id) ON DELETE CASCADE,
                summary TEXT NOT NULL,
                intent TEXT NOT NULL,
                resolution TEXT NOT NULL,
                escalation TEXT,
                next_steps TEXT,
                flags JSONB,
                tags JSONB,
                average_handle_time JSONB
            );

            -- 6. NEW: Create the sentiments table
            CREATE TABLE IF NOT EXISTS sentiments (
                sentiment_id SERIAL PRIMARY KEY,
                call_id INTEGER UNIQUE REFERENCES calls(call_id) ON DELETE CASCADE,
                score NUMERIC(5, 2),
                tone_summary TEXT,
                ai_interpretation TEXT,
                emotion_breakdown JSONB,
                key_phrases JSONB
            );

            -- 7. Create indexes for faster lookups
            CREATE INDEX IF NOT EXISTS idx_calls_customer_id ON calls (customer_id);
            CREATE INDEX IF NOT EXISTS idx_vehicles_call_id ON vehicles (call_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_summaries_call_id ON summaries (call_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sentiments_call_id ON sentiments (call_id);
            """

            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
            logger.info("Database schema is ready.")

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            error_message = f'Error while creating tables for conversations: {str(e)}'
            logger.error(error_message)
            raise DatabaseInitializationException(detail=error_message)

        except Exception as e:
            error_message = f'Error while creating tables for conversations: {str(e)}'
            logger.error(error_message)
            raise DatabaseInitializationException(detail=error_message)

        finally:
            if conn:
                self.db_client.close()

    @staticmethod
    def _convert_interval_to_time(interval: timedelta) -> time:
        """
        Convert a timedelta (INTERVAL) to a time object.

        Args:
            interval: timedelta object from database

        Returns:
            time object representing duration
        """
        total_seconds = int(interval.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return time(hour=hours % 24, minute=minutes, second=seconds)

    def save_conversation_data(self, request: CustomerDataRequestModel) -> int:
        """
        Logs a complete call as a single transaction from a CustomerDataRequestModel.

        Args:
            request (CustomerDataRequestModel): The complete request data.
        """
        conn = None

        # Extract data from the request model
        customer_data = request.customer_data
        call_data = request.call_data
        summary_data = request.summary_data
        sentiment_data = request.sentiment_data
        vehicle_data = request.vehicle_data

        try:
            logger.info(f'Started logging call details for SID: {call_data.sid}')
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            with conn.cursor() as cur:
                # Insert/Update Customer
                sql_customer = """
                   INSERT INTO customers (phone_number, first_name, customer_type)
                   VALUES (%s, %s, %s) ON CONFLICT (phone_number) DO \
                   UPDATE SET
                       first_name = EXCLUDED.first_name, \
                       customer_type = EXCLUDED.customer_type \
                       RETURNING customer_id; \
                               """
                cur.execute(sql_customer, (
                    customer_data.phone_number,
                    customer_data.first_name,
                    customer_data.customer_type.value
                ))
                customer_id = cur.fetchone()[0]
                logger.debug(f"Processed customer_id: {customer_id}")

                # Insert Call
                sql_call = """
                   INSERT INTO calls (
                       customer_id, \
                       created_time, \
                       sid, \
                       call_duration, \
                       artifacts, \
                       live_agent_transfer, \
                       abandoned, \
                       elead
                   )
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING call_id; \
                           """
                artifacts_json = json.dumps([artifact.model_dump() for artifact in call_data.artifacts])

                cur.execute(sql_call, (
                    customer_id,
                    call_data.created_time,
                    call_data.sid,
                    call_data.duration.isoformat(),  # Convert time to string for INTERVAL
                    artifacts_json,
                    call_data.live_agent_transfer,
                    call_data.abandoned,
                    call_data.e_lead
                ))
                call_id = cur.fetchone()[0]
                logger.debug(f"Logged call_id: {call_id}")

                # Insert Summary
                sql_summary = """
                  INSERT INTO summaries (
                      call_id, \
                      summary, \
                      intent, \
                      resolution, \
                      escalation, \
                      next_steps, \
                      flags, \
                      tags, \
                      average_handle_time
                  )
                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s); \
                              """
                cur.execute(sql_summary, (
                    call_id,
                    summary_data.summary,
                    summary_data.intent,
                    summary_data.resolution,
                    summary_data.escalation,
                    summary_data.next_steps,
                    json.dumps(summary_data.flags),
                    json.dumps(summary_data.tags),
                    json.dumps(summary_data.average_handle_time)
                ))

                # Insert Sentiment
                sql_sentiment = """
                    INSERT INTO sentiments (
                        call_id, \
                        score, \
                        tone_summary, \
                        ai_interpretation, \
                        emotion_breakdown, \
                        key_phrases
                    )
                    VALUES (%s, %s, %s, %s, %s, %s); \
                    """
                cur.execute(sql_sentiment, (
                    call_id,
                    sentiment_data.score,
                    sentiment_data.tone_summary,
                    sentiment_data.ai_interpretation,
                    json.dumps(sentiment_data.emotion_breakdown),
                    json.dumps(sentiment_data.key_phrases)
                ))

                # Insert Vehicle
                if vehicle_data:
                    sql_vehicle = """
                      INSERT INTO vehicles (call_id, \
                                            vehicle, \
                                            model, \
                                            requirements)
                      VALUES (%s, %s, %s, %s); \
                                  """
                    requirements_json = json.dumps(vehicle_data.requirements)
                    cur.execute(sql_vehicle, (
                        call_id,
                        vehicle_data.vehicle,
                        vehicle_data.model,
                        requirements_json
                    ))
                    logger.debug(f"Logged vehicle data for call_id: {call_id}")

            # Commit the transaction
            conn.commit()
            logger.info(f"Successfully committed all data for SID: {call_data.sid}")

            return customer_id

        except UniqueViolation as e:
            # Rollback the changes
            if conn:
                conn.rollback()
            error_message = f"Error during saving conversation data: {str(e)}"
            logger.error(error_message)
            raise ConversationAlreadyExistsException(
                detail=f"Call with SID {call_data.sid} already exists.",
            )
        
        except (DatabaseConnectionException, psycopg2.Error) as e:
            # Rollback the changes
            if conn:
                conn.rollback()
            logger.error(f"Database error saving conversation data: {str(e)}")
            raise DatabaseConnectionException(
                detail=f"Database error while saving conversation data: {str(e)}"
            )

        except Exception as e:
            # Rollback the changes
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error in save_conversation_data: {str(e)}")
            raise

        finally:
            if conn:
                conn.close()

    def get_conversation_data(self, page: int, per_page: int) -> CustomerDataResponseModel:
        """
        Retrieves all consolidated data, now joining all 5 tables.
        """
        conn = None
        try:
            conn = self.db_client.connect()
            if not conn:
                raise DatabaseConnectionException(detail="Could not connect to database.")

            sql_query = """
                SELECT
                    -- Customer columns
                    c.customer_id,
                    c.phone_number,
                    c.first_name,
                    c.customer_type,

                    -- Call columns
                    cl.call_id,
                    cl.created_time,
                    cl.sid,
                    cl.call_duration,
                    cl.artifacts,
                    cl.live_agent_transfer,
                    cl.abandoned,
                    cl.elead,

                    -- Vehicle columns
                    v.vehicle_id,
                    v.vehicle,
                    v.model,
                    v.requirements,

                    -- Summary columns
                    s.summary_id,
                    s.summary,
                    s.intent,
                    s.resolution,
                    s.escalation,
                    s.next_steps,
                    s.flags,
                    s.tags,
                    s.average_handle_time,

                    -- Sentiment columns
                    se.sentiment_id,
                    se.score,
                    se.tone_summary,
                    se.ai_interpretation,
                    se.emotion_breakdown,
                    se.key_phrases,

                    -- Total count window function
                    COUNT(*) OVER() AS total_items
                FROM calls cl
                         JOIN
                     customers c ON cl.customer_id = c.customer_id
                         LEFT JOIN
                     vehicles v ON cl.call_id = v.call_id
                         LEFT JOIN
                     summaries s ON cl.call_id = s.call_id
                         LEFT JOIN
                     sentiments se ON cl.call_id = se.call_id
                ORDER BY cl.created_time DESC
                    LIMIT %s
                OFFSET %s; \
                        """
            logger.info(f"Fetching page {page} of conversation data ({per_page} items per page).")

            # Fetch all the conversation data with pagination
            offset = (page - 1) * per_page
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query, (per_page, offset))
                rows = cur.fetchall()

            total_items = rows[0]["total_items"] if rows else 0
            results = []
            for row in rows:
                # Build CustomerDataModel
                customer_data = CustomerDataModel(
                    first_name=row['first_name'],
                    phone_number=row['phone_number'],
                    customer_type=row['customer_type']
                )

                # Convert call_duration (interval/timedelta) to time object
                duration_time = self._convert_interval_to_time(row['call_duration'])

                # Build CallDataModel
                call_data = CallDataModel(
                    created_time=row['created_time'],
                    sid=row['sid'],
                    duration=duration_time,
                    artifacts=row['artifacts'] if row['artifacts'] else [],
                    live_agent_transfer=row['live_agent_transfer'],
                    abandoned=row['abandoned'],
                    e_lead=row['elead']
                )

                # Build VehicleDataModel
                vehicle_data = VehicleDataModel(
                    vehicle=row['vehicle'],
                    model=row['model'],
                    requirements=row['requirements'] if row['requirements'] else []
                )

                # Build ConversationSummaryModel
                summary_data = ConversationSummaryModel(
                    summary=row['summary'],
                    intent=row['intent'],
                    resolution=row['resolution'],
                    escalation=row['escalation'] if row['escalation'] else "",
                    next_steps=row['next_steps'],
                    flags=row['flags'] if row['flags'] else [],
                    tags=row['tags'] if row['tags'] else [],
                    average_handle_time=row['average_handle_time'] if row['average_handle_time'] else []
                )

                # Build SentimentDataModel
                sentiment_data = SentimentDataModel(
                    score=float(row['score']),
                    tone_summary=row['tone_summary'],
                    ai_interpretation=row['ai_interpretation'],
                    emotion_breakdown=row['emotion_breakdown'] if row['emotion_breakdown'] else [],
                    key_phrases=row['key_phrases'] if row['key_phrases'] else []
                )

                # Create the complete CustomerDataRequestModel
                results.append(CustomerDataRequestModel(
                    customer_data=customer_data,
                    call_data=call_data,
                    vehicle_data=vehicle_data,
                    summary_data=summary_data,
                    sentiment_data=sentiment_data
                ))

            logger.info(f"Successfully fetched and structured {len(results)} items for page {page}.")

            total_pages = math.ceil(total_items / per_page) if total_items > 0 else 0

            return CustomerDataResponseModel(
                data=results,
                metadata=MetadataModel(
                    total_items=total_items,
                    total_pages=total_pages,
                    current_page=page,
                    per_page=per_page
                ),
                status=ResponseStatus.SUCCESS
            )

        except (DatabaseConnectionException, psycopg2.Error) as e:
            error_message = (
                f"Database error while fetching paginated data (page={page}, per_page={per_page}): {str(e)}"
            )
            logger.error(error_message)
            raise DatabaseConnectionException(detail=error_message)

        except Exception as e:
            logger.error(f"An unexpected error occurred during paginated data retrieval: {str(e)}")
            raise

        finally:
            if conn:
                conn.close()


conversation_service = ConversationService()