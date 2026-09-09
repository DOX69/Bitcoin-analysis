# Plan d'action complet — Forecast Bitcoin à 12 mois par quantiles

**Version :** 1.0  
**Granularité disponible :** daily OHLC  
**Historique :** ~10 ans  
**Horizon principal :** 365 jours (~12 mois)  
**Sortie probabiliste :** Q05 / Q25 / Q50 / Q75 / Q95  
**Modèle recommandé :** LightGBM en régression quantile  
**Infrastructure cible :** PostgreSQL + worker Python sur Railway  

---

## 1. Résumé exécutif

L'objectif n'est pas de générer une fausse courbe de prix quotidienne sur les 365 prochains jours, mais d'estimer **la distribution conditionnelle du rendement du Bitcoin à 12 mois**, compte tenu de l'état du marché observé aujourd'hui à partir des données OHLC quotidiennes.

Pour chaque date d'ancrage `t`, le modèle prédit cinq quantiles du rendement logarithmique futur à 365 jours :

- **Q05** : scénario de queue baissière ; 5 % des observations devraient finir sous ce niveau si le modèle est bien calibré ;
- **Q25** : quartile inférieur ;
- **Q50** : médiane du scénario conditionnel ;
- **Q75** : quartile supérieur ;
- **Q95** : scénario de queue haussière ; 95 % des observations devraient finir sous ce niveau.

Les deux intervalles les plus utiles sont donc :

- **Q05–Q95** : intervalle prédictif central à 90 % ;
- **Q25–Q75** : intervalle interquartile à 50 %.

La cible recommandée est :

```text
y_365(t) = ln(close[t + 365] / close[t])
```

Puis chaque quantile de prix est reconstruit par :

```text
price_Qα(t + 365) = close[t] × exp(return_Qα)
```

Le choix recommandé est **cinq modèles LightGBM distincts**, un par quantile :

```text
LightGBM alpha = 0.05  -> Q05
LightGBM alpha = 0.25  -> Q25
LightGBM alpha = 0.50  -> Q50
LightGBM alpha = 0.75  -> Q75
LightGBM alpha = 0.95  -> Q95
```

La granularité daily est suffisante, mais elle impose une contrainte méthodologique majeure : **les targets à 365 jours de deux jours successifs se chevauchent presque complètement**. Les lignes sont nombreuses, mais l'information indépendante est beaucoup plus faible que le nombre brut de lignes. Cela rend la validation temporelle, la purge de 365 jours et la régularisation du modèle absolument centrales.

---

## 2. Décision d'architecture

### 2.1 Architecture recommandée

```text
                    ┌─────────────────────────┐
                    │ Source OHLC Bitcoin     │
                    │ daily / UTC             │
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────┐
│                    PostgreSQL / Railway                  │
│                                                          │
│ btc_daily_ohlc                                           │
│       │                                                  │
│       ├──── validation qualité                           │
│       │                                                  │
│       ▼                                                  │
│ btc_features_daily                                      │
│       │                                                  │
│       ├──── features OHLC                                │
│       ├──── target_return_365d lorsqu'il est observable  │
│       │                                                  │
└───────┬──────────────────────────────────────────────────┘
        │ DATABASE_URL via réseau privé Railway
        ▼
┌────────────────────────────────────────────┐
│ Worker Python / Railway                    │
│                                            │
│ LightGBM quantile                          │
│ ├── Q05                                    │
│ ├── Q25                                    │
│ ├── Q50                                    │
│ ├── Q75                                    │
│ └── Q95                                    │
│                                            │
│ + purged walk-forward backtest             │
│ + calibration                              │
│ + model selection                          │
└───────────────┬────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────┐
│ PostgreSQL                                 │
│                                            │
│ forecast_model_sets                        │
│ forecast_models                            │
│ forecast_backtests                         │
│ btc_forecasts_365d                         │
└────────────────────────────────────────────┘
```

### 2.2 Pourquoi ne pas forcer le ML dans PostgreSQL

Pour ce projet, PostgreSQL doit rester :

- la source de vérité ;
- le moteur de feature engineering déterministe ;
- le stockage des modèles/versionnements ;
- le stockage des prédictions et backtests.

L'entraînement LightGBM peut vivre dans un container Python Railway très léger. Cela évite d'ajouter et maintenir une extension ML lourde dans PostgreSQL et permet d'utiliser plus facilement :

- LightGBM ;
- scikit-learn pour les métriques ;
- Optuna si nécessaire ;
- tests Python ;
- logique de walk-forward personnalisée.

Aucun GPU n'est nécessaire pour environ dix ans de données daily. La quantité de données est faible pour LightGBM.

### 2.3 Stockage des modèles sans volume partagé

LightGBM sait sérialiser un Booster vers une chaîne de caractères et le recharger depuis une chaîne. On peut donc stocker chaque modèle directement dans PostgreSQL en `TEXT`.

Avantages :

- aucun volume Railway partagé nécessaire ;
- le worker d'entraînement et celui d'inférence peuvent être deux services différents ;
- versionnement atomique des cinq quantiles ;
- rollback facile vers un ancien model set ;
- sauvegarde des modèles en même temps que la base PostgreSQL.

---

## 3. Définition exacte du problème

### 3.1 Unité temporelle canonique

Le Bitcoin cote 24/7. Il faut donc imposer une convention unique et immuable pour les candles daily.

**Recommandation : UTC, de 00:00:00 à 23:59:59 UTC.**

Ne jamais construire certaines candles en heure suisse et d'autres en UTC. Toute modification de frontière de journée introduirait un changement silencieux dans les OHLC et donc dans les features.

### 3.2 Date d'ancrage

Une prédiction produite pour la date `t` doit être calculée uniquement **après la clôture complète de la candle daily de `t`**.

À cet instant :

```text
features <= t
close_anchor = close[t]
target_date = t + 365 jours
```

### 3.3 Horizon

Pour conserver une durée fixe et faciliter le backtesting, la V1 utilisera :

```text
horizon_days = 365
```

C'est préférable à `+ 1 year` si l'objectif ML doit toujours avoir la même durée exacte, notamment autour des années bissextiles.

Si l'interface produit doit impérativement signifier « même date dans un an », il est possible de passer ultérieurement à un horizon calendrier de 12 mois. Il faut simplement ne jamais mélanger les deux conventions dans le même historique de backtest.

### 3.4 Target

Target principale : rendement logarithmique à 365 jours.

```text
target_return_365d(t) = ln(close[t + 365] / close[t])
```

Pourquoi le rendement plutôt que le prix brut :

1. un prix de 20 000 USD et un prix de 100 000 USD deviennent comparables ;
2. la cible est moins dépendante du niveau nominal de BTC ;
3. la transformation permet naturellement de reconstruire un prix ;
4. l'échelle logarithmique se comporte mieux avec des variations multiplicatives.

### 3.5 Sortie du modèle

Pour une date `t` :

```text
return_q05
return_q25
return_q50
return_q75
return_q95
```

Puis :

```text
price_q05 = close[t] * exp(return_q05)
price_q25 = close[t] * exp(return_q25)
price_q50 = close[t] * exp(return_q50)
price_q75 = close[t] * exp(return_q75)
price_q95 = close[t] * exp(return_q95)
```

Le modèle doit respecter :

```text
Q05 <= Q25 <= Q50 <= Q75 <= Q95
```

---

## 4. Ce que signifie réellement Q05 / Q25 / Q50 / Q75 / Q95

