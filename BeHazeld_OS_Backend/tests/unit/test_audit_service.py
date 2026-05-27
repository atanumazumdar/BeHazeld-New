"""
AuditService unit tests — DB calls mocked.

Critical invariants:
1. log_mutation() flushes but does NOT commit — participates in caller's txn.
2. log_and_commit() commits on success; rolls back and swallows on DB error.
3. Payload longer than _PAYLOAD_MAX is truncated before insert.
4. Payload is None-safe (no crash on empty body).
5. All fields (method, endpoint, tenant_id, user_id, ip_address) are passed
   through to the AuditLog model without mutation.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, call

import pytest

from app.models.audit import _PAYLOAD_MAX
from app.services.audit_service import AuditService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service():
    db = MagicMock()
    svc = AuditService(db)
    return svc, db


# ── CRITICAL TEST 1: flush not commit ─────────────────────────────────────────

def test_log_mutation_flushes_not_commits() -> None:
    """log_mutation() must flush (not commit) so it joins the caller's txn."""
    svc, db = _make_service()

    svc.log_mutation(
        method="POST",
        endpoint="/api/v1/sales/bills",
        response_status=201,
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        payload='{"amount": 100}',
    )

    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_log_mutation_adds_audit_log_to_session() -> None:
    """log_mutation() must call db.add() with an AuditLog instance."""
    from app.models.audit import AuditLog
    svc, db = _make_service()

    svc.log_mutation(
        method="DELETE",
        endpoint="/api/v1/catalog/products/abc",
        response_status=204,
    )

    db.add.assert_called_once()
    added_obj = db.add.call_args[0][0]
    assert isinstance(added_obj, AuditLog)


# ── CRITICAL TEST 2: log_and_commit behaviour ─────────────────────────────────

def test_log_and_commit_commits_on_success() -> None:
    """log_and_commit() must commit after a successful flush."""
    svc, db = _make_service()

    svc.log_and_commit(
        method="PATCH",
        endpoint="/api/v1/catalog/variants/xyz",
        response_status=200,
        tenant_id=uuid.uuid4(),
    )

    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_log_and_commit_swallows_db_error() -> None:
    """log_and_commit() must NOT raise even if the DB write fails."""
    svc, db = _make_service()
    db.flush.side_effect = RuntimeError("DB gone away")

    # Must not raise
    svc.log_and_commit(
        method="POST",
        endpoint="/test",
        response_status=500,
    )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ── CRITICAL TEST 3: payload truncation ───────────────────────────────────────

def test_payload_is_truncated_to_max_length() -> None:
    """Payloads longer than _PAYLOAD_MAX chars must be cut before insert."""
    svc, db = _make_service()
    big_payload = "x" * (_PAYLOAD_MAX + 500)   # over the limit

    svc.log_mutation(
        method="POST",
        endpoint="/api/v1/purchases/bills",
        response_status=201,
        payload=big_payload,
    )

    added_obj = db.add.call_args[0][0]
    assert len(added_obj.request_payload) == _PAYLOAD_MAX


def test_payload_within_limit_is_not_truncated() -> None:
    """Payloads ≤ _PAYLOAD_MAX chars must be stored verbatim."""
    svc, db = _make_service()
    small_payload = '{"name": "Priya"}'

    svc.log_mutation(
        method="POST",
        endpoint="/api/v1/sales/customers",
        response_status=201,
        payload=small_payload,
    )

    added_obj = db.add.call_args[0][0]
    assert added_obj.request_payload == small_payload


def test_none_payload_is_safe() -> None:
    """log_mutation() with payload=None must not crash."""
    svc, db = _make_service()

    svc.log_mutation(
        method="DELETE",
        endpoint="/api/v1/admin/users/abc",
        response_status=204,
        payload=None,
    )

    added_obj = db.add.call_args[0][0]
    assert added_obj.request_payload is None


# ── CRITICAL TEST 4: field pass-through ──────────────────────────────────────

def test_all_fields_are_stored_correctly() -> None:
    """All fields passed to log_mutation() must appear unchanged on AuditLog."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    user_id   = uuid.uuid4()

    svc.log_mutation(
        method="post",          # lowercase — should be uppercased
        endpoint="/api/v1/finance/journals",
        response_status=201,
        tenant_id=tenant_id,
        user_id=user_id,
        payload='{"x": 1}',
        ip_address="192.168.1.1",
    )

    obj = db.add.call_args[0][0]
    assert obj.method == "POST"          # uppercased
    assert obj.endpoint == "/api/v1/finance/journals"
    assert obj.response_status == 201
    assert obj.tenant_id == tenant_id
    assert obj.user_id == user_id
    assert obj.ip_address == "192.168.1.1"
