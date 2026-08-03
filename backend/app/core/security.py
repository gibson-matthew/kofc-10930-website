from passlib.context import CryptContext

# bcrypt is the recommended hashing algorithm for passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_PASSWORD_LENGTH = 72


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    Enforces bcrypt's 72-byte maximum password length.
    """
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password cannot exceed 72 characters.")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Enforces bcrypt's 72-byte maximum password length.
    """
    if len(plain_password) > MAX_PASSWORD_LENGTH:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # bcrypt throws ValueError if the stored hash was created
        # from a too-long password or is otherwise invalid.
        return False
