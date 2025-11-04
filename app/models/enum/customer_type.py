from enum import Enum


class CustomerType(str, Enum):
    NEW = "New Customer"
    RETURNING = "Returning Customer"