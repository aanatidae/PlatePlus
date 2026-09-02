# Dashboard Deployment

The production administrator dashboard is a Vercel-hosted React application. It calls the separately hosted FastAPI API on Render. All traffic, prices, transactions, and account balances remain simulated.

## Production Boundary

- Vercel hosts only `frontend/`.
- Render hosts the FastAPI API, Render PostgreSQL database, and the continuous traffic scheduler worker.
- Browser webcam access, YOLO inference, PaddleOCR, local model files, and raw frame processing remain local-only. Set `VITE_ENABLE_LOCAL_WEBCAM=false` for every Vercel deployment.

## Render

Create a new Render Blueprint from this repository's `render.yaml`. Before its first deploy, provide the required `DEMO_ADMIN_PASSWORD` and a comma-separated `CORS_ALLOWED_ORIGINS` value containing the final Vercel URL. Apply migrations with `cd backend && alembic upgrade head`, then run `python -m app.db.seed` once against the Render PostgreSQL database.

The Render API health URL is `/health`. Use the public API URL, including `https://`, as the Vercel API base URL. The scheduler is a separate worker because it must run continuously; it is not a Vercel Function.

## Vercel

Create a Vercel project with `frontend` as its root directory. Vite uses `npm run build` and publishes `dist`. `frontend/vercel.json` preserves direct links to `/dashboard` and `/traffic`.

Set these Production environment variables in Vercel:

| Variable | Value |
| --- | --- |
| `VITE_API_BASE_URL` | The public HTTPS URL of the Render FastAPI service, without a trailing slash. |
| `VITE_ENABLE_LOCAL_WEBCAM` | `false` |

Deploy a preview first. Add its URL to Render's `CORS_ALLOWED_ORIGINS` if it will be used for authenticated testing. After checking login, dashboard data, traffic settings, and direct navigation to `/dashboard` and `/traffic`, promote or deploy to production and add the production URL to CORS.

## Security Notes

- Never commit Render, Vercel, database, or admin credentials.
- Use a unique demo-admin password and Vercel/Render-generated token secret outside local development.
- The frontend receives only the API URL and webcam feature flag; do not place backend secrets in `VITE_*` variables.
