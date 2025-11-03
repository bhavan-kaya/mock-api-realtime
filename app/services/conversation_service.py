import logging

from app.connectors.postgres_connector import PostgresConnector
from app.models.conversation.customer_data_request_model import CustomerDataRequestModel
from app.models.conversation.customer_data_response_model import CustomerDataResponseModel
from singleton import SingletonMeta


# Get logger
logger = logging.getLogger(__name__)


class ConversationService(metaclass=SingletonMeta):
    def __init__(self):
        self._initialize_db()

    @classmethod
    def _initialize_db(cls):
        """
        Initializes the database configuration
        """
        logger.info("Attempting to initialize database schema...")
        try:
            with PostgresConnector() as db:
                db.initialize_db()
            logger.info("Database initialization check complete.")
        except Exception as e:
            logger.critical(f"Database initialization failed: {e}")
            raise

    @staticmethod
    async def save_conversation_data(call_data: CustomerDataRequestModel) -> int:
        """
        Save conversation data to the database

        Args:
            call_data (CustomerDataRequestModel): A dictionary containing conversation data

        Returns:
            int: Customer ID
        """
        try:
            with PostgresConnector() as db:
                customer_id = db.save_conversation_data(
                    customer_data=call_data.customer_data,
                    call_data=call_data.call_data,
                    vehicle_data=call_data.vehicle_data
                )
            return customer_id
        except Exception as e:
            raise

    @staticmethod
    async def get_conversation_data(page: int, per_page: int) -> CustomerDataResponseModel:
        """
        Retrieves all consolidated data (customer, call, and subject)

        Args:
            page (int): Number of pages to return
            per_page (int): Number of items per page

        Returns:
            CustomerDataResponseModel: A dictionary containing all joined data for the call
        """
        try:
            with PostgresConnector() as db:
                customer_data = db.get_conversation_data(
                    page=page, 
                    per_page=per_page
                )
            return customer_data
        except Exception as e:
            raise


conversation_service = ConversationService()
