import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.database as database_module
from src.database import init_db
from src.main import app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"
    # Point the module-level DB_PATH to the temp file
    original = database_module.DB_PATH
    database_module.DB_PATH = db_path
    init_db(db_path)

    with TestClient(app) as c:
        yield c

    database_module.DB_PATH = original
