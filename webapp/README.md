# Pharmasi AI Webapp

Struktur Next.js + TypeScript level production dengan App Router.

## Tech Stack

- Next.js 16 (App Router)
- TypeScript
- ESLint
- Tailwind CSS v4

## Folder Structure

```text
webapp/
├── public/
├── src/
│   ├── app/
│   │   ├── api/health/route.ts
│   │   ├── error.tsx
│   │   ├── loading.tsx
│   │   ├── not-found.tsx
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── shared/
│   │   └── ui/
│   ├── config/
│   ├── features/
│   │   └── home/
│   ├── hooks/
│   ├── lib/
│   │   ├── constants/
│   │   ├── http/
│   │   └── utils/
│   ├── server/
│   │   ├── actions/
│   │   ├── repositories/
│   │   └── services/
│   ├── tests/
│   │   ├── e2e/
│   │   ├── integration/
│   │   └── unit/
│   ├── types/
│   └── instrumentation.ts
├── .env.example
├── next.config.ts
├── package.json
└── tsconfig.json
```

## Environment Variables

Salin nilai dari `.env.example` dan sesuaikan untuk environment kamu.

- `NEXT_PUBLIC_APP_URL`
- `NEXT_PUBLIC_API_BASE_URL`
- `BACKEND_API_BASE_URL`
- `AUTH_SECRET`

## Auth Flow

- Frontend auth page mengakses endpoint Next.js `/api/auth/*`.
- Endpoint Next.js meneruskan request ke backend FastAPI `/api/v1/auth/*`.
- Validasi user, verifikasi password, dan query tabel `users` dilakukan di backend FastAPI (PostgreSQL).
- Jika sukses, Next.js membuat session cookie internal untuk proteksi route `/pharmacy`.

## NPM Scripts

- `npm run dev`: Menjalankan aplikasi di mode development.
- `npm run build`: Build production.
- `npm run start`: Menjalankan hasil build production.
- `npm run lint`: Menjalankan ESLint.
- `npm run lint:fix`: Perbaikan otomatis lint issue.
- `npm run typecheck`: Validasi type TypeScript.
- `npm run check`: Menjalankan typecheck dan lint.

## Catatan Arsitektur

- `src/app`: Khusus routing, layout, page, route handler, dan boundary file.
- `src/features`: Modul domain per fitur.
- `src/lib`: Utilitas shared (env, HTTP client, constants).
- `src/server`: Server-side orchestration (service, actions, repositories).
- `src/tests`: Ruang untuk test unit, integration, dan e2e.