### Q05

Le modèle estime le 5e percentile conditionnel.

Sur un grand nombre de prédictions comparables et si le modèle est bien calibré :

```text
P(y <= Q05) ≈ 5 %
```

Ce n'est pas « 5 % de probabilité que BTC vaille exactement ce prix ».

### Q25

```text
P(y <= Q25) ≈ 25 %
```

### Q50

Médiane conditionnelle :

```text
P(y <= Q50) ≈ 50 %
```

Q50 est donc la meilleure valeur centrale à afficher comme « scénario médian », plutôt qu'une moyenne potentiellement tirée par les queues de distribution.

### Q75

```text
P(y <= Q75) ≈ 75 %
```

### Q95

```text
P(y <= Q95) ≈ 95 %
```

### Intervalles

```text
[Q05, Q95] -> couverture cible : 90 %
[Q25, Q75] -> couverture cible : 50 %
```

Ces couvertures devront être mesurées explicitement dans le backtest.

---

## 5. Conséquence de la granularité daily sur dix ans

### 5.1 Nombre brut de lignes

Dix ans de candles daily représentent environ :

```text
~3 650 observations
```

Mais ce n'est pas le nombre réel de lignes supervisées exploitables.

Si la feature la plus longue nécessite 365 jours d'historique :

```text
~365 premières lignes perdues
```

Et la target nécessite 365 jours de futur :

```text
~365 dernières lignes non labellisées
```

Ordre de grandeur :

```text
3 650 - 365 - 365 ≈ 2 920 lignes supervisées
```

Le chiffre exact dépendra des dates réelles et des éventuels jours manquants.

### 5.2 Le problème des targets chevauchantes

Considérons :

```text
y(t)   = return entre t et t+365
y(t+1) = return entre t+1 et t+366
```

Ces deux targets partagent presque toute leur période future.

Elles ne constituent donc pas deux expériences indépendantes.

Conséquences :

- ne pas interpréter 2 900 lignes comme 2 900 observations indépendantes ;
- ne pas utiliser de KFold aléatoire ;
- ne pas mélanger passé et futur ;
- ne pas faire de recherche hyperparamétrique agressive ;
- évaluer aussi le modèle sur des ancres espacées, par exemple hebdomadaires ou mensuelles ;
- privilégier la stabilité entre plusieurs périodes historiques plutôt qu'un score global spectaculaire.

### 5.3 Stratégie recommandée

**Entraînement :** conserver les ancres quotidiennes pour ne pas jeter inutilement de données.  
**Évaluation principale :** métriques sur toutes les ancres + métriques secondaires sur une grille espacée de 7 ou 30 jours.  
**Validation :** walk-forward avec purge de 365 jours.

---

## 6. Contrôles qualité des données avant tout ML

Avant de produire des features :

### 6.1 Unicité

Une seule ligne par date.

```sql
SELECT candle_date, COUNT(*)
FROM btc_daily_ohlc
GROUP BY candle_date
HAVING COUNT(*) > 1;
```

Résultat attendu : zéro ligne.

### 6.2 Continuité

BTC cote tous les jours. Il faut détecter les trous.

```sql
WITH bounds AS (
  SELECT MIN(candle_date) AS min_date,
         MAX(candle_date) AS max_date
  FROM btc_daily_ohlc
),
calendar AS (
  SELECT generate_series(min_date, max_date, interval '1 day')::date AS d
  FROM bounds
)
SELECT c.d
FROM calendar c
LEFT JOIN btc_daily_ohlc b
  ON b.candle_date = c.d
WHERE b.candle_date IS NULL
ORDER BY c.d;
```

**Politique recommandée :** backfiller les candles manquantes depuis la source. Ne pas inventer arbitrairement une candle OHLC par interpolation.

### 6.3 Cohérence OHLC

Pour chaque ligne :

```text
high >= open
high >= close
low <= open
low <= close
high >= low
open > 0
high > 0
low > 0
close > 0
```

### 6.4 Candle incomplète

Le pipeline d'inférence ne doit jamais utiliser la candle quotidienne encore en cours.

### 6.5 Source et version

Stocker si possible :

```text
source
symbol
quote_currency
exchange_or_provider
loaded_at
```

Même si le modèle V1 n'utilise qu'une seule série.

---

## 7. Feature engineering V1 — OHLC only

Avec environ 2 900 lignes supervisées, mieux vaut commencer avec **un petit ensemble de features robustes** plutôt que des centaines d'indicateurs techniques corrélés.

Objectif initial : environ **20 à 35 features**.

### 7.1 Rendements / momentum

```text
log_return_1d
log_return_7d
log_return_14d
log_return_30d
log_return_60d
log_return_90d
log_return_180d
log_return_365d
```

Formule :

```text
ln(close[t] / close[t-n])
```

### 7.2 Position par rapport aux moyennes

```text
close_to_sma_20
close_to_sma_50
close_to_sma_100
close_to_sma_200
sma_20_to_sma_50
sma_50_to_sma_200
```

Exemple :

```text
close_to_sma_200 = close / SMA200 - 1
```

### 7.3 Volatilité réalisée

À partir des rendements daily :

```text
realized_vol_7d
realized_vol_30d
realized_vol_90d
realized_vol_180d
realized_vol_365d
```

Pour comparer des fenêtres différentes, annualiser éventuellement :

```text
annualized_vol = stddev(daily_log_returns) * sqrt(365)
```

BTC cote 365 jours par an ; utiliser `sqrt(365)`, pas `sqrt(252)` comme pour un marché actions classique.

### 7.4 Structure de candle

```text
body_return = (close - open) / open
range_pct   = (high - low) / close
upper_wick_pct
lower_wick_pct
close_location
```

Exemple :

```text
close_location = (close - low) / NULLIF(high - low, 0)
```

### 7.5 Drawdown / position historique

```text
ath_to_close
rolling_high_30d_distance
rolling_high_90d_distance
rolling_high_365d_distance
rolling_low_30d_distance
rolling_low_90d_distance
```

Exemple :

```text
drawdown_from_ath = close / all_time_high - 1
```

### 7.6 True Range / ATR normalisé

True Range journalier :

```text
max(
  high - low,
  abs(high - previous_close),
  abs(low - previous_close)
)
```

Puis :

```text
atr_14_pct = avg(true_range, 14d) / close
atr_30_pct = avg(true_range, 30d) / close
```

### 7.7 Volatilité OHLC avancée — V1.1 facultative

Les OHLC permettent d'estimer la volatilité sans volume :

- Parkinson ;
- Garman–Klass ;
- Rogers–Satchell.

Ces features sont intéressantes mais doivent être ajoutées seulement après qu'une V1 minimale soit correctement backtestée.

### 7.8 Features à éviter en V1

Ne pas commencer avec :

- 15 variantes du RSI ;
- dizaines de MACD ;
- centaines de transformations techniques ;
- année civile brute comme feature ;
- identifiant arbitraire de cycle ;
- informations calculées avec des données futures.

Avec seulement dix ans d'historique, augmenter le nombre de features augmente rapidement le risque d'overfit.

---

## 8. Exemple de feature view PostgreSQL

Hypothèse de table :

```sql
CREATE TABLE btc_daily_ohlc (
    candle_date date PRIMARY KEY,
    open  double precision NOT NULL,
    high  double precision NOT NULL,
    low   double precision NOT NULL,
    close double precision NOT NULL
);
```

Exemple de vue matérialisée simplifiée :

