from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User


SECRET_KEY = os.getenv("JWT_SECRET", "development-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 120_000
        ).hex()
        return hmac.compare_digest(expected, digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode({"sub": str(user_id), "purpose": "password-reset", "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


def get_reset_user(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "password-reset":
            raise ValueError
        user_id = int(payload.get("sub", ""))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", ""))
    except (JWTError, ValueError, TypeError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
