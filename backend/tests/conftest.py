import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base


@pytest.fixture(scope="session")
def test_engine():
    settings = get_settings()

    test_database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://ai_platform_user@localhost:5432/ai_engineering_platform_test",
    )

    url = make_url(test_database_url).set(
        password=settings.postgres_password
    )

    if url.database != "ai_engineering_platform_test":
        raise RuntimeError(
            "Tests must use the isolated ai_engineering_platform_test database."
        )

    engine = create_engine(
        url,
        pool_pre_ping=True,
    )

    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()
