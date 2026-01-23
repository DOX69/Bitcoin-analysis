# 🚀 Pre-Deployment Checklist

Use this checklist to ensure everything is ready before checking your Vercel dashboard.

## Git & Code Preparation
- [ ] **Feature Branch**: You are on `feature/create-web-app`.
- [ ] **Package.json**: Contains `build` ("next build") and `start` ("next start") scripts. (✅ Checked)
- [ ] **Next Config**: `next.config.ts` is present. (✅ Checked)
- [ ] **.gitignore**: Excludes `.env`, `.env.local`, `.next`, `node_modules`. (✅ Checked)
- [ ] **vercel.json**: Created in root to restrict deployment to this branch. (✅ Created)
- [ ] **.env.example**: Created in `app/` folder. (✅ Created)

## Action Items
1.  **Update Files**: Ensure `app/.env.example` matches your requirements if they changed.
2.  **Commit Changes**:
    ```bash
    git add .
    git commit -m "config: prepare Vercel deployment"
    ```
3.  **Push Branch**:
    ```bash
    git push origin feature/create-web-app
    ```

## Vercel Import
- [ ] **Import to Vercel**: Go to [dashboard.vercel.com](https://vercel.com/dashboard) and import the repo.
- [ ] **Root Directory**: Set to `app`.
- [ ] **Env Variables**: Add the 3 Databricks variables.
- [ ] **Deploy**: Click Deploy!
