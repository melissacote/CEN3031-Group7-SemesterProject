# User database operations
from datetime import datetime


class User:
    def __init__(self, id, username, first_name, last_name, phone_number, address, email = None):
        """Initialize new user"""
        self.id: int = id
        self.username: str = username
        self.first_name: str = first_name
        self.last_name: str = last_name
        self.phone_number: int = phone_number
        self.address: str = address
        self.email: str | None = email
        self.created_at: datetime = datetime.now()