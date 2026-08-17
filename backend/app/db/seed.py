"""Create the initial admin and user accounts, once.

Idempotent: existing usernames are left completely alone, so restarting the
container never resets a password an operator has already changed.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models import User, UserRole

logger = logging.getLogger(__name__)


async def seed_users(session: AsyncSession) -> None:
    wanted = (
        (settings.seed_admin_username, settings.seed_admin_password,
         UserRole.ADMIN, "Visioncore Administrator"),
        (settings.seed_user_username, settings.seed_user_password,
         UserRole.USER, "Visioncore User"),
    )
    created = []
    for username, password, role, full_name in wanted:
        if not username or not password:
            continue
        existing = await session.scalar(select(User).where(User.username == username))
        if existing is not None:
            continue
        session.add(User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
            full_name=full_name,
            is_active=True,
        ))
        created.append(f"{username} ({role.value})")

    if created:
        await session.commit()
        logger.info("Seeded accounts: %s", ", ".join(created))
        logger.warning("Change the seeded passwords before using this in production.")
