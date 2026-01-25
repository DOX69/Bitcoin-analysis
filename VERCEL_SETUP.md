# 🚀 Vercel Deployment Setup Guide

This guide will help you deploy your Next.js application (located in the `app` directory) to Vercel.

## 1. Environment Variables needed
You need to configure the following environment variables in Vercel project settings:

| Variable Name | Description | Where to find it |
|--------------|-------------|------------------|
| `DATABRICKS_HOST` | Databricks Workspace Host | Connection Details |
| `DATABRICKS_TOKEN` | Personal Access Token | User Settings > Developer |
| `DATABRICKS_HTTP_PATH` | SQL Warehouse HTTP Path | Connection Details |

## 2. Deploy Steps

1.  **Go to Vercel Dashboard**: [https://vercel.com/dashboard](https://vercel.com/dashboard)
2.  **Add New Project**: click "Add New..." > "Project".
3.  **Import Repository**: Select your GitHub repository (`Bitcoin-analysis`).
4.  **Configure Project**:
    *   **Framework Preset**: Select `Next.js`.
    *   **Root Directory**: ⚠️ **IMPORTANT** ⚠️ click "Edit" and select `app` folder.
5.  **Environment Variables**:
    *   Expand the "Environment Variables" section.
    *   Add the 3 variables listed above with your actual values (copy them from your local `.env.local` if needed).
6.  **Deploy**: Click the **Deploy** button.

## 3. Environments to Check

Once deployed, Vercel will create a deployment URL.

*   ✅ **Production**: The main URL assigned by Vercel.
*   ✅ **Development**: Any subsequent pushes to `<branch-name>` (Preview Deployments).

## 4. Verification Checklist

*   [ ] The deployment build logs show no errors.
*   [ ] The application loads on the provided Vercel URL.
*   [ ] Data from Databricks is loading correctly (check charts/tables).
