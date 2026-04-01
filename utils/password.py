from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Takes a plain text password, hashes using Argon2id, and returns hashed password."""
    return ph.hash(password)

def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify that a plain text password matches a hashed password."""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False