```sql
CREATE MATERIALIZED VIEW btc_features_daily AS
WITH lagged AS (
    SELECT
        candle_date,
        open,
        high,
        low,
        close,
        lag(close, 1)   OVER (ORDER BY candle_date) AS close_1d,
        lag(close, 7)   OVER (ORDER BY candle_date) AS close_7d,
        lag(close, 14)  OVER (ORDER BY candle_date) AS close_14d,
        lag(close, 30)  OVER (ORDER BY candle_date) AS close_30d,
        lag(close, 60)  OVER (ORDER BY candle_date) AS close_60d,
        lag(close, 90)  OVER (ORDER BY candle_date) AS close_90d,
        lag(close, 180) OVER (ORDER BY candle_date) AS close_180d,
        lag(close, 365) OVER (ORDER BY candle_date) AS close_365d,
        lead(close, 365) OVER (ORDER BY candle_date) AS close_plus_365d,
        max(close) OVER (
            ORDER BY candle_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS ath_close,
        avg(close) OVER (
            ORDER BY candle_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS sma_20,
        avg(close) OVER (
            ORDER BY candle_date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
        ) AS sma_50,
        avg(close) OVER (
            ORDER BY candle_date ROWS BETWEEN 99 PRECEDING AND CURRENT ROW
        ) AS sma_100,
        avg(close) OVER (
            ORDER BY candle_date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
        ) AS sma_200
    FROM btc_daily_ohlc
),
returns AS (
    SELECT
        *,
        ln(close / NULLIF(close_1d, 0)) AS log_return_1d,
        GREATEST(
            high - low,
            abs(high - close_1d),
            abs(low - close_1d)
        ) AS true_range
    FROM lagged
),
rolling AS (
    SELECT
        *,
        stddev_samp(log_return_1d) OVER (
            ORDER BY candle_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) * sqrt(365.0) AS realized_vol_7d,
        stddev_samp(log_return_1d) OVER (
            ORDER BY candle_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) * sqrt(365.0) AS realized_vol_30d,
        stddev_samp(log_return_1d) OVER (
            ORDER BY candle_date ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
        ) * sqrt(365.0) AS realized_vol_90d,
        stddev_samp(log_return_1d) OVER (
            ORDER BY candle_date ROWS BETWEEN 179 PRECEDING AND CURRENT ROW
        ) * sqrt(365.0) AS realized_vol_180d,
        stddev_samp(log_return_1d) OVER (
            ORDER BY candle_date ROWS BETWEEN 364 PRECEDING AND CURRENT ROW
        ) * sqrt(365.0) AS realized_vol_365d,
        avg(true_range) OVER (
            ORDER BY candle_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) / NULLIF(close, 0) AS atr_14_pct,
        avg(true_range) OVER (
            ORDER BY candle_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) / NULLIF(close, 0) AS atr_30_pct
    FROM returns
)
SELECT
    candle_date,
    close AS anchor_close,

    ln(close / NULLIF(close_1d, 0)) AS ret_1d,
    ln(close / NULLIF(close_7d, 0)) AS ret_7d,
    ln(close / NULLIF(close_14d, 0)) AS ret_14d,
    ln(close / NULLIF(close_30d, 0)) AS ret_30d,
    ln(close / NULLIF(close_60d, 0)) AS ret_60d,
    ln(close / NULLIF(close_90d, 0)) AS ret_90d,
    ln(close / NULLIF(close_180d, 0)) AS ret_180d,
    ln(close / NULLIF(close_365d, 0)) AS ret_365d,

    close / NULLIF(sma_20, 0) - 1 AS close_to_sma_20,
    close / NULLIF(sma_50, 0) - 1 AS close_to_sma_50,
    close / NULLIF(sma_100, 0) - 1 AS close_to_sma_100,
    close / NULLIF(sma_200, 0) - 1 AS close_to_sma_200,
    sma_20 / NULLIF(sma_50, 0) - 1 AS sma_20_to_50,
    sma_50 / NULLIF(sma_200, 0) - 1 AS sma_50_to_200,

    realized_vol_7d,
    realized_vol_30d,
    realized_vol_90d,
    realized_vol_180d,
    realized_vol_365d,
    atr_14_pct,
    atr_30_pct,

    (close - open) / NULLIF(open, 0) AS body_return,
    (high - low) / NULLIF(close, 0) AS range_pct,
    (high - GREATEST(open, close)) / NULLIF(close, 0) AS upper_wick_pct,
    (LEAST(open, close) - low) / NULLIF(close, 0) AS lower_wick_pct,
    (close - low) / NULLIF(high - low, 0) AS close_location,

    close / NULLIF(ath_close, 0) - 1 AS drawdown_from_ath,

    CASE
        WHEN close_plus_365d IS NOT NULL
        THEN ln(close_plus_365d / NULLIF(close, 0))
    END AS target_return_365d
FROM rolling;
```

Notes :

- l'utilisation de `lead(..., 365)` suppose qu'il existe exactement une ligne par jour ;
- si des dates sont manquantes, corriger la série avant de calculer cette target ;
- les premières lignes contiendront des `NULL` jusqu'à disponibilité des fenêtres historiques ;
- les 365 dernières lignes ont une target `NULL`, ce qui est normal en production.

---

## 9. Dataset d'entraînement

Le worker Python lit uniquement les lignes où :

```text
features nécessaires IS NOT NULL
AND target_return_365d IS NOT NULL
```

Exemple :

```sql
SELECT *
FROM btc_features_daily
WHERE ret_365d IS NOT NULL
  AND realized_vol_365d IS NOT NULL
  AND target_return_365d IS NOT NULL
ORDER BY candle_date;
```

Les colonnes suivantes ne doivent pas être utilisées comme features :

```text
candle_date
anchor_close
target_return_365d
```

`anchor_close` sert à reconstruire les prix et aux analyses, mais le niveau nominal de prix n'est pas nécessaire dans la V1.

---

## 10. Modèle LightGBM quantile

LightGBM supporte nativement :

```text
objective = quantile
alpha = <quantile>
```

Créer cinq modèles :

```python
QUANTILES = [0.05, 0.25, 0.50, 0.75, 0.95]
```

Squelette :

```python
from lightgbm import LGBMRegressor

model = LGBMRegressor(
    objective="quantile",
    alpha=0.50,
    n_estimators=600,
    learning_rate=0.03,
    num_leaves=15,
    max_depth=5,
    min_child_samples=60,
    subsample=0.85,
    colsample_bytree=0.85,
    reg_alpha=1.0,
    reg_lambda=3.0,
    random_state=42,
    n_jobs=-1,
)
```

Ces hyperparamètres sont un **point de départ**, pas des valeurs finales.

### Philosophie de régularisation

Le dataset étant petit :

- arbres peu profonds ;
- peu de feuilles ;
- `min_child_samples` relativement élevé ;
- régularisation L1/L2 ;
- learning rate faible ;
- nombre limité de features.

La priorité est la robustesse hors échantillon, pas l'optimisation du train score.

---

## 11. Recherche d'hyperparamètres

### 11.1 Ne pas faire de gros AutoML

Avec ~10 ans daily et des labels très chevauchants, une recherche de centaines ou milliers d'essais peut simplement optimiser le bruit du backtest.

### 11.2 Recherche recommandée

Ordre de grandeur : 20 à 50 essais par phase de recherche, avec walk-forward uniquement.

Espace raisonnable :

