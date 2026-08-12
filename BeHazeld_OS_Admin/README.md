# BeHazeld OS Admin

The Admin OS is a Next.js application for catalog, inventory, sales, purchases, and finance operations.

## Windows Self-Hosted Runtime

Production target:

- Public URL: `https://admin.behazeld.com`
- Local runtime: `http://127.0.0.1:3001`
- Backend API: `https://api.behazeld.com`

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=https://api.behazeld.com
```

Install and build:

```powershell
npm install
npm run build
npm run start
```

The IIS `web.config` in this folder reverse-proxies `admin.behazeld.com` to `127.0.0.1:3001`.

