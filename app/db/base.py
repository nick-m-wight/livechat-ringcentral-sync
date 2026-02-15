"""SQLAlchemy declarative base and database utilities."""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase
from typing import Any


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# For backward compatibility
metadata = Base.metadata
