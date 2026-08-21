# Phase 3 — Professional UI/UX Product Experience

Phase 3 adds `apps/web`, a bilingual Next.js product experience on top of the Phase 2 FastAPI intelligence engine. The frontend does not calculate eligibility, matching, or ranking scores; it renders the backend’s typed contracts and evidence.

## Product architecture

```text
Next.js App Router
  ├── /[locale]             marketing landing page
  ├── /[locale]/dashboard   Career Radar overview
  ├── /[locale]/jobs        search, filters, and pagination-ready discovery
  ├── /[locale]/jobs/[id]   evidence-rich job detail
  ├── /[locale]/companies   company intelligence table
  ├── /[locale]/onboarding  React Hook Form + Zod profile wizard
  ├── /[locale]/profile     candidate profile and score anatomy
  ├── /[locale]/settings    theme, language, and trust controls
  └── /[locale]/recommendations/[candidateId]/explain
```

`src/lib/api/client.ts` is the only API boundary. TanStack Query owns server state and cache invalidation; TypeScript interfaces mirror the existing Pydantic response contracts. Recommendation scores, reasons, warnings, evidence, and eligibility remain backend-owned.

## Design system

The UI uses a restrained ink/paper palette with indigo as the product accent, mint for positive evidence, amber for uncertainty, and rose for hard warnings. Shared primitives in `src/components/ui` cover buttons, badges, cards, inputs, selects, skeletons, score bars, and empty states. Feature components are organized by dashboard, jobs, recommendations, companies, profile, and onboarding.

The interface is responsive from mobile to desktop, uses semantic landmarks and visible focus rings, and keeps animation limited to page/card entrance and small hover transitions.

## Internationalization and theming

English (`/en`) is the default LTR experience. Persian (`/fa`) uses RTL layout, Persian number/date formatting, and translated product copy. `next-intl` provides the message context; `next-themes` persists light/dark/system preference.

## Local setup

```bash
cd apps/web
npm install
npm run dev
```

Run the FastAPI service separately at `http://localhost:8000`, or set `NEXT_PUBLIC_API_URL`. The API allows the local web origin through `WEB_ORIGIN` (default `http://localhost:3000`). For a complete verification pass:

```bash
npm run lint
npm run test
npm run build
npx playwright test
```

Playwright covers opening the application, English/Persian direction switching, dark mode, and the discovery surface. API-backed flows can run against the fictional Phase 2 demo seed described in `README.md`.
