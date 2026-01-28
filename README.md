# Bitcoin-analysis

Bitcoin-analysis is a comprehensive crypto-financial data analysis platform. Designed to offer institutional-grade insights to retail traders, it combines a robust data pipeline (ingestion, transformation, aggregation) with a modern user interface.

## 📚 Table of Contents / Table des Matières

- [🇫🇷 Version Française](#-version-française)
  - [Fonctionnalités Principales](#fonctionnalités-principales)
  - [Tutoriel : Pour Commencer](#tutoriel--pour-commencer)
  - [Guides Pratiques](#guides-pratiques)
  - [Explication](#explication)
  - [Référence](#référence)
  - [Roadmap](#roadmap)
- [🇺🇸 English Version](#-english-version)
  - [Key Features](#key-features)
  - [Tutorial: Getting Started](#tutorial-getting-started)
  - [How-to Guides](#how-to-guides)
  - [Explanation](#explanation)
  - [Reference](#reference)
  - [Roadmap (English)](#roadmap-english)
- [📞 Connect With Me](#-connect-with-me)

---

# 🇫🇷 Version Française

Bitcoin-analysis est un projet de pipeline de données pour l'analyse des prix du Bitcoin et d'autres cryptomonnaies. Il ingère des données OHLCV (Open, High, Low, Close, Volume) depuis l'API gratuite de Coinbase, les transforme via DBT selon une architecture médallion (bronze → silver → gold), et calcule des indicateurs comme le RSI. Déployé sur Databricks avec CI/CD GitHub Actions. Objectif : fournir une base de données analysée pour une future application web de visualisation d'indicateurs de marché Bitcoin.

## Fonctionnalités Principales

- **Pipeline de Données Automatisé** : Ingestion quotidienne des données OHLCV via l'API Coinbase et orchestration via Databricks Workflows.
- **Architecture Médallion (Bronze/Silver/Gold)** : Transformation structurée des données avec DBT pour garantir qualité et performance.
- **Calcul d'Indicateurs Techniques** : Génération automatique d'indicateurs comme le RSI, et bientôt le MACD, directement en base de données.
- **Support Multi-Devises** : Analyse des paires BTC/USD, BTC/EUR, ETH/USD, ETH/EUR, ETH/BTC, AAVE/USD.
- **CI/CD Intégré** : Déploiement continu via GitHub Actions vers les environnements Databricks.
- **Application Web (En cours)** : Interface React/Next.js immersive pour la visualisation et l'analyse.

## Stack Technique

<table>
  <tr>
    <td valign="top" width="50%">
      <h3>Backend & Data Engineering</h3>
      <table>
        <tr>
          <th>Technologie</th>
          <th>Usage</th>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></td>
          <td>Langage principal pour le traitement des données et l'orchestration</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Databricks-FF3621?style=for-the-badge&logo=databricks&logoColor=white" alt="Databricks" /></td>
          <td>Plateforme unifiée pour l'exécution Spark, le stockage Delta Lake et les jobs</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white" alt="dbt" /></td>
          <td>Transformation des données (ELT) et gestion des modèles Bronze/Silver/Gold</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" /></td>
          <td>Manipulation et analyse de données pour les datasets en mémoire</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" /></td>
          <td>Framework robuste pour les tests unitaires et d'intégration</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/uv-Astral-purple?style=for-the-badge" alt="uv" /></td>
          <td>Gestionnaire de paquets et de dépendances Python ultra-rapide</td>
        </tr>
      </table>
    </td>
    <td valign="top" width="50%">
      <h3>Frontend</h3>
      <table>
        <tr>
          <th>Technologie</th>
          <th>Usage</th>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" /></td>
          <td>Framework React pour le rendu côté serveur et la génération statique</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" /></td>
          <td>Bibliothèque JavaScript pour la construction d'interfaces utilisateur interactives</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" /></td>
          <td>Sur-ensemble typé de JavaScript pour un code plus fiable et maintenable</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" /></td>
          <td>Framework CSS utilitaire pour un design rapide et responsive</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Chart.js-F5788D?style=for-the-badge&logo=chart.js&logoColor=white" alt="Chart.js" /></td>
          <td>Bibliothèque de visualisation de données pour des graphiques dynamiques</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Jest-C21325?style=for-the-badge&logo=jest&logoColor=white" alt="Jest" /></td>
          <td>Framework de test complet pour l'application Frontend</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Zod-3E67B1?style=for-the-badge&logo=zod&logoColor=white" alt="Zod" /></td>
          <td>Validation de schémas TypeScript-first pour les formulaires et l'API</td>
        </tr>
      </table>
    </td>
  </tr>
</table>

## Tutoriel : Pour Commencer

### Prérequis
- Compte Databricks (édition gratuite disponible)
- Python 3.11+
- uv (gestionnaire de paquets Python)
- Databricks CLI

### Installation
1. Clonez le repo :
   ```bash
   git clone https://github.com/DOX69/Bitcoin-analysis.git
   cd Bitcoin-analysis
   ```

2. Installez uv :
   ```bash
   pip install uv
   ```

3. Compilez les dépendances :
   ```bash
   uv pip compile pyproject.toml -o requirements.txt
   ```

4. Installez Databricks CLI :
   ```bash
   pip install databricks-cli
   ```

### Configuration Databricks
1. Créez un compte Databricks (free tier).
2. Générez un token d'accès dans Databricks (User Settings > Developer > Access tokens).
3. Ajoutez les secrets dans GitHub (Settings > Secrets and variables > Actions) :
   - `DATABRICKS_HOST` : URL de votre workspace (ex: https://dbc-xxxxxx.cloud.databricks.com)
   - `DATABRICKS_TOKEN` : Votre token d'accès

### Premier déploiement
1. Allez dans le dossier dbx_workflow :
   ```bash
   cd dbx_workflow
   ```

2. Validez le bundle :
   ```bash
   databricks bundle validate -t dev -p DEV
   ```

3. Déployez :
   ```bash
   databricks bundle deploy -t dev -p DEV
   ```

4. Lancez le job principal :
   ```bash
   databricks bundle run -t dev -p DEV master_orchestrator_job
   ```

## Guides Pratiques

### Développer et tester en local (DEV)
Pour développer et tester localement sur Databricks DEV :

1. Créez un environnement virtuel avec uv :
   ```bash
   uv venv
   source .venv/bin/activate  # Sur Windows : .venv\Scripts\activate
   ```

2. Installez les dépendances pour les tests locaux :
   ```bash
   uv sync --dev
   ```

3. Assurez-vous d'avoir configuré les secrets GitHub (DATABRICKS_HOST, DATABRICKS_TOKEN) pour le profil DEV.

4. Depuis dbx_workflow :
   ```bash
   cd dbx_workflow
   ```

5. Validez, Déployez et Lancez sur DEV (comme ci-dessus).

Les ressources sont préfixées avec '[dev your_username]' et les jobs sont pausés par défaut.

### Déployer en Production (PROD)
Pour déployer en production avec jobs actifs :

1. Changez la target vers prod :
   ```bash
   databricks bundle validate -t prod -p PROD --var="pauseStatus=UNPAUSED"
   ```

2. Déployez :
   ```bash
   databricks bundle deploy -t prod -p PROD --var="pauseStatus=UNPAUSED"
   ```

3. Lancez le job en prod :
   ```bash
   databricks bundle run -t prod -p PROD master_orchestrator_job
   ```

En prod, le schéma est 'prod.bronze' et les jobs sont actifs (UNPAUSED).

## Explication

### Architecture médallion détaillée
Le projet implémente une architecture médallion pour la gestion des données :

- **Bronze Layer** :
  - Source : API Coinbase gratuite (pas de rate limits, historique complet).
  - Données : OHLCV quotidiennes pour BTC/USD, BTC/EUR, ETH/USD, ETH/EUR, ETH/BTC, AAVE/USD.
  - Stockage : Delta tables dans Databricks Unity Catalog (catalog.dev/schema.bronze ou prod).
  - Ingestion : PySpark job via Databricks bundle, incremental (full pour première run, puis delta depuis dernière date).

- **Silver Layer** :
  - Transformation : DBT models pour nettoyer et structurer (faits quotidiens par crypto).
  - Format : Tables Delta avec partitions temporelles.
  - Macros DBT : create_update_obt_fact_day_crypto pour upsert.

- **Gold Layer** :
  - Agrégations : Modèles DBT pour weekly, monthly, quarterly, yearly aggregations.
  - Indicateurs : RSI calculé via macros DBT (période 14 jours).
  - Analyses : Queries DBT pour explorer résultats.

### Choix technologiques
- **DBT** : ELT framework pour transformations SQL, macros pour logique réutilisable, analyses pour exploration.
- **Databricks** : Plateforme cloud pour exécution PySpark, stockage Delta, jobs orchestrés, Unity Catalog.
- **Coinbase API** : API gratuite sans limites, endpoint /products/{ticker}/candles pour données historiques.
- **GitHub Actions** : CI/CD pour déploiement automatique sur push (main branch).
- **uv** : Gestionnaire de paquets Python rapide pour dépendances.
- **PySpark** : Traitement distribué des données sur Databricks.

## Référence

### Commandes Databricks principales
- `databricks bundle validate -t [dev|prod] -p [DEV|PROD] [--var="pauseStatus=UNPAUSED"]` : Valide la syntaxe du bundle.
- `databricks bundle deploy -t [dev|prod] -p [DEV|PROD] [--var="pauseStatus=UNPAUSED"]` : Déploie le bundle sur Databricks.
- `databricks bundle run -t [dev|prod] -p [DEV|PROD] master_orchestrator_job` : Lance le job principal d'ingestion et transformation.

### Secrets GitHub
- `DATABRICKS_HOST` : URL du workspace Databricks.
- `DATABRICKS_TOKEN` : Token d'accès personnel.

### Points d'API Coinbase
- `GET /products/{ticker}-{currency}/candles` : Récupère données OHLCV historiques (Daily).

## Roadmap

### Application Web React JS
Prochaine étape : développement d'une application web interactive en React JS pour visualiser les indicateurs Bitcoin.

**Fonctionnalités Clés à Venir :**

- **Trading & Portfolio Management** :
  - **Backtesting de Stratégies** : Simulez vos stratégies sur 5 ans d'historique pour valider vos hypothèses avant de trader.
  - **Suivi de Performance en Temps Réel** : P&L dynamique, alertes de prix et rééquilibrage de portefeuille.

- **Intelligence Artificielle & Prévisions** :
  - **Modèles Prédictifs Profonds** : Utilisation de LSTM et Transformers pour anticiper les mouvements de marché à court terme.
  - **Détection d'Anomalies** : Alertes automatiques lors de comportements de marché inhabituels (flash crashes, pompes).

- **Analyse de Sentiment & On-Chain (The "Alpha")** :
  - **Whale Watching** : Suivi en temps réel des mouvements des "baleines" (comptes > 1000 BTC) pour anticiper les ventes massives.
  - **Crypto Greed & Fear Index 2.0** : Agrégation en temps réel du sentiment sur Twitter, Reddit et Google Trends.
  - **Métriques DeFi** : Intégration des taux d'intérêt AAVE/Compound pour optimiser le yield farming.

- **Correlations Macro-Economiques** :
  - Heatmaps de corrélation avec le S&P 500, le Gold, et le DXY pour comprendre l'environnement macro.

---

# 🇺🇸 English Version

Bitcoin-analysis is a data pipeline project for analyzing Bitcoin and other cryptocurrency prices. It ingests OHLCV (Open, High, Low, Close, Volume) data from the free Coinbase API, transforms it via DBT using a medallion architecture (Bronze → Silver → Gold), and calculates indicators like RSI. Deployed on Databricks with CI/CD via GitHub Actions. Goal: provide an analyzed database for a future web application visualizing Bitcoin market indicators.

## Key Features

- **Automated Data Pipeline**: Daily ingestion of OHLCV data via Coinbase API and orchestration via Databricks Workflows.
- **Medallion Architecture (Bronze/Silver/Gold)**: Structured data transformation with DBT to ensure quality and performance.
- **Technical Indicator Calculation**: Automatic generation of indicators like RSI, and soon MACD, directly in the database.
- **Multi-Currency Support**: Analysis of BTC/USD, BTC/EUR, ETH/USD, ETH/EUR, ETH/BTC, AAVE/USD pairs.
- **Integrated CI/CD**: Continuous deployment via GitHub Actions to Databricks environments.
- **Web Application (In Progress)**: Immersive React/Next.js interface for visualization and analysis.

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
          <td>Core language for data processing, scripting, and orchestration</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Databricks-FF3621?style=for-the-badge&logo=databricks&logoColor=white" alt="Databricks" /></td>
          <td>Unified Cloud Platform for Spark execution, Delta Lake storage, and jobs</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white" alt="dbt" /></td>
          <td>Data transformation workflow (ELT) and medallion architecture management</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" /></td>
          <td>Data manipulation and analysis library for in-memory datasets</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" /></td>
          <td>Robust framework for unit and integration testing of data pipelines</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/uv-Astral-purple?style=for-the-badge" alt="uv" /></td>
          <td>Extremely fast Python package installer and dependency manager</td>
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
          <td>React framework for server-side rendering, SSG, and fullstack features</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" /></td>
          <td>JavaScript library for building interactive user interfaces and components</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" /></td>
          <td>Superset of JavaScript adding static typing for better code quality</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" /></td>
          <td>Utility-first CSS framework for rapid, responsive UI styling</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Chart.js-F5788D?style=for-the-badge&logo=chart.js&logoColor=white" alt="Chart.js" /></td>
          <td>Data visualization library for creating responsive and interactive charts</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Jest-C21325?style=for-the-badge&logo=jest&logoColor=white" alt="Jest" /></td>
          <td>Comprehensive testing framework for Frontend logic and components</td>
        </tr>
        <tr>
          <td><img src="https://img.shields.io/badge/Zod-3E67B1?style=for-the-badge&logo=zod&logoColor=white" alt="Zod" /></td>
          <td>TypeScript-first schema declaration and validation library</td>
        </tr>
      </table>
    </td>
  </tr>
</table>

## Tutorial: Getting Started

### Prerequisites
- Databricks Account (free edition available)
- Python 3.11+
- uv (Python package manager)
- Databricks CLI

### Installation
1. Clone the repo:
   ```bash
   git clone https://github.com/DOX69/Bitcoin-analysis.git
   cd Bitcoin-analysis
   ```

2. Install uv:
   ```bash
   pip install uv
   ```

3. Compile dependencies:
   ```bash
   uv pip compile pyproject.toml -o requirements.txt
   ```

4. Install Databricks CLI:
   ```bash
   pip install databricks-cli
   ```

### Databricks Configuration
1. Create a Databricks account (free tier).
2. Generate an access token in Databricks (User Settings > Developer > Access tokens).
3. Add secrets in GitHub (Settings > Secrets and variables > Actions):
   - `DATABRICKS_HOST`: Your workspace URL (e.g., https://dbc-xxxxxx.cloud.databricks.com)
   - `DATABRICKS_TOKEN`: Your access token

### First Deployment
1. Go to the dbx_workflow folder:
   ```bash
   cd dbx_workflow
   ```

2. Validate the bundle:
   ```bash
   databricks bundle validate -t dev -p DEV
   ```

3. Deploy:
   ```bash
   databricks bundle deploy -t dev -p DEV
   ```

4. Run the main job:
   ```bash
   databricks bundle run -t dev -p DEV master_orchestrator_job
   ```

## How-to Guides

### Run in Dev
To develop and test locally on Databricks DEV:

1. Create a virtual environment with uv:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies for local tests:
   ```bash
   uv sync --dev
   ```

3. Ensure GitHub secrets (DATABRICKS_HOST, DATABRICKS_TOKEN) are configured for the DEV profile.

4. From dbx_workflow:
   ```bash
   cd dbx_workflow
   ```

5. Validate, Deploy, and Run on DEV (as above).

Resources are prefixed with '[dev your_username]' and jobs are paused by default.

### Deploy to Prod
To deploy to production with active jobs:

1. Change target to prod:
   ```bash
   databricks bundle validate -t prod -p PROD --var="pauseStatus=UNPAUSED"
   ```

2. Deploy:
   ```bash
   databricks bundle deploy -t prod -p PROD --var="pauseStatus=UNPAUSED"
   ```

3. Run the job in prod:
   ```bash
   databricks bundle run -t prod -p PROD master_orchestrator_job
   ```

In prod, the schema is 'prod.bronze' and jobs are active (UNPAUSED).

## Explanation

### Detailed Medallion Architecture
The project implements a medallion architecture for data management:

- **Bronze Layer**:
  - Source: Free Coinbase API (no rate limits, full history).
  - Data: Daily OHLCV for BTC/USD, BTC/EUR, ETH/USD, ETH/EUR, ETH/BTC, AAVE/USD.
  - Storage: Delta tables in Databricks Unity Catalog.
  - Ingestion: PySpark job via Databricks bundle, incremental mode.

- **Silver Layer**:
  - Transformation: DBT models to clean and structure (daily facts per crypto).
  - Format: Delta tables with time partitions.

- **Gold Layer**:
  - Aggregations: DBT models for weekly, monthly, quarterly, yearly aggregations.
  - Indicators: RSI calculated via DBT macros (14-day period).

### Tech Choices
- **DBT**: ELT framework for SQL transformations.
- **Databricks**: Cloud platform for PySpark execution and Delta storage.
- **Coinbase API**: Free historical data API.
- **GitHub Actions**: CI/CD for automatic deployment.
- **uv**: Fast Python package manager.

## Reference

### Main Databricks Commands
- `databricks bundle validate`: Validates bundle syntax.
- `databricks bundle deploy`: Deploys bundle to Databricks.
- `databricks bundle run`: Runs the main ingestion and transformation job.

## Roadmap (English)

### React JS Web App
Next step: development of an interactive React JS web application to visualize Bitcoin indicators.

**Key Upcoming Features:**

- **Trading & Portfolio Management**:
  - **Strategy Backtesting**: Simulate strategies on 5 years of history.
  - **Real-time Performance Tracking**: Dynamic P&L, price alerts.

- **AI & Forecasts**:
  - **Deep Predictive Models**: LSTM and Transformers for short-term market moves.
  - **Anomaly Detection**: Automatic alerts for unusual market behavior.

- **Sentiment & On-Chain (The "Alpha")**:
  - **Whale Watching**: Real-time tracking of large account movements.
  - **Crypto Greed & Fear Index 2.0**: Real-time sentiment aggregation (Twitter, Reddit).
  - **DeFi Metrics**: Integration of AAVE/Compound interest rates.

- **Macro-Economic Correlations**:
  - Correlation heatmaps with S&P 500, Gold, and DXY.

---

# 📞 Connect With Me

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/mickael-rakotoarinivo/)
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:mickael.rakotoa@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/DOX69)

---

## Run Checks (Development)

Run all tests before checking in code:
- **Windows**: `./check-all.bat`
- **Linux/Mac**: `./check-all`
