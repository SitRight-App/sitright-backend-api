from enum import Enum


class Role(str, Enum):
    WORKER = "worker"
    ADMIN = "admin"
