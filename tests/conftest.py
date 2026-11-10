import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app, get_db, get_current_user
from backend.app.database import Base
from backend.app.models import User, Skill


@pytest.fixture
def test_environment(tmp_path):
    # Create a separate SQLite database for this test.
    database_file = tmp_path / "cwip_test.db"
    engine = create_engine(f"sqlite:///{database_file}")

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    Base.metadata.create_all(bind=engine)

    db = TestSession()

    user = User(
        id=1,
        name="Test User",
        email="test@example.com",
        password_hash="test_hash"
    )

    other_user = User(
        id=2,
        name="Other User",
        email="other@example.com",
        password_hash="test_hash"
    )

    regression = Skill(
        id=1,
        name="Regression",
        description="Regression testing skill",
        category="Machine Learning"
    )

    statistics = Skill(
        id=2,
        name="Statistics",
        description="Statistics skill",
        category="Mathematics"
    )

    db.add_all([user, other_user, regression, statistics])
    db.commit()

    # Override the database dependency.
    def override_get_db():
        test_db = TestSession()
        try:
            yield test_db
        finally:
            test_db.close()

    # Override authentication with a controlled test user.
    def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as client:
            yield {
                "client": client,
                "db": db,
                "user": user,
                "other_user": other_user,
                "regression": regression,
                "statistics": statistics,
                "Session": TestSession,
            }
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
