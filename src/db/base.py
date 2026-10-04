"""Database base model imports."""

from src.db.session import Base

# Import all models to register them
from src.db.models import *  # noqa: F403,F401