# Clothing Store Frontend

Minimal Next.js storefront for displaying products from the FastAPI backend.

## Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at:

```txt
http://127.0.0.1:8000
```

Override it with:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```
