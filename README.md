# Bitcoin-analysis

Bitcoin-analysis est un projet de pipeline de données pour l'analyse des prix du Bitcoin et d'autres cryptomonnaies. Il ingère des données OHLCV (Open, High, Low, Close, Volume) depuis l'API gratuite de Coinbase, les transforme via DBT selon une architecture médallion (bronze → silver → gold), et calcule des indicateurs comme le RSI. Déployé sur Databricks avec CI/CD GitHub Actions. Objectif : fournir une base de données analysée pour une future application web de visualisation d'indicateurs de marché Bitcoin.

## Tutorial: Getting Started

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

Le pipeline ingère les données BTC/USD, BTC/EUR, ETH/USD, ETH/EUR, ETH/BTC, AAVE/USD depuis Coinbase et les transforme en tables Delta dans Databricks.

### Aperçu de l'architecture
Le projet suit une architecture médallion :
- **Bronze** : Données brutes OHLCV ingérées quotidiennement depuis Coinbase API, stockées en Delta tables.
- **Silver** : Données nettoyées et transformées (faits quotidiens par crypto).
- **Gold** : Agrégations temporelles (hebdomadaire, mensuelle, trimestrielle, annuelle) et indicateurs (RSI).

## How-to Guides

### How to run in dev
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

5. Validez le bundle pour DEV :
   ```bash
   databricks bundle validate -t dev -p DEV
   ```

6. Déployez sur DEV :
   ```bash
   databricks bundle deploy -t dev -p DEV
   ```

7. Lancez le job :
   ```bash
   databricks bundle run -t dev -p DEV master_orchestrator_job
   ```

Les ressources sont préfixées avec '[dev your_username]' et les jobs sont pausés par défaut.

### How to deploy to prod
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

## Explanation

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

## Reference

### Commandes Databricks principales
- `databricks bundle validate -t [dev|prod] -p [DEV|PROD] [--var="pauseStatus=UNPAUSED"]` : Valide la syntaxe du bundle.
- `databricks bundle deploy -t [dev|prod] -p [DEV|PROD] [--var="pauseStatus=UNPAUSED"]` : Déploie le bundle sur Databricks.
- `databricks bundle run -t [dev|prod] -p [DEV|PROD] master_orchestrator_job` : Lance le job principal d'ingestion et transformation.

### Secrets GitHub
- `DATABRICKS_HOST` : URL du workspace Databricks (ex: https://dbc-xxxxxx.cloud.databricks.com).
- `DATABRICKS_TOKEN` : Token d'accès personnel généré dans Databricks (User Settings > Developer > Access tokens).

### Variables d'environnement (TODO - non implémentées)
- `LOG_DIR` : Répertoire pour les logs (actuellement "logs" par défaut).
- `LOG_LEVEL` : Niveau de logging (actuellement "INFO" par défaut).

### Points d'API Coinbase
- `GET /products/{ticker}-{currency}/candles` : Récupère données OHLCV historiques.
  - Paramètres : start, end, granularity (86400 pour daily).
  - Exemple : /products/BTC-USD/candles?start=2020-01-01T00:00:00Z&end=2023-01-01T00:00:00Z&granularity=86400
  - Réponse : [[time, low, high, open, close, volume], ...]

## Roadmap

### Application Web React JS
Prochaine étape : développement d'une application web interactive en React JS pour visualiser les indicateurs Bitcoin.

**Fonctionnalités prévues :**
- **Analyse de marché** : Graphiques prix, volumes, RSI en temps réel.
- **Analyse on-chain** : Métriques blockchain (transactions, hashrate, etc.) - à intégrer ultérieurement.
- **Analyse de sentiment** : Indicateurs sociaux et news - à intégrer ultérieurement.
- **Analyse fondamentale** : Métriques économiques impactant Bitcoin - à intégrer ultérieurement.

**Gestion de portefeuille crypto :**
- Interface interactive pour saisir achats/ventes de Bitcoin.
- Suivi intelligent du portefeuille avec calculs P&L (Profit & Loss).
- Gestion utilisateurs sécurisée avec authentification et autorisations.
- Historique des transactions avec analyses de performance.

L'app consommera les données analysées du pipeline actuel, offrant une expérience utilisateur complète pour traders et investisseurs crypto.

# create requirement.txt
```bash
uv pip compile pyproject.toml -o requirements.txt
```

# test rapide :
```bash
# 1. Simuler ce que le workflow va faire
cd dbx_workflow

# 2. Supprimer vos anciens packages (nettoyer)
pip uninstall -r requirements.txt -y

# 3. Réinstaller depuis le nouveau requirements.txt
pip install -r requirements.txt

# 4. Tester les 3 commandes que le workflow utilise
databricks --version
echo "✅ Step 1: databricks CLI installed"

databricks  databricks workspace list / -p PROD
echo "✅ Step 2: Authentication works"

databricks bundle validate --target prod --profile PROD --var="pauseStatus=UNPAUSED"
echo "✅ Step 3: Bundle validation works"

