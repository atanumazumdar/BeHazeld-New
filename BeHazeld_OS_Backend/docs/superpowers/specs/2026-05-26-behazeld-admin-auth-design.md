# BeHazeld Admin Frontend — Phase 7: Foundation & Auth

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Build a professional Next.js 14 App Router admin frontend for BeHazeld E-Commerce OS, secured via httpOnly cookie-based JWT authentication against the existing FastAPI backend.

**Architecture:** Next.js 14 (App Router) in a sibling directory `behazeld-admin/`. Backend FastAPI updated to set httpOnly cookies on login/refresh/logout. Next.js middleware guards admin routes server-side by inspecting the cookie. API client uses `credentials: 'include'` for automatic cookie forwarding.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, Shadcn UI, `fetch` (native), FastAPI (existing backend on `http://localhost:8000`)

---

## 1. Backend Change — httpOnly Cookie Auth

**File:** `BeHazeld E-Commerce OS/app/api/v1/auth.py`

`POST /api/v1/auth/login` and `POST /api/v1/auth/refresh` set two cookies in the response using FastAPI's `Response` object:

| Cookie | Value | Flags | Max-Age |
|---|---|---|---|
| `access_token` | JWT access token | httpOnly, Secure, SameSite=Lax, Path=/ | 30 min |
| `refresh_token` | JWT refresh token | httpOnly, Secure, SameSite=Lax, Path=/ | 7 days |

Both endpoints **also** continue returning the token JSON body (backward-compatible for API consumers).

`POST /api/v1/auth/logout` clears both cookies by setting them with `max_age=0`.

**CORS:** `allow_credentials=True` is already set. Frontend origin `http://localhost:3000` must be in `ALLOWED_ORIGINS`.

---

## 2. Frontend Project Structure

**Location:** `~/Claude Workspace/behazeld-admin/` (sibling to `BeHazeld E-Commerce OS/`)

```
behazeld-admin/
├── app/
│   ├── (auth)/login/page.tsx          ← public login page
│   ├── (admin)/
│   │   ├── layout.tsx                 ← shell with sidebar + topbar
│   │   └── dashboard/page.tsx         ← placeholder landing page
│   ├── globals.css
│   └── layout.tsx                     ← root layout (fonts, providers)
├── components/
│   ├── layout/
│   │   ├── sidebar.tsx                ← collapsible nav sidebar
│   │   ├── sidebar-nav-item.tsx       ← single nav row
│   │   └── topbar.tsx                 ← header with user + tenant
│   └── ui/                            ← Shadcn generated components
├── lib/
│   ├── api-client.ts                  ← fetch wrapper, error handling
│   └── auth-actions.ts                ← server actions: login, logout
├── hooks/
│   └── use-user.ts                    ← client hook: /auth/me data
├── types/
│   └── api.ts                         ← shared API response types
├── middleware.ts                       ← route protection
└── .env.local                         ← NEXT_PUBLIC_API_URL
```

---

## 3. API Client (`lib/api-client.ts`)

- **Base URL:** `process.env.NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`)
- **Credentials:** `credentials: 'include'` on every request (sends cookies automatically)
- **Error handling:** Parses `{ success, error_code, message, correlation_id }` envelope; throws typed `ApiError` class with `errorCode` and `correlationId` fields
- **401 handling:** If any request returns 401, the client calls `POST /auth/refresh`; if refresh succeeds, retries original request once; if refresh fails, redirects to `/login`
- **No token storage:** Client never reads or stores tokens — cookies are browser-managed

---

## 4. Auth Flow

### Login page (`app/(auth)/login/page.tsx`)
- Full-page centered card, warm stone/cream background (B design direction)
- Fields: email + password, submit button with loading state
- On success: `router.push('/dashboard')`
- On failure: displays `message` from error envelope inline (red text, no alert())
- Brand: "BeHazeld OS" wordmark, mahogany-red accent on primary button

### Server Action (`lib/auth-actions.ts`)
- `loginAction(formData)` — POSTs to `/api/v1/auth/login`; cookies are set by the backend response automatically
- `logoutAction()` — POSTs to `/api/v1/auth/logout`; cookies cleared server-side; redirects to `/login`

### Middleware (`middleware.ts`)
- Matcher: all routes except `/login`, `/_next`, `/favicon`
- Reads `access_token` cookie from the request
- If missing → `redirect('/login')`
- If present and path is `/` or `/login` → `redirect('/dashboard')`
- Does NOT verify the JWT signature (that's the backend's job) — presence check is sufficient for UX-level protection; backend will reject invalid tokens with 401 which triggers the refresh cycle

---

## 5. Admin Shell Layout

**Design direction:** B — Warm Neutral Light

| Token | Value |
|---|---|
| Sidebar background | `stone-50` / `#fafaf9` |
| Sidebar border | `stone-200` |
| Active item bg | `stone-100` with `rose-800` text |
| Accent / primary | `rose-800` (#9f1239) — mahogany |
| Topbar | white with `stone-200` border-bottom |
| Content area | `stone-50` |

**Sidebar behaviour:**
- Default: expanded (240px), shows icon + label
- Collapsed: 64px icon rail, tooltips on hover
- Collapse toggle: chevron button at sidebar bottom
- State persisted in `localStorage` key `sidebar-collapsed`

**Navigation items (in order):**
1. Dashboard (LayoutDashboard icon)
2. Catalog (Package icon)
3. Inventory (ArrowLeftRight icon)
4. Sales (ShoppingCart icon)
5. Purchases (Truck icon)
6. Finance (BookOpen icon)
7. Reports (BarChart3 icon)
8. Settings (Settings icon) — bottom-pinned

**Topbar:**
- Left: hamburger / collapse toggle (mobile) + page title (from route)
- Right: search (static for now) + notification bell + user avatar with dropdown (Profile, Logout)
- Shows tenant name (`BeHazeld`) and username from `/auth/me`

---

## 6. Environment Variables

```bash
# behazeld-admin/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 7. Spec Self-Review

- ✅ No TBDs or placeholders
- ✅ Backend change is backward-compatible (body still returned alongside cookies)
- ✅ Middleware does not over-verify (JWT check belongs to backend, not middleware)
- ✅ CORS already configured for credentials; just needs localhost:3000 in ALLOWED_ORIGINS
- ✅ Sidebar state localStorage key defined to prevent hydration mismatch
- ✅ All navigation modules correspond 1:1 with existing backend routers