```text
num_leaves:         5 -> 31
max_depth:          3 -> 6
min_child_samples:  30 -> 150
learning_rate:      0.01 -> 0.05
n_estimators:       200 -> 1500
subsample:          0.70 -> 1.00
colsample_bytree:   0.60 -> 1.00
reg_alpha:          0 -> 10
reg_lambda:         0 -> 10
```

### 11.3 Méthode

L'objectif d'optimisation est la moyenne des **pinball losses** sur les folds walk-forward.

Ne jamais choisir les paramètres sur un split aléatoire.

---

## 12. Validation temporelle : règle anti-leakage fondamentale

### 12.1 Pourquoi un simple split chronologique ne suffit pas

Une observation d'entraînement ancrée au jour `t` utilise comme label le prix de `t+365`.

Si la période de test commence au jour `T`, toute observation d'entraînement doit respecter :

```text
t + 365 < T
```

Sinon le label d'entraînement contient des prix provenant de la période de test.

### 12.2 Purge obligatoire

Pour chaque fold :

```text
latest_train_anchor <= test_start - 365 jours
```

Visuellement :

```text
TRAIN ANCHORS                PURGE / GAP              TEST ANCHORS
───────────────|────────────────────────────────|─────────────────
               <----------- 365 jours ---------->
```

Cette purge n'est pas optionnelle.

### 12.3 Walk-forward expanding window

Exemple conceptuel pour une série couvrant environ 2016–2026 :

```text
Fold 1
Train anchors : début -> fin 2019
Purge         : 365 jours
Test anchors  : 2021

Fold 2
Train anchors : début -> fin 2020
Purge         : 365 jours
Test anchors  : 2022

Fold 3
Train anchors : début -> fin 2021
Purge         : 365 jours
Test anchors  : 2023

Fold 4
Train anchors : début -> fin 2022
Purge         : 365 jours
Test anchors  : 2024

Fold 5
Train anchors : début -> fin 2023
Purge         : 365 jours
Test anchors  : 2025, dans la mesure où les targets sont aujourd'hui réalisées
```

Les dates exactes devront être générées à partir de la date min/max réellement disponible dans PostgreSQL.

### 12.4 Dernière date réellement backtestable

À une date courante `D`, une prédiction historique à 12 mois n'est évaluable que si :

```text
anchor_date <= D - 365 jours
```

Les prédictions plus récentes restent « pending » jusqu'à maturité de leur target.

---

## 13. Évaluation : métriques obligatoires

### 13.1 Pinball loss — métrique primaire

Pour chaque quantile α :

```text
Lα(y, q) =
  α × (y - q)          si y >= q
  (1 - α) × (q - y)    si y < q
```

À calculer séparément pour :

```text
Q05
Q25
Q50
Q75
Q95
```

Puis moyenne pondérée ou non pondérée des cinq quantiles comme score synthétique.

### 13.2 Calibration de chaque quantile

Pour chaque α :

```text
coverage_α = mean(y_true <= q_pred_α)
```

Attendu :

```text
Q05 -> ~0.05
Q25 -> ~0.25
Q50 -> ~0.50
Q75 -> ~0.75
Q95 -> ~0.95
```

### 13.3 Couverture des intervalles

```text
coverage_90 = mean(Q05 <= y <= Q95)
coverage_50 = mean(Q25 <= y <= Q75)
```

Cibles :

```text
coverage_90 ≈ 90 %
coverage_50 ≈ 50 %
```

### 13.4 Sharpness

Un intervalle prédictif peut atteindre une bonne couverture simplement en devenant énorme.

Il faut donc mesurer aussi :

```text
width_90 = Q95 - Q05
width_50 = Q75 - Q25
```

Le bon modèle cherche à être :

- calibré ;
- mais aussi aussi étroit que raisonnablement possible.

### 13.5 Quantile crossing rate

Avant post-processing :

```text
crossing_rate = proportion des prédictions où
Q05 > Q25
OR Q25 > Q50
OR Q50 > Q75
OR Q75 > Q95
```

Le taux final exposé en production doit être 0 %.

### 13.6 Métriques secondaires

Pour Q50 :

- MAE du rendement à 365 jours ;
- directional accuracy : signe de Q50 vs signe du rendement réalisé ;
- erreur de prix médian reconstruite, uniquement comme métrique secondaire.

---

## 14. Évaluation anti-illusion due au chevauchement

Les métriques seront calculées de deux manières.

### Niveau A — toutes les ancres daily

Permet de mesurer le comportement opérationnel du modèle pour une prédiction produite chaque jour.

### Niveau B — ancres espacées

Recalculer les mêmes métriques sur :

```text
1 ancre tous les 7 jours
```

et idéalement :

```text
1 ancre tous les 30 jours
```

Cela réduit la domination de séries de targets presque identiques.

Le dashboard de backtest doit afficher les deux vues.

### Interprétation

Si le modèle paraît excellent en daily mais perd tout avantage sur les ancres mensuelles, c'est un signal d'overfit ou d'illusion statistique.

---

## 15. Baselines obligatoires

Un modèle ML n'a de valeur que s'il bat des alternatives simples.

### Baseline 1 — quantiles historiques inconditionnels

À chaque fold, calculer les quantiles uniquement sur le train :

```sql
SELECT
    percentile_cont(0.05) WITHIN GROUP (ORDER BY target_return_365d) AS q05,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY target_return_365d) AS q25,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY target_return_365d) AS q50,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY target_return_365d) AS q75,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY target_return_365d) AS q95
FROM train_dataset;
```

Ce baseline dit en substance :

> « Sans tenir compte du régime actuel, quelle était historiquement la distribution des rendements BTC à 365 jours ? »

### Baseline 2 — médiane zéro

Pour le centre de distribution uniquement :

```text
Q50 return = 0
```

Cela correspond à un prix médian futur égal au prix actuel.

### Baseline 3 — modèle linéaire simple, facultatif

Une régression quantile linéaire sur un sous-ensemble minimal de features peut servir de contrôle de complexité.

### Skill score

Pour chaque quantile :

```text
skill = 1 - pinball_loss_model / pinball_loss_baseline
```

Interprétation :

```text
skill > 0 -> ML meilleur que baseline
skill = 0 -> équivalent
skill < 0 -> baseline meilleure
```

---

## 16. Critères Go / No-Go de la V1

Le modèle ne doit pas être promu simplement parce qu'il « semble plausible ».

### Go si

- pinball skill positif face à la baseline historique sur la majorité des folds ;
- avantage agrégé positif sur au moins 4 quantiles sur 5 ;
- aucune dégradation majeure persistante sur un quantile ;
- calibration raisonnable de Q05/Q25/Q50/Q75/Q95 ;
- couverture Q05–Q95 proche de 90 % ;
- couverture Q25–Q75 proche de 50 % ;
- résultats cohérents sur la grille daily et les ancres espacées ;
- quantile crossing final = 0 ;
- comportement stable entre régimes de marché différents.

### No-Go si

- performance uniquement bonne sur le train ;
- un seul fold explique tout le gain ;
- le modèle ne bat pas les quantiles historiques ;
- intervalle Q05–Q95 trop étroit et sous-calibré ;
- intervalle tellement large qu'il n'apporte aucune information ;
- résultats qui s'effondrent sur les ancres mensuelles ;
- changements mineurs d'hyperparamètres produisant des prévisions radicalement différentes.

---

## 17. Quantile crossing

Cinq modèles indépendants peuvent théoriquement produire :

