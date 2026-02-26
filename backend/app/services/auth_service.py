"""Authentication service."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token


async def register_user(db: AsyncSession, email: str, username: str, password: str, full_name: str = None) -> User:
    """Register a new user."""
    # Check existing
    result = await db.execute(select(User).where((User.email == email) | (User.username == username)))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("User with this email or username already exists")

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate a user and return the user object if valid."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def generate_tokens(user: User) -> dict:
    """Generate access and refresh tokens for a user."""
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }
