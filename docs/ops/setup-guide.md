# Setup guide: accounts and deployment

You perform every step below yourself. Never paste passwords or connection strings into a chat, an issue or a commit.

## 1. GitHub

Create the public repository from this folder (after confirming the name and owner):

```bash
gh repo create ddq-portfolio-dashboard --public --source . --remote origin --push --description "DDQ (Data Driven Quant) Portfolio Risk Analytics Dashboard"
```

Then create the `production` environment: repository Settings → Environments → New environment → `production`.

## 2. Supabase

1. Create a project named `ddq-portfolio-dashboard`. Choose a region and remember it (pick a Render region close to it).
2. Save the database password in a password manager.
3. Project Settings → Database → Connection string. Copy two strings:
   - the **transaction pooler** string (port 6543) for runtime,
   - the **session pooler** string (port 5432) for migrations.
4. URL-encode any special characters in the password (for example `@` becomes `%40`).

## 3. Local `.env`

Copy `.env.example` to `.env`, fill in `DDQ_DATABASE_URL` (transaction pooler) and `DDQ_DATABASE_MIGRATION_URL` (session pooler). `.env` is git-ignored; keep it that way.

## 4. GitHub secrets and variables

```bash
gh secret set DDQ_DATABASE_MIGRATION_URL --env production
```

Paste the session pooler string when prompted. After Render is live, set the repository variable used by the keep-warm workflow:

```bash
gh variable set API_URL --body "https://<your-render-service>.onrender.com"
```

## 5. Render

New → Blueprint → select the repository. When prompted, enter:

- `DDQ_DATABASE_URL`: the transaction pooler string,
- `DDQ_ALLOWED_ORIGINS`: your Vercel production URL (`https://…`, no trailing slash).

`DDQ_TRUSTED_PROXY_HOPS` starts at `1`; the go-live checklist verifies it.

## 6. Vercel

Import the repository, set **Root Directory** to `apps/web`, and add the environment variable `VITE_API_URL` = your Render URL (`https://…onrender.com`). The production build fails on purpose if it is missing.

## 7. Order of operations

1. Publish the repo and add the migration secret (steps 1, 2, 4).
2. Let CI run on `main` so the `migrate` job applies migrations.
3. Create the Render service (its URL is needed by Vercel).
4. Create the Vercel project with `VITE_API_URL`.
5. Put the Vercel URL into Render's `DDQ_ALLOWED_ORIGINS`, then tighten the CSP in `apps/web/vercel.json` to the exact API origin.
6. Run the smoke test:

```bash
uv run python -m ddq_api.ops.smoke --api https://<render-url> --web https://<vercel-url>
```
