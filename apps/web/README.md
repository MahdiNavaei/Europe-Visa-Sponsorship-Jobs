# Career Radar web app

The Phase 3 frontend is a Next.js 16 application for the Europe Visa Sponsorship Jobs intelligence engine.

## Local development

From this directory:

```bash
npm install
npm run dev
```

The web app runs at `http://localhost:3000`. Start the FastAPI service at `http://localhost:8000` and set `NEXT_PUBLIC_API_URL` when the API is hosted elsewhere.

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

The UI supports `/en` and `/fa`; Persian routes use RTL layout and Persian number/date formatting. Candidate profiles created through onboarding are associated with a local browser identifier so the backend remains the source of truth.

## Verification

```bash
npm run lint
npm run test
npm run build
npm run test:e2e
```
