from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


settings = get_settings()

# Read the database host from DATABASE_URL, but obtain the password
# from the existing POSTGRES_PASSWORD setting.
base_url = make_url(settings.database_url)

database_url = URL.create(
    drivername="postgresql+psycopg",
    username="ai_platform_user",
    password=settings.postgres_password,
    host=base_url.host or "localhost",
    port=base_url.port or 5432,
    database=base_url.database or "ai_engineering_platform",
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
