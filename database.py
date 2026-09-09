from collections.abc import Generator
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sahaayak.db")
DATABASE_ENGINE = os.getenv("DATABASE_ENGINE", "sqlite")
MONGO_URI = os.getenv("MONGO_URI")


class Base(DeclarativeBase):
    pass


mongo_client = None
mongo_db = None


if DATABASE_ENGINE.lower() == "mongodb" or (MONGO_URI and DATABASE_URL.startswith("mongodb")):
    try:
        from pymongo import MongoClient
    except Exception:
        MongoClient = None

    if MongoClient:
        mongo_client = MongoClient(MONGO_URI or DATABASE_URL, serverSelectionTimeoutMS=3000)
        mongo_db = mongo_client.get_default_database()


if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = None

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def ensure_user_columns() -> None:
    """Add new profile fields to an existing development SQLite database."""
    if not engine or DATABASE_URL.startswith("mongodb"):
        return

    expected = {
        "aadhaar_number": "VARCHAR(12)",
        "upi_id": "VARCHAR(120)",
        "bank_account_number": "VARCHAR(40)",
        "bank_ifsc": "VARCHAR(20)",
        "permanent_address": "TEXT",
        "residential_address": "TEXT",
    }
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        for name, sql_type in expected.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type}"))


def get_db() -> Generator[Session, None, None]:
    if DATABASE_URL.startswith("mongodb") or DATABASE_ENGINE.lower() == "mongodb":
        raise RuntimeError("MongoDB migration requires the API route layer to be rewritten from SQLAlchemy sessions to the Mongo repository API.")

    if engine is None:
        raise RuntimeError("No SQLAlchemy database engine is configured.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_hint() -> dict[str, str]:
    return {
        "backend": "sqlite" if DATABASE_URL.startswith("sqlite") else "mongodb" if DATABASE_URL.startswith("mongodb") else "configured",
        "database_url": DATABASE_URL,
        "mongo_uri_configured": "true" if MONGO_URI else "false",
    }


def get_database_hint() -> dict[str, str]:
    return {
        "backend": "sqlite" if DATABASE_URL.startswith("sqlite") else "mongodb" if DATABASE_URL.startswith("mongodb") else "configured",
        "database_url": DATABASE_URL,
        "mongo_uri_configured": "true" if MONGO_URI else "false",
    }
