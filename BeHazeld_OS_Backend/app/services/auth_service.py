"""
AuthService — authentication and session management.

Token rotation strategy
-----------------------
Every refresh produces a new refresh token; the old one is immediately
revoked.  If a *revoked* token is presented again, we treat this as a
possible theft and revoke every active session for that user so a stolen
token cannot be silently rotated elsewhere.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError
from app.models.identity import User
from app.repositories.identity_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.auth import TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.tenant_repo = TenantRepository(db)

    # ── public API ────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> TokenResponse:
        user = self.user_repo.get_by_email(email)
        if user is None or not security.verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive")

        tenant = self.tenant_repo.get_by_id(user.tenant_id)
        if not tenant.is_active:
            raise InvalidCredentialsError("Tenant account is inactive")

        return self._issue_token_pair(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        rt = self.user_repo.get_refresh_token(refresh_token)

        if rt is None:
            raise InvalidCredentialsError("Invalid refresh token")

        # Reuse detection: a revoked token being replayed signals possible theft.
        # Revoke every session for this user so a compromised token goes dead.
        if rt.revoked_at is not None:
            self.user_repo.revoke_all_refresh_tokens_for_user(rt.user_id)
            self.db.commit()
            raise InvalidCredentialsError(
                "Refresh token reuse detected — all sessions have been revoked"
            )

        if not rt.is_valid:
            raise InvalidCredentialsError("Refresh token has expired")

        payload = security.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidCredentialsError("Invalid token type")

        user = self.user_repo.get_by_id(uuid.UUID(payload["sub"]))
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive")

        # Atomic rotation: revoke old, mint new
        self.user_repo.revoke_refresh_token(refresh_token)
        return self._issue_token_pair(user)

    def logout(self, refresh_token: str) -> None:
        self.user_repo.revoke_refresh_token(refresh_token)
        self.db.commit()

    def request_password_reset(self, email: str) -> str | None:
        user = self.user_repo.get_by_email(email)
        if user is None or not user.is_active:
            return None

        return security.create_password_reset_token({
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
        })

    def reset_password(self, reset_token: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise InvalidCredentialsError("Password must be at least 8 characters")

        payload = security.decode_token(reset_token)
        if payload.get("type") != "password_reset":
            raise InvalidCredentialsError("Invalid reset token")

        user = self.user_repo.get_by_id(uuid.UUID(payload["sub"]))
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive")

        self.user_repo.update_password(user.id, security.hash_password(new_password))
        self.user_repo.revoke_all_refresh_tokens_for_user(user.id)
        self.db.commit()

    def get_current_user(self, user_id: uuid.UUID) -> UserResponse:
        user = self.user_repo.get_by_id(user_id)
        return UserResponse.model_validate(user)

    # ── internal helpers ──────────────────────────────────────────────────────

    def _issue_token_pair(self, user: User) -> TokenResponse:
        permissions = self._collect_permissions(user)
        base_claims = {"sub": str(user.id), "tenant_id": str(user.tenant_id)}
        access_claims = {**base_claims, "permissions": permissions}

        access_token = security.create_access_token(access_claims)
        refresh_token = security.create_refresh_token(base_claims)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        self.user_repo.store_refresh_token(user.id, refresh_token, expires_at)
        self.db.commit()
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    def _collect_permissions(self, user: User) -> list[str]:
        codes: list[str] = []
        for role in user.roles:
            for perm in role.permissions:
                if perm.code not in codes:
                    codes.append(perm.code)
        if user.is_superuser:
            codes.append("*")
        return codes
