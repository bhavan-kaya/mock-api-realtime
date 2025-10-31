from enum import Enum


class StorageType(str, Enum):
    GCP = "gcp"
    LOCAL = "local"