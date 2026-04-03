import sqlite3
import pytest
from database.db_connection import create_tables

@pytest.fixture
def test_db():
    """Pytest fixture that creates a clean temporary database file for each test and deletes it after the test is complete."""
    conn = sqlite3.connect(':memory:')
    create_tables(conn)
    yield conn
    conn.close()