def test_get_db_yields_and_closes() -> None:
    from unittest.mock import MagicMock, patch
    import app.db.session  # ensure module is imported before patching
    from app.db.session import get_db
    mock_session = MagicMock()
    mock_session_local = MagicMock(return_value=mock_session)
    with patch("app.db.session.SessionLocal", mock_session_local):
        gen = get_db()
        db = next(gen)
        assert db is mock_session
        try:
            next(gen)
        except StopIteration:
            pass
        mock_session.close.assert_called_once()


def test_base_has_metadata() -> None:
    from app.db.base import Base
    assert Base.metadata is not None


def test_timestamp_mixin_provides_fields() -> None:
    from app.db.base import TimestampMixin
    assert hasattr(TimestampMixin, "created_at")
    assert hasattr(TimestampMixin, "updated_at")
