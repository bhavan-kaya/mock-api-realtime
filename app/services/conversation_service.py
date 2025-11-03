import logging

from singleton import SingletonMeta
from app.models.storage_response_model import FileData
from app.services.storage import storage_factory


# Get logger
logger = logging.getLogger(__name__)


class ConversationService(metaclass=SingletonMeta):
    def __init__(self):
        self.storage = storage_factory.get_storage()
    
    async def get_post_conversation_artifacts(self, sid: str) -> list[FileData]:
        """
        Retrieve post conversation artifacts of a given SID.
        
        Args:
            sid: The session ID to retrieve the post conversation artifacts for
            
        Returns:
            list[FileData]: The post conversation artifacts as a list of file data
        """
        return await self.storage.get_all_files_in_sid(sid)


conversation_service = ConversationService()
