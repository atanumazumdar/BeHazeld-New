"""
Identity repository — pure data access layer.
No business rules live here; all domain decisions belong in services.
"""
import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.identity import RefreshToken, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── read ─────────────────────────────────────────────────────────────────

    def get_by_id(self, user_id: uuid.UUID) -> User:
        user = self.db.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_by_tenant(self, tenant_id: uuid.UUID) -> list[User]:
        return list(self.db.scalars(select(User).where(User.tenant_id == tenant_id)))

    def count_active_superusers_in_tenant(self, tenant_id: uuid.UUID) -> int:
        """Return the number of active superusers for the given tenant."""
        result = self.db.scalar(
            select(func.count()).where(
                User.tenant_id == tenant_id,
                User.is_superuser.is_(True),
                User.is_active.is_(True),
            )
        )
        return result or 0

    # ── write ─────────────────────────────────────────────────────────────────

    def create(
        self,
        email: str,
        username: str,
        hashed_password: str,
        tenant_id: uuid.UUID,
        is_superuser: bool = False,
    ) -> User:
        if self.get_by_email(email) is not None:
            raise ConflictError(f"User with email '{email}' already exists")
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            is_superuser=is_superuser,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def set_active(self, user_id: uuid.UUID, is_active: bool) -> User:
        user = self.get_by_id(user_id)
        user.is_active = is_active
        self.db.flush()
        return user

    # ── refresh token management ──────────────────────────────────────────────

    def store_refresh_token(
        self, user_id: uuid.UUID, token: str, expires_at: datetime
    ) -> RefreshToken:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(rt)
        self.db.flush()
        return rt

    def get_refresh_token(self, token: str) -> RefreshToken | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

    def revoke_refresh_token(self, token: str) -> None:
        rt = self.get_refresh_token(token)
        if rt is not None:
            rt.revoked_at = datetime.now(timezone.utc)
            self.db.flush()

    def revoke_all_refresh_tokens_for_user(self, user_id: uuid.UUID) -> int:
        """
        Bulk-revoke every active refresh token for a user.
        Called when token reuse is detected — a signal of a possible theft.
        Returns the number of tokens revoked.
        """
        result = self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        self.db.flush()
        return result.rowcount
