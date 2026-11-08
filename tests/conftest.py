import pytest
from fastapi.testclient import TestClient

from app.db import connect, get_db, init_db
from app.main import app


@pytest.fixture
def client(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    app.dependency_overrides[get_db] = lambda: (yield from connect(path))
    yield TestClient(app)
    app.dependency_overrides.clear()
