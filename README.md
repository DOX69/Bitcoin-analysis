# Bitcoin-analysis

Bitcoin-analysis is a comprehensive crypto-financial data analysis platform. Designed to provide institutional-grade insights to retail traders, it combines a robust data pipeline (ingestion, transformation, aggregation) with a modern user interface.

## 📚 Table of Contents

- [Key Features](#key-features)
- [Technical Stack](#technical-stack)
- [Tutorial: Getting Started](#tutorial-getting-started)
- [How-to Guides](#how-to-guides)
- [Detailed Architecture](#detailed-architecture)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Verification & QA](#verification--qa)
- [Roadmap](#roadmap)
- [Connect With Me](#connect-with-me)

---

## Key Features

- **Automated Data Pipeline**: Daily ingestion of OHLCV (Open, High, Low, Close, Volume) data from the Coinbase API, orchestrated via Databricks Workflows.
- **Medallion Architecture (Bronze/Silver/Gold)**: Structured data transformation using dbt to ensure high data quality and performance.
- **Technical Indicator Calculation**: Automatic generation of key indicators such as **RSI**, **MACD**, **SMA**, and **EMA** directly within the database.
- **Multi-Currency Support**: Comprehensive analysis for BTC/USD, BTC/EUR, ETH/USD, ETH/EUR, ETH/BTC, and AAVE/USD.
- **Integrated CI/CD**: Continuous integration and deployment via GitHub Actions targeting Databricks environments.
- **Immersive Web Application**: A React/Next.js interface providing dynamic visualizations and deep-dive market analysis.

## Technical Stack

<table>
  <tr>
    <td valign="top" width="50%">
      <h3>Backend & Data Engineering</h3>
      <table>
        <tr>
          <th>Technology</th>
          <th>Usage</th>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></td>
          <td>Core language for data processing, scripting, and orchestration.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Databricks-FF3621?style=for-the-badge&logo=databricks&logoColor=white" alt="Databricks" /></td>
          <td>Unified Cloud Platform for Spark execution, Delta Lake storage, and job scheduling.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white" alt="dbt" /></td>
          <td>ELT workflow management following Medallion architecture patterns.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" /></td>
          <td>Data manipulation library for specialized in-memory analysis.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" /></td>
          <td>Testing framework for ensuring data pipeline integrity.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/uv-Astral-purple?style=for-the-badge" alt="uv" /></td>
          <td>Ultra-fast Python package installer and dependency manager.</td>
        </tr>
      </table>
    </td>
    <td valign="top" width="50%">
      <h3>Frontend</h3>
      <table>
        <tr>
          <th>Technology</th>
          <th>Usage</th>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" /></td>
          <td>React framework for server-side rendering and full-stack capabilities.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" /></td>
          <td>Library for building interactive and component-based user interfaces.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" /></td>
          <td>Type-safe JavaScript flavor for reliable and maintainable code.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" /></td>
          <td>Utility-first CSS framework for rapid and responsive UI styling.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Chart.js-F5788D?style=for-the-badge&logo=chart.js&logoColor=white" alt="Chart.js" /></td>
          <td>Data visualization library for rendering responsive market charts.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Jest-C21325?style=for-the-badge&logo=jest&logoColor=white" alt="Jest" /></td>
          <td>Testing framework for React components and business logic.</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Zod-3E67B1?style=for-the-badge&logo=zod&logoColor=white" alt="Zod" /></td>
          <td>Schema declaration and validation for API responses and forms.</td>
        </tr>
      </table>
    </td>
  </tr>
</table>

## Tutorial: Getting Started

### Prerequisites
- **Databricks Account** (Community Edition works).
- **Python 3.11+**.
- **uv** (Python package manager).
- **Node.js 18+** & **npm**.
- **Databricks CLI**.

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/DOX69/Bitcoin-analysis.git
   cd Bitcoin-analysis
   ```

2. Install `uv`:
   ```bash
   pip install uv
   ```

3. Compile and install dependencies:
   ```bash
   uv sync
   ```

4. Install Databricks CLI:
   ```bash
   pip install databricks-cli
   ```

### Databricks Configuration
1. Generate an Access Token in Databricks (User Settings > Developer > Access tokens).
2. Configure your Databricks profile:
   ```bash
   databricks configure --token
   ```
3. Add GitHub Secrets (Settings > Secrets and variables > Actions):
   - `DATABRICKS_HOST`: Your workspace URL.
   - `DATABRICKS_TOKEN`: Your generated access token.

## How-to Guides

### Development Environment (DEV)
To develop locally and test against a Databricks DEV environment:

1. Activate your virtual environment:
   ```bash
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. Navigate to the `dbx_workflow` folder:
   ```bash
   cd dbx_workflow
   ```
3. Validate, Deploy, and Run:
   ```bash
   databricks bundle validate -t dev -p DEV
   databricks bundle deploy -t dev -p DEV
   databricks bundle run -t dev -p DEV master_orchestrator_job
   ```

### Production Deployment (PROD)
To deploy to production with active scheduling:

1. Validate and deploy with the target set to `prod`:
   ```bash
   databricks bundle deploy -t prod -p PROD --var="pauseStatus=UNPAUSED"
   ```
2. Run the production job:
   ```bash
   databricks bundle run -t prod -p PROD master_orchestrator_job
   ```

## Detailed Architecture

### Medallion Data Design
The project leverages a Medallion architecture inside Delta Lake:

- **Bronze Layer**: Raw ingestion from the Coinbase API. Stores full history OHLCV data for multiple pairs.
- **Silver Layer**: Cleaned and structured data facts. Handles deduplication and schema enforcement using dbt.
- **Gold Layer**: Business-level aggregations and technical indicators. Calculates RSI (14-day), MACD, SMA, and EMA over various timeframes (Daily, Weekly, Monthly, Yearly).

### Engineering Standards
- **dbt**: Used for all SQL transformations and metric calculations.
- **GitHub Actions**: Automated CI/CD pipelines for testing and deployment.
- **Asset Bundles (DABs)**: Databricks Asset Bundles for managing infrastructure as code.

## Pre-Deployment Checklist

Before deploying to production or Vercel:

- [ ] **Run Checks**: Execute `./check-all.bat` (Windows) or `./check-all` (Linux/Mac) and ensure all tests pass.
- [ ] **Environment Variables**: Verify `.env.example` matches current production needs.
- [ ] **Architecture Alignment**: Ensure `dbt` models are successfully built in the `prod` schema.
- [ ] **Vercel Settings**:
  - Root Directory: `app`
  - Required Env Vars: Databricks host, token, and warehouse ID.

## Verification & QA

A general check script is provided to validate the entire repository:

- **Windows**: `./check-all.bat`
- **Linux/Mac**: `./check-all`

This script validates:
1. **Frontend**: Runs `npm test` in the `app/` directory.
2. **Backend**: Runs `pytest` for Databricks workflows.
3. **dbt**: Executes `dbt test` for both `dev` and `prod` targets.

## Roadmap

- **Trading & Portfolio Management**: Strategy backtesting on 5-year historical data.
- **AI-Driven Forecasting**: Deep learning models (LSTM/Transformers) for short-term price movement prediction.
- **Sentiment & On-Chain Analysis**: Whale activity tracking and real-time social sentiment aggregation (Twitter/Reddit).
- **Macro-Economic Integration**: Correlation analysis with S&P 500, Gold, and DXY.

---

## Connect With Me

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mickael-rakotoarinivo/)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:mickael.rakotoa@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/DOX69)
