"""Smoke test duplicate product IDs in checkout payloads.

Run from the backend directory:

    python scripts/test_duplicate_checkout.py

The script creates a temporary SQLite database, applies Alembic migrations,
and calls the checkout route directly. It does not touch backend/store.db.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_dir))

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "duplicate_checkout.db"
        database_url = f"sqlite:///{db_path}"

        env = {**os.environ, "DATABASE_URL": database_url}
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            check=True,
        )

        os.environ["DATABASE_URL"] = database_url

        from fastapi import HTTPException

        from app.database import SessionLocal
        from app.models.order import Order
        from app.models.product import Product
        from app.routers.checkout import create_checkout
        from app.schemas.order import CheckoutCreate

        with SessionLocal() as db:
            db.add(
                Product(
                    name="Duplicate Checkout Test",
                    slug="duplicate-checkout-test",
                    description="Temporary product for duplicate checkout test.",
                    category="Test",
                    image_url="https://example.com/product.jpg",
                    price=Decimal("100.00"),
                    color="Gold",
                    size="Made to measure",
                    inventory_count=5,
                )
            )
            db.commit()

        base_payload = {
            "customer_email": "test@example.com",
            "customer_name": "Test Customer",
            "shipping_address": "123 Test Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001",
            "country": "India",
        }

        with SessionLocal() as db:
            try:
                create_checkout(
                    CheckoutCreate(
                        **base_payload,
                        items=[
                            {"product_id": 1, "quantity": 3},
                            {"product_id": 1, "quantity": 3},
                        ],
                    ),
                    db,
                )
            except HTTPException as exc:
                assert exc.status_code == 400, exc
                db.rollback()
            else:
                raise AssertionError("Expected duplicate quantity to exceed stock")

            product = db.get(Product, 1)
            assert product is not None
            assert product.inventory_count == 5
            assert db.query(Order).count() == 0

        with SessionLocal() as db:
            order = create_checkout(
                CheckoutCreate(
                    **base_payload,
                    items=[
                        {"product_id": 1, "quantity": 2},
                        {"product_id": 1, "quantity": 3},
                    ],
                ),
                db,
            )

            assert order is not None
            assert len(order.items) == 1
            assert order.items[0].product_id == 1
            assert order.items[0].quantity == 5
            assert order.items[0].line_total == Decimal("500.00")
            assert order.total == Decimal("500.00")

            product = db.get(Product, 1)
            assert product is not None
            assert product.inventory_count == 0

        print("OK: duplicate checkout product IDs are merged before stock checks.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
