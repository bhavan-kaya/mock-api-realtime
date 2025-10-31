import logging
from typing import Union

from app.services.gcp_service import GCPService
from app.services.local_storage_service import LocalStorageService
from app.models.storage_type import StorageType
from config import STORAGE_TYPE

class StorageFactory:
    """
    Factory class to get the appropriate storage service based on configuration.
    The storage type is loaded from the STORAGE_TYPE environment variable.
    Defaults to 'gcp' if not specified.
    """
    _instance = None
    _storage_type = None
    _initialized = False
    
    def __init__(self):
        if not self._initialized:
            self.set_storage_type(STORAGE_TYPE)
            self._initialized = True
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StorageFactory, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def set_storage_type(cls, storage_type: Union[StorageType, str]):
        """
        Set the storage type to be used.
        
        Args:
            storage_type: Either StorageType enum or string ('gcp' or 'local')
            
        Raises:
            ValueError: If an invalid storage type is provided
        """
        if isinstance(storage_type, str):
            try:
                storage_type = StorageType(storage_type.lower())
            except ValueError as e:
                raise ValueError(f"Invalid storage type: {storage_type}. Must be one of: {[t.value for t in StorageType]}") from e
                
        cls._storage_type = storage_type
        logger = logging.getLogger(__name__)
        logger.info(f"Storage type set to: {cls._storage_type.value}")
    
    @classmethod
    def get_storage(cls):
        """
        Get the appropriate storage service based on current configuration.
        
        Returns:
            An instance of either GCPService or LocalStorageService
            
        Raises:
            ValueError: If storage type is not set or invalid
        """    
        if cls._storage_type == StorageType.GCP:
            return GCPService()
        elif cls._storage_type == StorageType.LOCAL:
            return LocalStorageService()
            
        raise ValueError(f"Unsupported storage type: {cls._storage_type}")


# Create a singleton instance of the storage factory
storage_factory = StorageFactory()

# Initialize with config value
storage_factory.set_storage_type(STORAGE_TYPE)