```text
Q25 > Q50
```

ou :

```text
Q75 > Q95
```

### MVP

Après prédiction, ordonner les cinq sorties :

```python
ordered = sorted([q05, q25, q50, q75, q95])
q05, q25, q50, q75, q95 = ordered
```

Toujours stocker :

```text
had_quantile_crossing = true/false
```

avant correction.

### V2

Si les crossings sont fréquents :

- recalibrage monotone ;
- rearrangement/isotonic post-processing ;
- approche multi-quantile non-crossing.

Un taux de crossing élevé est lui-même un signal d'instabilité du modèle.

---

## 18. Recalibration

Même si LightGBM optimise une quantile loss, les quantiles hors échantillon peuvent être mal calibrés.

Après plusieurs folds walk-forward, comparer :

```text
quantile nominal -> coverage observée
0.05             -> ?
0.25             -> ?
0.50             -> ?
0.75             -> ?
0.95             -> ?
```

Exemple problématique :

```text
Q95 nominal = 95 %
coverage observée = 86 %
```

Le modèle est alors trop optimiste / intervalle supérieur trop étroit.

**V1 :** mesurer et afficher la calibration sans complexifier prématurément.  
**V1.1/V2 :** appliquer une couche de calibration sur les prédictions out-of-fold si l'historique est suffisant.

---

## 19. Schéma PostgreSQL proposé

### 19.1 Model sets

Un model set représente les cinq modèles entraînés ensemble.

```sql
CREATE TABLE forecast_model_sets (
    model_set_id uuid PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    horizon_days integer NOT NULL CHECK (horizon_days = 365),
    feature_version text NOT NULL,
    training_code_version text NOT NULL,
    train_anchor_start date NOT NULL,
    train_anchor_end date NOT NULL,
    latest_target_date_used date NOT NULL,
    validation_summary jsonb NOT NULL,
    is_active boolean NOT NULL DEFAULT false
);
```

### 19.2 Modèles LightGBM

```sql
CREATE TABLE forecast_models (
    model_set_id uuid NOT NULL REFERENCES forecast_model_sets(model_set_id),
    quantile numeric(4,3) NOT NULL,
    model_text text NOT NULL,
    hyperparameters jsonb NOT NULL,
    metrics jsonb NOT NULL,
    best_iteration integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (model_set_id, quantile),
    CHECK (quantile IN (0.05, 0.25, 0.50, 0.75, 0.95))
);
```

### 19.3 Prévisions

```sql
CREATE TABLE btc_forecasts_365d (
    forecast_date date PRIMARY KEY,
    target_date date NOT NULL,
    anchor_close double precision NOT NULL,

    return_q05 double precision NOT NULL,
    return_q25 double precision NOT NULL,
    return_q50 double precision NOT NULL,
    return_q75 double precision NOT NULL,
    return_q95 double precision NOT NULL,

    price_q05 double precision NOT NULL,
    price_q25 double precision NOT NULL,
    price_q50 double precision NOT NULL,
    price_q75 double precision NOT NULL,
    price_q95 double precision NOT NULL,

    model_set_id uuid NOT NULL REFERENCES forecast_model_sets(model_set_id),
    had_quantile_crossing boolean NOT NULL,
    generated_at timestamptz NOT NULL DEFAULT now(),

    realized_close double precision,
    realized_return double precision,
    matured_at timestamptz,

    CHECK (price_q05 <= price_q25),
    CHECK (price_q25 <= price_q50),
    CHECK (price_q50 <= price_q75),
    CHECK (price_q75 <= price_q95)
);
```

### 19.4 Backtests

```sql
CREATE TABLE forecast_backtest_folds (
    model_set_id uuid NOT NULL,
    fold_id text NOT NULL,
    train_start date NOT NULL,
    train_end date NOT NULL,
    test_start date NOT NULL,
    test_end date NOT NULL,
    purge_days integer NOT NULL DEFAULT 365,
    metrics_daily jsonb NOT NULL,
    metrics_weekly_anchor jsonb,
    metrics_monthly_anchor jsonb,
    PRIMARY KEY (model_set_id, fold_id)
);
```

---

## 20. Sérialisation LightGBM dans PostgreSQL

Lors de l'entraînement :

```python
model.fit(X_train, y_train)
model_text = model.booster_.model_to_string()
```

Stocker `model_text` dans `forecast_models.model_text`.

Lors de l'inférence :

```python
import lightgbm as lgb

booster = lgb.Booster(model_str=model_text)
prediction = booster.predict(X_latest)[0]
```

Ce mécanisme permet à PostgreSQL de rester le registre central des modèles.

---

## 21. Organisation du code

```text
btc-forecast/
├── pyproject.toml
├── Dockerfile
├── README.md
├── src/
│   └── btc_forecast/
│       ├── config.py
│       ├── db.py
│       ├── dataset.py
│       ├── features.py
│       ├── splits.py
│       ├── metrics.py
│       ├── baselines.py
│       ├── train.py
│       ├── predict.py
│       ├── evaluate.py
│       ├── serialize.py
│       └── cli.py
├── sql/
│   ├── 001_tables.sql
│   ├── 002_features.sql
│   └── 003_indexes.sql
└── tests/
    ├── test_target_alignment.py
    ├── test_purged_split.py
    ├── test_no_future_features.py
    ├── test_quantile_order.py
    ├── test_metrics.py
    └── test_serialization.py
```

---

## 22. CLI recommandée

Un même Docker image peut exposer plusieurs commandes :

```bash
python -m btc_forecast.cli validate-data
python -m btc_forecast.cli refresh-features
python -m btc_forecast.cli backtest
python -m btc_forecast.cli train
python -m btc_forecast.cli predict
python -m btc_forecast.cli mature-forecasts
```

Pour Railway, on peut déployer la même image plusieurs fois avec des start commands différents.

---

## 23. Railway — services recommandés

### 23.1 PostgreSQL

Conserver la base existante.

Le worker ML doit se connecter à PostgreSQL via le réseau privé Railway lorsque les services sont dans le même projet/environnement.

### 23.2 Trainer

Service :

```text
btc-forecast-trainer
```

Rôle :

```text
refresh features
-> validate dataset
-> run backtest/tuning si nécessaire
-> train Q05/Q25/Q50/Q75/Q95
-> stocker le model set
-> activer atomiquement le nouveau model set
-> exit
```

### 23.3 Predictor

Service :

```text
btc-forecast-predictor
```

Rôle quotidien :

```text
vérifier candle complète
-> refresh dernière feature
-> charger model set actif
-> prédire 5 quantiles
-> corriger crossing si nécessaire
-> reconstruire les 5 prix
-> INSERT forecast
-> exit
```

### 23.4 Maturation

Le même predictor peut également mettre à jour les forecasts vieux de 365 jours :

```text
realized_close
realized_return
matured_at
```

Cela permet un monitoring live de calibration.

---

## 24. Fréquence de calcul

### Inference

**1 fois par jour**, après clôture et ingestion de la candle UTC.

Le modèle n'a pas besoin d'être réentraîné pour produire une nouvelle prédiction daily.

### Retraining

**1 fois par mois** pour commencer.

Pourquoi :

- horizon de 365 jours ;
- seulement ~30 nouvelles targets deviennent observables par mois ;
- ces nouvelles targets se chevauchent fortement ;
- un retrain journalier apporte peu d'information supplémentaire.

### Full backtest / hyperparameter search

