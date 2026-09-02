# Dashboard Deployment

The production administrator dashboard is a Vercel-hosted React application. It calls the separately hosted FastAPI API on Render. All traffic, prices, transactions, and account balances remain simulated.

## Production Boundary

- Vercel hosts only `frontend/`.
- Render hosts the FastAPI API and PostgreSQL database. The free deployment intentionally does not run a continuous traffic scheduler worker.
- Browser webcam access, YOLO inference, PaddleOCR, local model files, and raw frame processing remain local-only. Set `VITE_ENABLE_LOCAL_WEBCAM=false` for every Vercel deployment.

## Render

Create a new Render Blueprint from this repository's `render.yaml`. Before its first deploy, provide the required `DEMO_ADMIN_PASSWORD` and a comma-separated `CORS_ALLOWED_ORIGINS` value containing the final Vercel URL. The API start command applies Alembic migrations and idempotently seeds the synthetic demo records before starting FastAPI, so the free deployment does not require Render shell access or a one-off job.

The Render API health URL is `/health`. Use the public API URL, including `https://`, as the Vercel API base URL.

### Free-tier operation

This Blueprint uses only Render's free Web Service and free Postgres offerings; it deliberately omits the continuous `traffic_scheduler` worker, which requires paid worker compute. Administrators can still run and audit a simulation from `/traffic` using **Run simulation now**, and the saved simulation mode and pricing rules continue to apply.

This is suitable for a capstone demonstration, with these operational limits:

- A free Render web service sleeps after 15 minutes without inbound traffic and takes roughly a minute to wake for the next request.
- The free Render Postgres database is limited to 1 GB and expires after 30 days. Export or reseed the simulated demo data before it expires.
- The dashboard remains live on Vercel, but its API calls can experience the Render cold start after inactivity.

For automatic scheduled simulation or a long-lived database, change to paid infrastructure and restore a separate worker service running `python -m app.traffic_scheduler`.

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
