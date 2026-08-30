# Bitcoin Analysis app

This Next.js dashboard reads processed cryptocurrency data from PostgreSQL.

## Local development

Use Node.js 20 and PostgreSQL 16. Set `DATABASE_URL` in the current shell to a PostgreSQL connection string, then install dependencies and start the app:

```powershell
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Checks

```powershell
npm test
npx tsc --noEmit
npm run lint
```

## Railway deployment

Create the web service manually with these settings:

| Setting | Value |
| --- | --- |
| Builder | Railpack |
| Root directory | `/app` |
| Build command | `npm run build` |
| Start command | `npm run start` |
| Watch path | `app/**` |

Attach a private Railway PostgreSQL service and expose its connection string to the web service as `DATABASE_URL`. Keep database credentials server-side.