Pas nécessaire à chaque retrain.

Proposition :

```text
mensuel      -> retrain avec hyperparamètres approuvés
trimestriel  -> backtest complet + éventuelle retune
```

Si le modèle est encore en phase R&D, exécuter le backtest complet manuellement à chaque modification de features ou code.

---

## 25. Cron Railway et robustesse

Les tâches planifiées Railway doivent terminer leur processus après le travail. Une exécution suivante peut être ignorée si la précédente tourne toujours.

Chaque job doit donc :

- fermer ses connexions DB ;
- retourner un exit code non nul en cas d'erreur ;
- être idempotent ;
- ne pas laisser de thread/service web actif ;
- utiliser un lock applicatif ou PostgreSQL.

Exemple de verrou :

```sql
SELECT pg_try_advisory_lock(hashtext('btc_forecast_train'));
```

Si `false`, le job quitte proprement sans lancer un second entraînement concurrent.

Les schedules Railway sont évalués en UTC. Cela convient bien puisque les candles seront également normalisées en UTC.

---

## 26. Activation atomique d'un model set

Ne jamais activer Q05 puis Q25 puis Q50 séparément.

Les cinq modèles doivent être promus ensemble.

Transaction :

```sql
BEGIN;

UPDATE forecast_model_sets
SET is_active = false
WHERE is_active = true;

UPDATE forecast_model_sets
SET is_active = true
WHERE model_set_id = :new_model_set_id;

COMMIT;
```

Avant activation, vérifier qu'il existe exactement cinq modèles :

```text
0.05
0.25
0.50
0.75
0.95
```

---

## 27. Pipeline d'entraînement détaillé

```text
1. Lock du job
2. Vérification qualité data
3. Refresh de btc_features_daily
4. Extraction dataset mature
5. Vérification du schéma des features
6. Construction des folds purgés
7. Calcul des baselines par fold
8. Entraînement Q05 sur chaque fold
9. Entraînement Q25 sur chaque fold
10. Entraînement Q50 sur chaque fold
11. Entraînement Q75 sur chaque fold
12. Entraînement Q95 sur chaque fold
13. Calcul pinball/calibration/coverage
14. Calcul métriques daily/weekly/monthly
15. Quantile crossing analysis
16. Comparaison aux baselines
17. Application des critères Go/No-Go
18. Fit final des 5 modèles sur tout historique mature
19. Sérialisation des 5 modèles
20. INSERT model_set + models + metrics
21. Activation atomique si critères satisfaits
22. Génération éventuelle du forecast courant
23. Commit
24. Unlock / fermeture DB / exit
```

---

## 28. Squelette Python du backtest purgé

```python
from dataclasses import dataclass
from datetime import timedelta
import pandas as pd

HORIZON_DAYS = 365

@dataclass
class Fold:
    train: pd.DataFrame
    test: pd.DataFrame


def make_fold(df: pd.DataFrame, test_start, test_end) -> Fold:
    test_start = pd.Timestamp(test_start)
    test_end = pd.Timestamp(test_end)

    latest_train_anchor = test_start - pd.Timedelta(days=HORIZON_DAYS)

    train = df[df["candle_date"] < latest_train_anchor].copy()
    test = df[
        (df["candle_date"] >= test_start)
        & (df["candle_date"] <= test_end)
    ].copy()

    # Règle critique : aucune target de train ne doit entrer dans la période test.
    assert (
        train["candle_date"].max() + pd.Timedelta(days=HORIZON_DAYS)
        < test_start
    )

    return Fold(train=train, test=test)
```

La logique finale devra gérer précisément les inclusions/exclusions de bornes, mais l'invariant est celui-ci :

```text
train_anchor + 365 < test_start
```

---

## 29. Squelette Python des cinq quantiles

```python
import lightgbm as lgb
from sklearn.metrics import mean_pinball_loss

QUANTILES = [0.05, 0.25, 0.50, 0.75, 0.95]

BASE_PARAMS = {
    "objective": "quantile",
    "n_estimators": 600,
    "learning_rate": 0.03,
    "num_leaves": 15,
    "max_depth": 5,
    "min_child_samples": 60,
    "subsample": 0.85,
    "subsample_freq": 1,
    "colsample_bytree": 0.85,
    "reg_alpha": 1.0,
    "reg_lambda": 3.0,
    "random_state": 42,
    "n_jobs": -1,
}

models = {}
predictions = {}

for q in QUANTILES:
    model = lgb.LGBMRegressor(
        **BASE_PARAMS,
        alpha=q,
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    loss = mean_pinball_loss(y_test, y_pred, alpha=q)

    models[q] = model
    predictions[q] = y_pred
```

---

## 30. Reconstruction des prix

```python
import numpy as np

pred_returns = np.array([
    pred_q05,
    pred_q25,
    pred_q50,
    pred_q75,
    pred_q95,
])

had_crossing = not np.all(np.diff(pred_returns) >= 0)

# MVP monotonic post-processing
pred_returns = np.sort(pred_returns)

pred_prices = anchor_close * np.exp(pred_returns)
```

Grâce à la monotonie de `exp`, l'ordre des quantiles de rendement reste l'ordre des quantiles de prix.

---

## 31. Exemple d'output API / application

```json
{
  "forecastDate": "2026-09-06",
  "targetDate": "2027-09-06",
  "horizonDays": 365,
  "anchorClose": 100000,
  "returns": {
    "q05": -0.55,
    "q25": -0.18,
    "q50": 0.21,
    "q75": 0.62,
    "q95": 1.05
  },
  "prices": {
    "q05": 57695,
    "q25": 83527,
    "q50": 123368,
    "q75": 185896,
    "q95": 285765
  },
  "modelSetId": "..."
}
```

**Valeurs purement illustratives — pas des prévisions BTC réelles.**

Dans l'interface, afficher plutôt :

```text
Horizon : 12 mois

Q05  queue baissière        $57.7k
Q25  quartile inférieur     $83.5k
Q50  scénario médian       $123.4k
Q75  quartile supérieur    $185.9k
Q95  queue haussière       $285.8k

Intervalle central 50 % : $83.5k – $185.9k
Intervalle central 90 % : $57.7k – $285.8k
```

Éviter les formulations :

```text
"95 % de chance que BTC atteigne Q95"
```

Ce n'est pas l'interprétation correcte d'un quantile.

---

## 32. Monitoring en production

Une prédiction 365d ne peut être évaluée qu'un an après sa production.

Le monitoring comporte donc deux couches.

### Court terme — immédiatement disponible

- job réussi/échoué ;
- données complètes ;
- nombre de features NULL ;
- modèle actif présent ;
- quantile crossing ;
- amplitude Q05–Q95 ;
- drift des features ;
- différence entre prévision du jour et de la veille.

### Long terme — après maturation

- pinball loss par quantile ;
- calibration ;
- coverage 50 % ;
- coverage 90 % ;
- sharpness ;
- directional accuracy Q50 ;
- performance par model set.

---

## 33. Feature drift

Même sans avoir la target future, on peut détecter si le marché entre dans une zone de features jamais vue auparavant.

Exemples :

- volatilité 30d au-delà du 99e percentile de train ;
- drawdown hors plage historique ;
- momentum 365d extrême ;
- plusieurs features hors bornes historiques simultanément.

Stocker avec chaque model set :

```text
feature_min
feature_max
feature_p01
feature_p50
feature_p99
```

Si une prédiction est massivement hors distribution, l'UI peut signaler une confiance moindre sans modifier artificiellement les quantiles.

