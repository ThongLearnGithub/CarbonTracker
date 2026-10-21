import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import Integer

# Load .env from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:vgu30062001@localhost:5432/carbon_db",
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def migrate_trip_distance_precision():
    if engine.dialect.name not in {"postgresql", "mysql"}:
        return

    trip_columns = inspect(engine).get_columns("trips")
    distance_column = next(
        (column for column in trip_columns if column["name"] == "distance_km"),
        None,
    )
    if distance_column is None or not isinstance(distance_column["type"], Integer):
        return

    if engine.dialect.name == "postgresql":
        statement = (
            "ALTER TABLE trips ALTER COLUMN distance_km TYPE DOUBLE PRECISION "
            "USING distance_km::DOUBLE PRECISION"
        )
    else:
        statement = "ALTER TABLE trips MODIFY distance_km DOUBLE NOT NULL"

    with engine.begin() as connection:
        connection.execute(text(statement))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
