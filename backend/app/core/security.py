"""
Security utilities for authentication and password handling.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption for sensitive data (like SIP passwords)
_fernet = None
_encryption_key_valid = True


def get_fernet() -> Fernet:
    """Get or create Fernet instance for encryption.

    If the configured ENCRYPTION_KEY is invalid, generates a temporary key
    and logs a warning. This allows the app to start but new encrypted data
    won't be recoverable if the key changes.
    """
    global _fernet, _encryption_key_valid
    if _fernet is None:
        try:
            _fernet = Fernet(settings.encryption_key.encode())
            logger.info("Fernet encryption initialized with configured key")
        except (ValueError, TypeError) as e:
            # Invalid key format - generate a temporary one
            _encryption_key_valid = False
            temp_key = Fernet.generate_key()
            _fernet = Fernet(temp_key)
            logger.warning(
                f"ENCRYPTION_KEY is invalid ({e}). Generated temporary key. "
                "Set a valid 32-byte base64 Fernet key in ENCRYPTION_KEY env var. "
                "Any data encrypted with this temporary key will be unrecoverable "
                "after restart. Generate a valid key with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
    return _fernet


def is_encryption_key_valid() -> bool:
    """Check if the configured encryption key is valid."""
    # Ensure fernet is initialized
    get_fernet()
    return _encryption_key_valid


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }

    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def encrypt_value(value: str) -> str:
    """Encrypt a sensitive value (like SIP password)."""
    fernet = get_fernet()
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a sensitive value."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_value.encode()).decode()


# Alias for password-specific decryption
def decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted password. Alias for decrypt_value."""
    return decrypt_value(encrypted_password)
