# Clothing Store Backend

Minimal FastAPI backend for the clothing store.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Default API URL:

```txt
http://localhost:8000
```

Useful endpoints:

```txt
GET /health
GET /products
GET /products/{slug}
POST /checkout
```

## Database migrations

Alembic owns schema creation. The FastAPI app does not call
`Base.metadata.create_all()` on startup.

Create a new migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe change"
```

Apply pending migrations:

```bash
alembic upgrade head
```

If you already have a local `store.db` that was created before Alembic, either
rebuild it from migrations:

```bash
rm store.db
alembic upgrade head
python -m app.seed
```

or mark the existing schema as already migrated:

```bash
alembic stamp head
```