---

## 34. Reproductibilité

Chaque model set doit être traçable jusqu'à :

```text
Git commit SHA
feature_version
LightGBM version
Python version
training dates
hyperparameters
random seed
list of feature names in exact order
data quality report
fold definitions
baseline metrics
model metrics
```

Le modèle ne doit jamais dépendre implicitement de l'ordre courant des colonnes SQL.

Stocker la liste des features dans `jsonb` et la réutiliser exactement à l'inférence.

---

## 35. Tests indispensables

### 35.1 Target alignment

Pour une date arbitraire :

```text
target_close == close exactement 365 jours plus tard
```

### 35.2 No-future-feature test

Aucune feature de l'ancre `t` ne doit dépendre d'une date > `t`.

### 35.3 Purged split

Pour chaque fold :

```text
max(train_anchor) + 365 < min(test_anchor)
```

### 35.4 Feature order

L'ordre utilisé à l'inférence doit être strictement identique à celui du train.

### 35.5 Model round-trip

```text
train -> model_to_string -> PostgreSQL -> model_from_string -> predict
```

La prédiction avant/après sérialisation doit être identique à la tolérance numérique près.

### 35.6 Quantile ordering

Après post-processing :

```text
Q05 <= Q25 <= Q50 <= Q75 <= Q95
```

### 35.7 Idempotence

Deux exécutions du predictor pour la même `forecast_date` ne doivent pas créer deux lignes contradictoires.

Utiliser `INSERT ... ON CONFLICT` selon la politique décidée.

---

## 36. Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_btc_ohlc_date
    ON btc_daily_ohlc(candle_date);

CREATE INDEX IF NOT EXISTS idx_model_sets_active
    ON forecast_model_sets(is_active)
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_forecasts_target_date
    ON btc_forecasts_365d(target_date);
```

La volumétrie reste très faible ; les indexes servent surtout à garder le comportement explicite et prévisible.

---

## 37. Gestion des versions de features

Commencer avec :

```text
feature_version = "ohlc-v1"
```

Exemple d'évolution :

```text
ohlc-v1       -> returns + SMA + vol + candle + drawdown + ATR
ohlc-v1.1     -> + Parkinson/Garman-Klass
ohlc-macro-v2 -> + variables macro externes
ohlc-chain-v3 -> + variables on-chain
```

Ne jamais comparer deux model sets sans savoir quelles features ont été utilisées.

---

## 38. Plan de réalisation par phases

### Phase 0 — Data audit

**But :** certifier la série daily.

Livrables :

- contrôle dates manquantes ;
- contrôle doublons ;
- contrôle OHLC ;
- timezone/source documentées ;
- décision fixe : candles UTC ;
- table de base propre.

**Exit criterion :** aucune anomalie non expliquée.

---

### Phase 1 — Dataset supervisé

Livrables :

- `btc_features_daily` ;
- ~20–35 features OHLC ;
- `target_return_365d` ;
- tests d'alignement ;
- rapport du nombre de lignes réellement utilisables.

**Exit criterion :** aucune feature future et target vérifiée manuellement sur plusieurs dates.

---

### Phase 2 — Baselines

Implémenter :

- quantiles historiques Q05/Q25/Q50/Q75/Q95 ;
- médiane zéro ;
- mêmes folds walk-forward que le ML.

**Exit criterion :** métriques baseline stockées en base.

---

### Phase 3 — Backtest LightGBM initial

Entraîner les cinq quantiles avec paramètres conservateurs.

Mesurer :

- pinball loss ;
- skill vs baseline ;
- calibration ;
- coverage ;
- sharpness ;
- crossing ;
- daily/weekly/monthly-anchor results.

**Exit criterion :** comprendre précisément où le modèle gagne ou perd.

---

### Phase 4 — Tuning limité

Seulement si la Phase 3 montre du signal.

- petit Optuna ;
- validation purgée ;
- même définition de folds ;
- pas de tuning sur le test final réservé.

**Exit criterion :** amélioration stable sur plusieurs folds, pas uniquement sur un score moyen.

---

### Phase 5 — Production Railway

Déployer :

```text
PostgreSQL existant
btc-forecast-trainer
btc-forecast-predictor
```

Stocker les modèles dans PostgreSQL.

**Exit criterion :** un forecast complet Q05…Q95 est produit depuis la dernière candle close.

---

### Phase 6 — Monitoring

- maturation automatique après 365 jours ;
- dashboard calibration ;
- performance par model set ;
- feature drift ;
- alertes jobs.

---

### Phase 7 — Enrichissement seulement si nécessaire

Si l'OHLC-only ne bat pas suffisamment les baselines, le levier prioritaire n'est probablement pas un modèle plus complexe.

Ajouter des variables qui décrivent mieux le régime économique du Bitcoin :

```text
macro
on-chain
liquidité
marchés cross-asset
```

Puis recommencer exactement le même protocole de validation.

---

## 39. Ce qu'il ne faut pas faire

### Ne pas prédire 365 candles récursivement

```text
J+1 -> J+2 -> ... -> J+365
```

Chaque erreur devient une entrée pour la suivante.

Pour l'objectif actuel, prédire directement la distribution du rendement à 365 jours.

### Ne pas utiliser de split random

Il mélange les régimes temporels et crée de la fuite entre labels chevauchants.

### Ne pas utiliser les 365 dernières lignes comme train labels

Leur target n'existe pas encore.

### Ne pas évaluer une prévision avant maturité

Un forecast du jour n'est objectivement jugeable que dans 365 jours.

### Ne pas lancer du deep learning en premier

Avec dix ans de daily, un LSTM/Transformer apporte beaucoup plus de capacité que de nouvelles informations.

### Ne pas multiplier les indicateurs techniques

Le dataset est trop petit pour justifier des centaines de features.

### Ne pas considérer Q05/Q95 comme des bornes certaines

5 % des observations peuvent théoriquement être sous Q05 et 5 % au-dessus de Q95 si la calibration est correcte.

---

## 40. Choix CPU / RAM Railway

Le dataset est minuscule pour LightGBM.

Commencer avec une allocation modeste et mesurer :

```text
CPU : 1–2 vCPU
RAM : 1–2 GiB
GPU : aucun
```

Augmenter uniquement si les backtests parallèles ou la recherche d'hyperparamètres deviennent un goulot.

La principale charge n'est pas l'entraînement d'un seul modèle ; c'est éventuellement la multiplication :

```text
5 quantiles × N folds × N essais hyperparamètres
```

Même dans ce cas, rester sur CPU est le choix logique pour cette volumétrie.

---

## 41. Dockerfile minimal indicatif

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY sql ./sql

RUN pip install --no-cache-dir \
    lightgbm \
    pandas \
    numpy \
    scikit-learn \
    "psycopg[binary]" \
    pydantic-settings

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "btc_forecast.cli", "predict"]
```

Pour une vraie production, pinner les versions dans le lockfile.

---

## 42. Variables d'environnement

```text
DATABASE_URL
FORECAST_HORIZON_DAYS=365
FEATURE_VERSION=ohlc-v1
MODEL_RANDOM_SEED=42
LOG_LEVEL=INFO
RUN_MODE=train|predict
```

Ne jamais embarquer de credentials dans l'image Docker.

---

## 43. Observabilité minimale

Chaque run doit logger :

