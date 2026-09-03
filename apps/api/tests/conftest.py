import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["RESEARCH_PROVIDER"] = "mock"
os.environ["RESEARCH_RUN_INLINE"] = "true"
os.environ["AGENT_PROVIDER"] = "guided"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.accounts import models  # noqa: F401
from app.modules.agent import models as agent_models  # noqa: F401
from app.modules.business_case import models as business_case_models  # noqa: F401
from app.modules.deployment import models as deployment_models  # noqa: F401
from app.modules.discovery import models as discovery_models  # noqa: F401
from app.modules.evaluation import models as evaluation_models  # noqa: F401
from app.modules.poc import models as poc_models  # noqa: F401
from app.modules.research import models as research_models  # noqa: F401
from app.modules.solutions import models as solution_models  # noqa: F401

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session():
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def client():
    def override_get_db():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
