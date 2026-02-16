# ₿ Bitcoin Analysis Dashboard

## 📋 Variable Catalog (Environments)

This project uses a multi-environment configuration to handle different Databricks workspaces and application settings.

### Available Environments
- **Development**: Used for local feature development and side branches.
- **Production**: Used for the final deployment on the `main` branch.

### Local Development
You can switch between environments locally using specific npm scripts:

- `npm run dev:dev`: Starts the development server with `.env.development` (Default).
- `npm run dev:prod`: Starts the development server with `.env.production` (Prod emulation).

### CI/CD Methodology
- **Side Branches**: CI/CD runs tests against the development configuration.
- **Main Branch**: When merged to `main`, the pipeline automatically builds and deploys using the production configuration.

The current environment is displayed in the dashboard header via the **Environment Badge** (DEV/PROD).

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

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