```text
run_id
job_type
started_at
finished_at
status
source_latest_candle
feature_latest_date
training_rows
feature_count
active_model_set_id
new_model_set_id
forecast_date
quantile_crossing_before_fix
```

Pour un entraînement :

```text
fold metrics
baseline metrics
pinball skill
calibration
coverage
best_iteration
hyperparameters
```

---

## 44. Interprétation produit recommandée

Présenter le forecast comme une **distribution de scénarios**, pas comme une certitude.

Bon wording :

```text
Forecast probabiliste à 12 mois

Médiane conditionnelle (Q50): ...
Intervalle central 50 %: Q25 – Q75
Intervalle central 90 %: Q05 – Q95
```

Compléter avec :

```text
Backtest coverage Q05–Q95: ...
Backtest coverage Q25–Q75: ...
Model version: ...
Forecast generated: ...
```

Cela donne à l'utilisateur une information sur la calibration réelle du modèle.

---

## 45. Risque spécifique : changement structurel du marché Bitcoin

Dix ans de Bitcoin couvrent plusieurs régimes très différents.

Le modèle pourrait apprendre des relations présentes dans les cycles historiques mais qui disparaissent ensuite.

Mesures de protection :

- expanding walk-forward ;
- score par fold ;
- feature drift ;
- modèle simple ;
- comparaison permanente à un baseline historique ;
- ne jamais masquer une détérioration de calibration ;
- envisager ultérieurement un training window limité ou des poids de récence, mais uniquement après backtest.

Ne pas appliquer arbitrairement des poids de récence en V1 : cela réduit encore l'information effective et doit être justifié par des résultats hors échantillon.

---

## 46. Améliorations V2 potentielles

Une fois le pipeline V1 stable :

### 46.1 Horizons supplémentaires directs

Ajouter éventuellement :

```text
90 jours
180 jours
365 jours
```

Avec des modèles complètement distincts par horizon.

Cela donnerait :

```text
3 horizons × 5 quantiles = 15 modèles
```

Mais le 365 jours reste le scope V1.

### 46.2 Données macro

Exemples :

- taux ;
- dollar ;
- indices actions ;
- liquidité globale.

### 46.3 Données on-chain

Exemples :

- realized cap ;
- MVRV ;
- exchange flows ;
- supply metrics.

### 46.4 Ensemble

Combiner plus tard :

```text
LightGBM + modèle linéaire quantile + baseline historique
```

Mais seulement si le gain est démontré par le même walk-forward purgé.

### 46.5 Calibration avancée

- conformalisation adaptée au temps ;
- isotonic/rearrangement ;
- correction conditionnelle par régime.

---

## 47. Définition de Done de la V1

La V1 est terminée lorsque :

- [ ] la série OHLC daily UTC est certifiée continue ;
- [ ] `btc_features_daily` est reproductible ;
- [ ] la target 365d est vérifiée ;
- [ ] aucune fuite temporelle n'est possible par test automatisé ;
- [ ] les folds walk-forward appliquent 365 jours de purge ;
- [ ] les baselines Q05/Q25/Q50/Q75/Q95 existent ;
- [ ] cinq modèles LightGBM sont entraînés ;
- [ ] pinball loss est calculée par quantile ;
- [ ] calibration est calculée par quantile ;
- [ ] coverage Q05–Q95 et Q25–Q75 est calculée ;
- [ ] métriques daily + weekly/monthly anchors sont disponibles ;
- [ ] quantile crossing est mesuré et corrigé ;
- [ ] les modèles sont sérialisés dans PostgreSQL ;
- [ ] un model set peut être activé atomiquement ;
- [ ] Railway produit automatiquement une nouvelle prédiction après chaque candle daily ;
- [ ] Railway réentraîne mensuellement ;
- [ ] les forecasts matures sont rapprochés du résultat réel ;
- [ ] l'UI/API expose la date, l'horizon, les cinq quantiles et la version du modèle ;
- [ ] le modèle bat de manière crédible la baseline avant d'être présenté comme réellement prédictif.

---

## 48. Ordre d'implémentation recommandé

Si le projet démarre aujourd'hui, suivre exactement cet ordre :

```text
1. Audit OHLC / dates / UTC
2. Table propre btc_daily_ohlc
3. Feature view ohlc-v1
4. Target log-return 365d
5. Tests no-leakage
6. Purged walk-forward splitter
7. Baseline empirical quantiles
8. LightGBM Q50 seulement
9. Valider le pipeline entier sur Q50
10. Ajouter Q05/Q25/Q75/Q95
11. Calibration + coverage
12. Quantile crossing handling
13. Backtest daily + 7d + 30d anchors
14. Tuning conservateur
15. Tables model registry PostgreSQL
16. Sérialisation model_to_string
17. Railway trainer
18. Railway predictor
19. Maturation automatique
20. Monitoring
```

Cette séquence évite d'investir dans l'orchestration avant d'avoir validé que le problème ML est correctement formulé.

---

## 49. Recommandation finale

Pour des données **OHLC daily sur environ dix ans**, la meilleure V1 à mon sens est :

```text
Target
└── log-return direct à 365 jours

Features
└── 20–35 variables robustes dérivées uniquement de OHLC daily

Model
└── LightGBM quantile
    ├── Q05
    ├── Q25
    ├── Q50
    ├── Q75
    └── Q95

Validation
└── expanding walk-forward
    └── purge stricte de 365 jours

Evaluation
├── pinball loss
├── calibration
├── coverage 50 %
├── coverage 90 %
├── sharpness
├── crossing rate
└── comparaison aux quantiles historiques

Production
├── PostgreSQL = données + features + model registry + forecasts
├── Railway Python worker CPU
├── inference daily
├── retrain mensuel
└── backtest/tuning périodique
```

Le point le plus important n'est pas LightGBM lui-même. C'est la discipline du protocole temporel.

Avec un horizon de 365 jours et des observations daily, il est très facile de construire un modèle qui semble excellent parce que ses labels se chevauchent et que le train a implicitement vu une partie du futur du test. **La purge de 365 jours, les baselines et la calibration sont donc des éléments constitutifs du modèle, pas des raffinements facultatifs.**

Enfin, si l'OHLC-only ne bat pas proprement la baseline historique, la prochaine étape recommandée est d'ajouter de l'information économique/on-chain plutôt que de remplacer LightGBM par un modèle deep learning plus complexe.

---

## 50. Références techniques principales

- LightGBM — documentation officielle, paramètres : objectif `quantile` et paramètre `alpha`.
- LightGBM — documentation officielle du `Booster` : sérialisation `model_to_string()` / chargement depuis chaîne.
- Railway — documentation officielle des Cron Jobs : exécution planifiée d'un service qui doit terminer à la fin du job ; schedules en UTC.
- Railway — documentation PostgreSQL et Private Networking : connexion entre services du même projet via réseau privé et variables de connexion.

Documentation consultée lors de la préparation de ce plan :

- https://lightgbm.readthedocs.io/en/stable/Parameters.html
- https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html
- https://docs.railway.com/cron-jobs
- https://docs.railway.com/databases/postgresql
- https://docs.railway.com/networking/private-networking

---

## 51. Note de prudence

Ce projet est un système de prévision probabiliste expérimental. Même un modèle parfaitement calibré sur l'historique ne garantit pas que la distribution future de Bitcoin ressemblera à celle observée pendant les dix années disponibles. Les quantiles doivent être interprétés comme les sorties d'un modèle conditionnel évalué sur historique, et non comme des garanties de prix ou des conseils financiers.
