from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ml.settings import get_settings


def get_engine() -> Engine:
    return create_engine(get_settings().database_url)
