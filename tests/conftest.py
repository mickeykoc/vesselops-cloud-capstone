import pytest
from app import create_app

TOKEN = "test-operator-token-" + "x" * 40


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "API_TOKEN": TOKEN, "SQLITE_PATH": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth():
    return {"Authorization": "Bearer " + TOKEN}
