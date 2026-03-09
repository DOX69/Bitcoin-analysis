This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

### 🗄️ Catalog Switching

You can switch between `prod` and `dev` catalogs using the `--catalog` flag:

```bash
# Run with dev catalog
npm run dev -- --catalog dev

# Run with prod catalog (default)
npm run dev
```

The application defaults to `prod` if no catalog is specified. This is also handled automatically in the CI/CD pipeline based on the branch.

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/basic-features/font-optimization) to automatically optimize and load Inter, a custom Google Font.

## Testing

To run the unit tests for this application using Jest and React Testing Library:

```bash
npm test
# or to run in watch mode:
npm run test:watch
```

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new).

### 🔑 Step-by-Step Setup

1.  **Import Project**: Connect your GitHub account and import the repository.
2.  **Configure Directory**: ⚠️ **IMPORTANT** ⚠️ In the "Build & Development Settings", click "Edit" next to **Root Directory** and select the `app` folder.
3.  **Environment Variables**: Expand the "Environment Variables" section and add the following:

| Variable Name | Description | Default/Value |
|--------------|-------------|---------------|
| `DATABRICKS_HOST` | Databricks Workspace Host | Your workspace URL |
| `DATABRICKS_TOKEN` | Personal Access Token | Your access token |
| `DATABRICKS_PATH` | SQL Warehouse HTTP Path | Your HTTP path |
| `DATABRICKS_CATALOG` | Target Catalog | `prod` (Recommended) |

> [!TIP]
> To test with development data, set `DATABRICKS_CATALOG` to `dev` for **Preview** environments. This allows automatic testing of side branches on Vercel preview URLs.

4.  **Deploy**: Click the **Deploy** button.

### ✅ Verification Checklist

*   [ ] Build logs show no errors.
*   [ ] Application loads at the assigned Vercel URL.
*   [ ] Databricks data (charts/tables) displays correctly.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
