# Rapport d'évaluation — Challengers du forecast Bitcoin à 12 mois

**Version :** 1.0  
**Date :** 2026-09-06  
**Granularité disponible :** OHLC daily  
**Historique :** ~10 ans  
**Horizon principal :** 365 jours (~12 mois)  
**Sortie probabiliste cible :** Q05 / Q25 / Q50 / Q75 / Q95  
**Champion actuel :** LightGBM en régression quantile (rapport précédent)  
**Objet de ce rapport :** définir et prioriser les meilleurs challengers, avec un protocole de comparaison strictement commun.

---

## 1. Résumé exécutif

Le premier rapport retient **LightGBM Quantile** comme solution de référence pour prédire directement la distribution du rendement Bitcoin à 365 jours :

```text
y_365(t) = ln(close[t + 365] / close[t])
```

avec cinq modèles :

```text
Q05  -> alpha = 0.05
Q25  -> alpha = 0.25
Q50  -> alpha = 0.50
Q75  -> alpha = 0.75
Q95  -> alpha = 0.95
```

Le présent rapport ne remplace pas cette architecture. Il organise un **forecasting bake-off** destiné à répondre à une question plus utile :

> Existe-t-il une famille de modèles qui généralise mieux que LightGBM sur un horizon de 12 mois, avec seulement ~10 ans de données daily, sans introduire de fuite temporelle et sans rendre l'infrastructure Railway inutilement complexe ?

Les challengers retenus sont :

1. **Chronos-2-small zero-shot** — foundation model pré-entraîné, sans entraînement local initial.
2. **Chronos-2 complet zero-shot** — utilisé seulement si le small est prometteur ou si l'interpolation Q25/Q75 dégrade la calibration.
3. **NHITS + Multi-Quantile Loss** — modèle neural spécialement conçu pour le long-horizon forecasting.
4. **Regime-aware LightGBM** — HMM + probabilités de régime ajoutées au modèle LightGBM ou mixture-of-experts.
5. **TimesFM 2.5** — foundation model zero-shot, benchmark secondaire.
6. **Ensemble probabiliste** — uniquement si au moins deux challengers apportent des erreurs réellement complémentaires.

### Décision recommandée avant toute implémentation

L'ordre d'expérimentation recommandé est :

```text
B0  Baseline historique 365d
B1  Naive / random walk

M1  LightGBM Quantile (champion actuel)
        ↓
C1  Chronos-2-small zero-shot
        ↓
C2  NHITS + MQLoss
        ↓
C3  HMM + LightGBM regime-aware
        ↓
C4  Chronos-2 complet si nécessaire
        ↓
C5  TimesFM 2.5
        ↓
E1  Ensemble si justifié
```

La recommandation n'est **pas** de construire immédiatement tous les modèles.

Le premier objectif est de déterminer rapidement si :

- le pré-entraînement massif de Chronos apporte une amélioration sur un historique BTC court ;
- NHITS exploite réellement les structures multi-échelles du BTC sans surapprendre ;
- les régimes de marché ajoutent plus de valeur que le simple changement d'algorithme.

---

# 2. Contraintes structurelles du problème

## 2.1 Dataset

Hypothèses :

```text
Asset        : Bitcoin
Granularité  : 1 jour
Historique   : ~10 ans
Observations : ~3 650 candles
Colonnes     : date, open, high, low, close
Volume       : à intégrer si disponible, mais non requis
```

Le dataset est relativement petit pour du deep learning from scratch.

La granularité daily est cohérente avec l'horizon de 12 mois. Il n'est pas nécessaire de reconstruire artificiellement des données horaires ou intraday.

---

## 2.2 Deux problèmes de forecasting différents

Il faut distinguer deux types de modèles.

### A. Forecast terminal direct

LightGBM répond à :

```text
Quel est le rendement du Bitcoin exactement à t + 365 jours ?
```

Sortie :

```text
return_Q05_365
return_Q25_365
return_Q50_365
return_Q75_365
return_Q95_365
```

Il ne cherche pas à prédire chaque jour intermédiaire.

### B. Forecast de trajectoire

Chronos, NHITS et TimesFM peuvent répondre à :

```text
Quelle est la distribution prévisionnelle de BTC pour :

J+1
J+2
...
J+365 ?
```

Ils produisent donc potentiellement :

```text
365 × 5 quantiles
```

Cette différence doit absolument être prise en compte lors du benchmark.

**La métrique primaire restera la performance à J+365**, afin que tous les modèles soient comparables.

Les performances sur la trajectoire complète seront des métriques secondaires.

---

# 3. Protocole de benchmark commun

Aucun challenger ne doit bénéficier d'un protocole plus favorable qu'un autre.

## 3.1 Principe fondamental

Pour une date de forecast `t` :

```text
le modèle ne voit absolument aucune information postérieure à t.
```

Cela inclut :

- les prix ;
- les features ;
- les statistiques de normalisation ;
- les régimes HMM ;
- le tuning des hyperparamètres ;
- le choix du modèle ;
- les targets futures.

---

## 3.2 Purge de 365 jours

Pour un target à 365 jours :

```text
y(t) = close[t + 365]
```

une observation située juste avant le début du test contient un label qui utilise des prix appartenant au test.

Il faut donc imposer :

```text
fin des targets du train < début du test
```

soit conceptuellement :

```text
TRAIN
───────────────┐

               │ 365 jours de purge
               └──────────────────────

                                      TEST
                                      ───────────
```

Ce principe s'applique également aux modèles multi-horizon entraînés sur des fenêtres.

Une fenêtre d'entraînement qui commence avant le test mais dont la cible `[t+1, ..., t+365]` pénètre dans la période de test doit être exclue.

---

## 3.3 Walk-forward expanding

Protocole recommandé :

```text
Fold 1
Train : début dataset -> cutoff_1 - 365j
Test  : période suivant cutoff_1

Fold 2
Train : début dataset -> cutoff_2 - 365j
Test  : période suivant cutoff_2

Fold 3
...

Fold N
```

La fenêtre d'entraînement s'agrandit progressivement.

---

## 3.4 Fréquence des points d'évaluation

Les forecasts produits deux jours consécutifs sont très dépendants.

Pour l'évaluation principale :

```text
anchor frequency = 30 jours
```

Exemple :

```text
2021-01-01
2021-02-01
2021-03-01
...
```

Une analyse secondaire peut utiliser :

```text
7 jours
```

Une analyse de sensibilité peut conserver tous les jours, mais les métriques daily ne doivent pas être interprétées comme des observations indépendantes.

### Pourquoi les ancres mensuelles ?

Parce que :

- l'horizon est de 365 jours ;
- les targets sont fortement chevauchants ;
- l'évaluation quotidienne créerait une illusion de grand échantillon.

---

# 4. Métriques communes

## 4.1 Pinball Loss

Pour chaque quantile :

```text
Pinball(Q05)
Pinball(Q25)
Pinball(Q50)
Pinball(Q75)
Pinball(Q95)
```

Puis :

```text
Mean Quantile Loss
```

Ce sera la métrique probabiliste principale.

---

## 4.2 Calibration

Un modèle bien calibré doit vérifier approximativement :

```text
P(Y <= Q05) ≈ 5 %
P(Y <= Q25) ≈ 25 %
P(Y <= Q50) ≈ 50 %
P(Y <= Q75) ≈ 75 %
P(Y <= Q95) ≈ 95 %
```

On calcule donc :

```text
calibration_error_q =
abs(empirical_frequency - q)
```

---

## 4.3 Couverture des intervalles

### Intervalle central à 90 %

```text
[Q05, Q95]
```

Couverture cible :

```text
~90 %
```

### Intervalle interquartile

```text
[Q25, Q75]
```

Couverture cible :

```text
~50 %
```

---

## 4.4 Largeur des intervalles

Un modèle peut obtenir 95 % de couverture simplement en générant un intervalle gigantesque.

On mesure donc également :

```text
width_90 = Q95 - Q05
width_50 = Q75 - Q25
```

Idéalement, le modèle doit être :

```text
calibré
+
aussi sharp que possible
```

---

## 4.5 Q50

Pour la médiane :

```text
MAE_Q50
Median Absolute Error
```

sur :

```text
return_365
```

et éventuellement sur :

```text
price_365
```

La métrique en rendement est préférable pour comparer différentes époques de prix BTC.

---

## 4.6 Direction

Métrique secondaire :

```text
sign(predicted_return_Q50) == sign(actual_return_365)
```

Cela donne une :

```text
directional_accuracy_365d
```

Elle ne doit pas remplacer la Pinball Loss.

---

# 5. Baselines obligatoires

Avant de parler de neural networks ou foundation models, chaque modèle doit battre des baselines très simples.

## B0 — Distribution historique des rendements 365 jours

Pour chaque cutoff :

```text
historical_returns =
ln(close[t] / close[t-365])
```

sur les données disponibles avant le cutoff.

On calcule :

```text
Q05 historique
Q25 historique
Q50 historique
Q75 historique
Q95 historique
```

Cette baseline est extrêmement importante.

Si un modèle sophistiqué ne réduit pas la Pinball Loss par rapport à ces quantiles historiques, il n'apporte pas de valeur démontrée.

---

## B1 — No-change / random walk

Pour la médiane :

```text
price_Q50(t+365) = close(t)
```

soit :

```text
return_Q50 = 0
```

Ce baseline est volontairement naïf.

---

# 6. Champion actuel — LightGBM Quantile

Le modèle du premier rapport reste la référence.

## Input

Features OHLC dérivées :

```text
returns
momentum
rolling volatility
SMA ratios
drawdown
ATR
candle structure
rolling skew
rolling kurtosis
```

## Target

```text
log_return_365
```

## Modèles

```text
LGBM_Q05
LGBM_Q25
LGBM_Q50
LGBM_Q75
LGBM_Q95
```

## Forces

- très adapté à ~3 000 observations supervisées ;
- CPU friendly ;
- très facile à déployer sur Railway ;
- interprétable via feature importance / SHAP ;
- target directement aligné sur notre besoin J+365 ;
- quantiles exacts Q05/Q25/Q50/Q75/Q95.

## Faiblesses

- ne produit pas naturellement une trajectoire journalière ;
- dépend fortement du feature engineering ;
- ne bénéficie pas de pré-entraînement sur d'autres séries temporelles ;
- traite implicitement les régimes comme une seule distribution fonctionnelle.

---

# 7. Challenger C1 — Chronos-2-small zero-shot

## 7.1 Pourquoi il mérite la priorité

Chronos-2-small est un foundation model de forecasting pré-entraîné.

Caractéristiques importantes :

```text
Paramètres      : ~28M
Licence         : Apache-2.0
Context length  : 8192
Granularité     : générique
Training local  : aucun en zero-shot
```

Notre série :

```text
~3650 points daily
```

rentre entièrement dans sa fenêtre de contexte.

Cela permet de tester une question fondamentale :

> Un modèle ayant appris des structures temporelles sur de nombreuses séries peut-il compenser notre faible quantité de données Bitcoin ?

---

## 7.2 Horizon

La configuration du modèle utilise :

```text
max_output_patches = 64
output_patch_size  = 16
```

soit une capacité nominale de :

```text
64 × 16 = 1024 points
```

Notre horizon :

```text
365
```

est donc dans l'enveloppe du modèle.

---

## 7.3 Quantiles

Chronos-2-small possède nativement les niveaux :

```text
0.01
0.05
0.10
0.20
0.30
0.40
0.50
0.60
0.70
0.80
0.90
0.95
0.99
```

Cela signifie :

```text
Q05  -> natif
Q25  -> interpolé entre Q20 et Q30
Q50  -> natif
Q75  -> interpolé entre Q70 et Q80
Q95  -> natif
```

La pipeline Chronos supporte explicitement l'interpolation de quantiles demandés qui ne font pas partie des quantiles d'entraînement.

Cette interpolation doit être **mesurée**, pas supposée parfaite.

---

## 7.4 Chronos-2 complet comme escalade

Le Chronos-2 complet possède notamment :

```text
Q05
Q25
Q50
Q75
Q95
```

nativement.

Il ne doit pas être utilisé immédiatement.

Ordre recommandé :

```text
Chronos-2-small
      │
      ├── mauvais -> abandon de la piste
      │
      └── prometteur
              │
              ▼
       Chronos-2 complet
```

Le modèle complet devient pertinent si :

- Small bat LightGBM sur plusieurs folds ;
- Q25/Q75 sont mal calibrés ;
- ou Small est proche du champion et justifie une escalade.

---

## 7.5 Représentation du target

Trois variantes à benchmarker.

### C1-A — Close brut

```text
target = close
```

Avantage :

- formulation la plus naturelle.

Inconvénient :

- énorme changement d'échelle du BTC sur 10 ans.

---

### C1-B — Log-price

Recommandation principale :

```text
target = ln(close)
```

Forecast :

```text
log_price_q
```

puis :

```text
price_q = exp(log_price_q)
```

Avantages :

- atténue l'amplitude exponentielle de BTC ;
- interdit implicitement les prix négatifs après exponentiation ;
- rend les changements multiplicatifs plus naturels.

---

### C1-C — Return / cumulative return

Expérience secondaire :

```text
daily_log_return =
ln(close_t / close_t-1)
```

Le modèle prédit la trajectoire des rendements, puis les cumule.

Cette stratégie est plus fragile car les erreurs quotidiennes s'accumulent.

Elle n'est pas prioritaire.

---

## 7.6 Premier benchmark recommandé

```text
C1-A : Chronos small / close
C1-B : Chronos small / log(close)
```

On sélectionne la meilleure représentation **uniquement sur validation passée**.

---

## 7.7 Exemple d'inférence

Pseudo-code :

```python
from chronos import BaseChronosPipeline

pipeline = BaseChronosPipeline.from_pretrained(
    "autogluon/chronos-2-small",
    device_map="cpu",
)

forecast = pipeline.predict_df(
    df=context_df,
    prediction_length=365,
    quantile_levels=[0.05, 0.25, 0.50, 0.75, 0.95],
    id_column="item_id",
    timestamp_column="date",
    target="log_close",
    freq="D",
)
```

À vérifier lors du POC :

- RAM réelle ;
- durée d'un forecast ;
- durée d'un backtest complet ;
- reproductibilité ;
- interpolation Q25/Q75 ;
- quantile crossing éventuel.

---

## 7.8 Railway

Railway ne propose actuellement pas de GPU.

Chronos-2-small est toutefois assez petit pour justifier **un test CPU batch**, particulièrement parce que :

```text
inférence non temps réel
+
une seule série
+
forecast peu fréquent
```

Il ne faut pas présumer qu'il sera suffisamment rapide.

### Gate C1

Chronos-2-small reste sur Railway si :

```text
runtime acceptable
RAM acceptable
aucun crash
backtest exécutable
```

Sinon :

```text
Railway = orchestration
GPU externe = inference Chronos
```

---

## 7.9 Critères de réussite

Chronos Small passe en phase suivante s'il remplit au moins une condition :

1. meilleure Mean Pinball Loss que LightGBM ;
2. meilleure calibration avec perte comparable ;
3. meilleure performance sur certains régimes avec erreurs complémentaires ;
4. trajectoire utile sans dégrader J+365.

---

# 8. Challenger C2 — NHITS + Multi-Quantile Loss

## 8.1 Pourquoi NHITS

NHITS est une architecture MLP conçue spécifiquement pour le **long-horizon forecasting**.

Elle utilise :

```text
multi-rate input processing
+
hierarchical interpolation
+
frequency specialization
```

Contrairement à un LSTM générique, le problème long-horizon est au cœur du design.

---

## 8.2 Sortie directe

Configuration :

```text
h = 365
```

Loss :

```text
MQLoss(
    quantiles=[
        0.05,
        0.25,
        0.50,
        0.75,
        0.95,
    ]
)
```

Le réseau produit alors directement :

```text
365 jours × 5 quantiles
```

---

## 8.3 Input size

Le principal hyperparamètre structurel est la longueur du contexte.

À tester :

```text
730 jours   = 2 ans
1095 jours  = 3 ans
1460 jours  = 4 ans
```

Je ne commencerais pas par 5 ans, car cela réduit fortement le nombre de fenêtres disponibles.

### Search space recommandé

```text
input_size ∈ {730, 1095, 1460}
```

Le tuning doit rester volontairement petit.

Avec seulement ~3650 points, une recherche d'hyperparamètres massive augmenterait le risque d'overfitting au backtest.

---

## 8.4 Target

Recommandation :

```text
y = log(close)
```

Plutôt que :

```text
close brut
```

On reconstruit ensuite :

```text
price = exp(predicted_log_price)
```

---

## 8.5 OHLC comme covariables

Deux étapes.

### NHITS-1

Uniquement :

```text
log_close
```

### NHITS-2

Ajouter des historical exogenous variables :

```text
log_open
log_high
log_low

daily_return
range_pct
body_pct
volatility_30
volatility_90
drawdown
```

Important :

```text
aucune future exogenous variable non connue
```

Les features futures ne peuvent être utilisées que si elles sont réellement connues pour les 365 prochains jours.

---

## 8.6 Configuration de départ

Pseudo-code :

```python
from neuralforecast import NeuralForecast
from neuralforecast.models import NHITS
from neuralforecast.losses.pytorch import MQLoss

quantiles = [0.05, 0.25, 0.50, 0.75, 0.95]

model = NHITS(
    h=365,
    input_size=1095,
    loss=MQLoss(quantiles=quantiles),
    scaler_type="robust",
    max_steps=1000,
    early_stop_patience_steps=10,
    val_check_steps=50,
    random_seed=42,
)
```

Valeurs à adapter après un premier benchmark.

---

## 8.7 Risque principal : nombre d'exemples réels

La construction des fenêtres crée mathématiquement beaucoup de samples :

```text
window t
window t+1
window t+2
...
```

mais ces fenêtres sont extrêmement corrélées.

Le modèle ne doit pas être évalué comme s'il disposait de milliers d'exemples indépendants.

C'est pourquoi :

- la validation reste walk-forward ;
- les anchors d'évaluation principaux sont mensuels ;
- plusieurs seeds sont nécessaires ;
- on évite les architectures énormes.

---

## 8.8 Seeds

Pour LightGBM, la variance d'initialisation est faible.

Pour NHITS, on doit tester :

```text
seed = 11
seed = 42
seed = 73
```

Puis comparer :

```text
mean metric
std metric
```

Un modèle neural qui gagne sur une seule seed ne doit pas être promu.

---

## 8.9 Railway

NHITS peut fonctionner sur CPU.

La question n'est pas :

```text
est-ce techniquement possible ?
```

mais :

```text
est-ce économiquement et opérationnellement intéressant ?
```

POC :

```text
2-4 vCPU
4-8 GB RAM
```

à ajuster selon le runtime observé.

Railway Cron est compatible avec ce type de job batch, à condition que le processus termine explicitement après le training.

---

## 8.10 Gate C2

NHITS est conservé si :

```text
Mean Pinball < baseline
ET
stabilité multi-seed acceptable
ET
runtime acceptable
```

Pour battre LightGBM, une amélioration minuscule mais extrêmement instable ne suffit pas.

---

# 9. Challenger C3 — HMM + LightGBM regime-aware

## 9.1 Pourquoi cette piste est particulièrement intéressante

Cette approche ne remplace pas nécessairement LightGBM.

Elle teste une hypothèse différente :

> Les relations entre momentum, volatilité, drawdown et rendement à 12 mois changent-elles selon le régime de marché ?

Bitcoin traverse historiquement des périodes très différentes :

```text
bull expansion
bear contraction
sideways / transition
high volatility
low volatility
```

Un modèle global peut devoir apprendre une fonction moyenne entre ces états.

---

## 9.2 Hidden Markov Model

Le HMM reçoit par exemple :

```text
daily_return
volatility_30
volatility_90
drawdown
momentum_90
```

Il estime des probabilités latentes :

```text
P(regime_0)
P(regime_1)
P(regime_2)
```

Important :

> Le HMM doit être refitté dans chaque fold uniquement avec les données disponibles à cette date.

Sinon il y a leakage.

---

## 9.3 Ne pas commencer par trois modèles séparés

Avec ~10 ans de daily, découper immédiatement les données en :

```text
bull dataset
bear dataset
sideways dataset
```

réduit énormément le nombre d'observations par modèle.

La première variante recommandée est plus robuste.

### C3-A — Soft regime features

Ajouter au LightGBM global :

```text
regime_p0
regime_p1
regime_p2
```

Puis :

```text
LightGBM(features + regime probabilities)
```

C'est la recommandation initiale.

---

## 9.4 Variante C3-B — Hard regime

Ajouter :

```text
regime_id = argmax(probabilities)
```

comme feature catégorielle.

À comparer au soft regime.

---

## 9.5 Variante C3-C — Mixture of experts

Seulement si C3-A montre une amélioration claire.

```text
                HMM
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
      Regime0  Regime1  Regime2
        │        │        │
        ▼        ▼        ▼
      LGBM0    LGBM1    LGBM2
        │        │        │
        └────────┼────────┘
                 │
                 ▼
          weighted forecast
```

Poids :

```text
P(regime_0)
P(regime_1)
P(regime_2)
```

Forecast final :

```text
Qα_final =
Σ P(regime_k) × Qα_model_k
```

Ce mélange de quantiles est une approximation ; pour une vraie mixture distribution, il faut reconstruire/mélanger les distributions. On ne doit donc pas promouvoir cette formule naïve sans vérification de calibration.

---

## 9.6 Nombre de régimes

Tester seulement :

```text
2 états
3 états
```

Éviter :

```text
5
6
7
...
```

Avec 10 ans d'historique, les états supplémentaires risquent surtout de découper le bruit.

---

## 9.7 Labeling des régimes

Les IDs HMM :

```text
0
1
2
```

n'ont pas de signification stable.

Après fit, on peut seulement les nommer pour l'affichage :

```text
regime avec mean return élevé  -> bull-like
regime avec mean return faible -> bear-like
regime intermédiaire           -> transition
```

Le code prédictif ne doit pas dépendre du fait que :

```text
state 0 == bull
```

car l'ordre des états peut changer entre deux fits.

---

## 9.8 Pourquoi C3 peut battre des modèles plus complexes

C3 conserve les points forts du champion :

```text
faible variance
CPU
feature engineering
target direct 365d
quantiles exacts
```

tout en ajoutant une information structurelle.

Il est possible que cette simple extension apporte plus de valeur que :

```text
LSTM
TFT
TimesFM
```

sur un dataset aussi court.

---

# 10. Challenger C4 — Chronos-2 complet

Ce n'est pas un challenger initial séparé mais une **escalade de C1**.

## Raisons de l'utiliser

- Q25 et Q75 sont natifs ;
- capacité supérieure ;
- plus grande richesse du modèle.

## Raisons de ne pas commencer par lui

- plus lourd ;
- plus lent sur CPU ;
- augmente la probabilité de devoir sortir l'inférence de Railway ;
- si le small est mauvais, le modèle complet n'est pas automatiquement la solution.

### Trigger recommandé

Tester Chronos-2 complet uniquement si :

```text
Chronos-small Mean Pinball <= LightGBM × 1.05
```

ou si :

```text
Small est bon sur Q05/Q50/Q95
mais Q25/Q75 sont clairement moins calibrés.
```

Le seuil 1.05 est un exemple de gate opérationnel à figer avant le benchmark.

---

# 11. Challenger C5 — TimesFM 2.5

## 11.1 Caractéristiques

TimesFM 2.5 :

```text
~200M paramètres
context max ~16 384
horizon quantile max ~1024
licence Apache-2.0 pour v2.5
zero-shot
```

365 jours rentrent donc dans son horizon.

---

## 11.2 Pourquoi il est secondaire

L'API standard expose principalement :

```text
Q10
Q20
Q30
Q40
Q50
Q60
Q70
Q80
Q90
```

Notre benchmark principal exige :

```text
Q05
Q25
Q50
Q75
Q95
```

Même si TimesFM 2.5 dispose d'un continuous quantile head, la sortie et le support des niveaux custom doivent être vérifiés dans la version exacte de la librairie utilisée.

Pour éviter de fabriquer artificiellement :

```text
Q05
Q95
```

par extrapolation fragile, TimesFM ne doit pas être le premier challenger.

---

## 11.3 Utilisation recommandée

Premier benchmark TimesFM :

```text
Q10
Q20
Q50
Q80
Q90
```

pour juger la qualité générale.

Puis seulement si prometteur :

```text
vérifier les custom quantiles
ou
définir un protocole de recalibration.
```

---

## 11.4 Infrastructure

200M paramètres restent nettement plus lourds que Chronos-small.

Pour un batch mensuel ou un benchmark offline, le CPU peut être testé.

Mais Railway indique explicitement ne pas proposer de GPU.

Si le runtime est mauvais :

```text
Railway
   │
   └── orchestration + Postgres
             │
             ▼
       GPU externe ponctuel
```

Il ne faut pas ajouter cette infrastructure tant que TimesFM n'a pas démontré un gain.

---

# 12. Modèles explicitement dépriorisés

## 12.1 LSTM from scratch

Pourquoi non prioritaire :

```text
dataset faible
fort chevauchement des fenêtres
sensible aux hyperparamètres
entraînement neural
aucun avantage structurel clair vs NHITS
```

Un LSTM peut rester un benchmark pédagogique.

---

## 12.2 TFT from scratch

Temporal Fusion Transformer est intéressant avec :

- plusieurs séries ;
- nombreuses covariables ;
- beaucoup de données.

Pour :

```text
1 série BTC
~3650 points
OHLC seulement
```

le rapport complexité/bénéfice est mauvais.

---

## 12.3 Prophet

À garder comme baseline statistique éventuelle.

Pas comme challenger principal.

---

## 12.4 ARIMA

Même position :

```text
baseline statistique
≠ moteur final attendu
```

Il reste intéressant pour vérifier que le ML apporte réellement quelque chose.

---

# 13. Standardisation des outputs

Tous les modèles doivent produire un schéma commun.

## Table `forecast_backtest_predictions`

```sql
CREATE TABLE forecast_backtest_predictions (
    id                bigserial PRIMARY KEY,
    model_id          text NOT NULL,
    model_version     text NOT NULL,
    fold_id           text NOT NULL,
    anchor_date       date NOT NULL,
    horizon_days      integer NOT NULL,
    target_date       date NOT NULL,

    spot_price        double precision NOT NULL,

    q05_return        double precision,
    q25_return        double precision,
    q50_return        double precision,
    q75_return        double precision,
    q95_return        double precision,

    q05_price         double precision,
    q25_price         double precision,
    q50_price         double precision,
    q75_price         double precision,
    q95_price         double precision,

    actual_return     double precision,
    actual_price      double precision,

    runtime_seconds   double precision,
    metadata          jsonb,

    created_at        timestamptz DEFAULT now()
);
```

Pour les modèles path-based, on peut ajouter une table séparée.

## `forecast_path_predictions`

```sql
CREATE TABLE forecast_path_predictions (
    model_id        text NOT NULL,
    fold_id         text NOT NULL,
    anchor_date     date NOT NULL,
    forecast_date   date NOT NULL,
    horizon_step    integer NOT NULL,

    q05_price       double precision,
    q25_price       double precision,
    q50_price       double precision,
    q75_price       double precision,
    q95_price       double precision,

    actual_price    double precision,

    PRIMARY KEY (
        model_id,
        fold_id,
        anchor_date,
        horizon_step
    )
);
```

---

# 14. Metrics table

```sql
CREATE TABLE forecast_model_metrics (
    model_id             text NOT NULL,
    model_version        text NOT NULL,
    evaluation_scope     text NOT NULL,

    pinball_q05          double precision,
    pinball_q25          double precision,
    pinball_q50          double precision,
    pinball_q75          double precision,
    pinball_q95          double precision,
    mean_pinball         double precision,

    calibration_q05      double precision,
    calibration_q25      double precision,
    calibration_q50      double precision,
    calibration_q75      double precision,
    calibration_q95      double precision,

    coverage_50          double precision,
    coverage_90          double precision,

    avg_width_50         double precision,
    avg_width_90         double precision,

    mae_q50              double precision,
    directional_accuracy double precision,

    runtime_seconds      double precision,

    created_at           timestamptz DEFAULT now()
);
```

---

# 15. Normalisation des forecasts path-based vers J+365

Chronos/NHITS/TimesFM produisent :

```text
Qα(date + 1)
...
Qα(date + 365)
```

Pour le leaderboard principal :

```text
prendre horizon_step = 365
```

Puis calculer :

```text
return_q =
ln(price_q_J365 / current_price)
```

Cela permet de comparer exactement avec LightGBM.

---

# 16. Leaderboard principal

Table souhaitée :

| Model | Mean Pinball ↓ | Q05 Cal. | Q25 Cal. | Q50 Cal. | Q75 Cal. | Q95 Cal. | Coverage 90 | MAE Q50 ↓ | Runtime |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Historical Quantiles | | | | | | | | | |
| Naive | | | | | | | | | |
| LightGBM Quantile | | | | | | | | | |
| Chronos-2-small | | | | | | | | | |
| NHITS | | | | | | | | | |
| HMM + LightGBM | | | | | | | | | |
| Chronos-2 | | | | | | | | | |
| TimesFM 2.5 | | | | | | | | | |

---

# 17. Leaderboard secondaire — horizons intermédiaires

Pour les modèles qui produisent une trajectoire :

```text
J+30
J+90
J+180
J+365
```

Mesurer :

```text
Pinball
Calibration
MAE Q50
```

Cela permet de savoir si un modèle :

```text
bon à court terme
mais mauvais à 12 mois
```

ou inversement.

LightGBM 365d ne participe pas nécessairement à ce leaderboard sauf si l'on entraîne des targets supplémentaires :

```text
90d
180d
365d
```

---

# 18. Test des erreurs complémentaires

Un modèle qui ne bat pas LightGBM seul peut malgré tout être utile dans un ensemble.

Pour chaque anchor :

```text
error_model =
predicted_Q50_return - actual_return
```

Calculer ensuite la corrélation des erreurs :

```text
corr(error_LGBM, error_Chronos)
corr(error_LGBM, error_NHITS)
corr(error_LGBM, error_HMM)
```

Exemple d'interprétation :

```text
Chronos
Mean Pinball légèrement moins bon
mais corr(error, LightGBM) = 0.35

=> potentiellement excellent candidat ensemble
```

À l'inverse :

```text
modèle moins bon
+
corrélation erreurs = 0.95

=> faible valeur marginale
```

---

# 19. Ensemble probabiliste E1

Ne construire un ensemble que si le benchmark le justifie.

## 19.1 Ensemble simple

Pour chaque quantile :

```text
Qα_ensemble =
w1 × Qα_LGBM
+
w2 × Qα_Chronos
+
w3 × Qα_NHITS
```

Contraintes :

```text
wi >= 0
Σ wi = 1
```

Les poids doivent être appris uniquement sur les folds historiques.

---

## 19.2 Point de départ

```text
equal weight
```

Exemple :

```text
1/3
1/3
1/3
```

Puis comparer à une optimisation des poids minimisant :

```text
Mean Pinball Loss
```

---

## 19.3 Attention au quantile crossing

Après blend :

```text
Q05 <= Q25 <= Q50 <= Q75 <= Q95
```

doit toujours être vérifié.

Si crossing :

```text
sort quantiles
```

peut servir de correctif minimal, mais la fréquence des crossings doit être enregistrée comme métrique de qualité.

---

# 20. Expériences exactes recommandées

## Expérience B0

```text
Historical 365d quantiles
```

But :

```text
baseline probabiliste minimale
```

---

## Expérience M1

```text
LightGBM Quantile v1
```

Configuration du rapport précédent.

---

## Expérience C1.1

```text
Chronos-2-small
target = close
zero-shot
h = 365
```

---

## Expérience C1.2

```text
Chronos-2-small
target = log(close)
zero-shot
h = 365
```

Cette variante est celle que je m'attends à préférer.

---

## Expérience C2.1

```text
NHITS
log(close)
input_size = 730
MQLoss
```

---

## Expérience C2.2

```text
NHITS
log(close)
input_size = 1095
MQLoss
```

---

## Expérience C2.3

```text
NHITS
log(close)
input_size = 1460
MQLoss
```

Ne pas multiplier les configurations au-delà de ce premier test.

---

## Expérience C3.1

```text
HMM 2 states
+
LightGBM global
+
soft regime probabilities
```

---

## Expérience C3.2

```text
HMM 3 states
+
LightGBM global
+
soft regime probabilities
```

---

## Expérience C3.3

Seulement si C3.1/C3.2 sont prometteurs :

```text
mixture of experts
```

---

## Expérience C4

Uniquement si Chronos-small passe le gate :

```text
amazon/chronos-2
```

---

## Expérience C5

Après les challengers précédents :

```text
TimesFM 2.5
```

---

# 21. Ordre d'implémentation concret

## Phase 0 — Harness de benchmark

Créer :

```text
forecasting/
├── data/
├── features/
├── splits/
├── metrics/
├── models/
├── backtest/
└── cli/
```

Objectif :

```text
un seul moteur de folds
un seul système de métriques
plusieurs adapters de modèles
```

---

## Phase 1 — Reproduire le champion

Avant tout challenger :

```text
run LightGBM
```

et obtenir un résultat de référence reproductible.

Exemple :

```bash
python -m forecasting.cli backtest \
  --model lightgbm_quantile \
  --anchor-step 30
```

---

## Phase 2 — Chronos Small

```bash
python -m forecasting.cli backtest \
  --model chronos2_small_logclose \
  --anchor-step 30
```

Mesurer :

```text
accuracy
calibration
runtime
RAM
```

---

## Phase 3 — NHITS

```bash
python -m forecasting.cli backtest \
  --model nhits \
  --input-size 1095 \
  --seed 42
```

Puis multi-seed.

---

## Phase 4 — Regime-aware

```bash
python -m forecasting.cli backtest \
  --model lightgbm_hmm \
  --states 2
```

puis :

```text
3 states
```

---

## Phase 5 — Escalade

Seulement après analyse :

```text
Chronos full
TimesFM
Ensemble
```

---

# 22. Interface Python commune

Exemple :

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class QuantileForecast:
    anchor_date: date
    horizon_days: int

    q05: float
    q25: float
    q50: float
    q75: float
    q95: float

class ForecastModel:
    def fit(self, train_df):
        ...

    def predict_terminal(self, context_df) -> QuantileForecast:
        ...

    def predict_path(self, context_df):
        return None
```

Pour zero-shot :

```python
def fit(self, train_df):
    return self
```

Ainsi, le backtester ne traite pas Chronos différemment de LightGBM au niveau de l'interface.

---

# 23. Railway — architecture recommandée

```text
                 Railway Project
┌──────────────────────────────────────────┐
│                                          │
│ PostgreSQL                               │
│ ├── btc_daily_ohlc                       │
│ ├── btc_features_daily                   │
│ ├── forecast_predictions                 │
│ ├── forecast_path_predictions            │
│ └── forecast_metrics                     │
│                                          │
│ forecast-runner                          │
│ ├── LightGBM                             │
│ ├── HMM                                  │
│ ├── Chronos-small CPU POC                │
│ └── NHITS CPU                            │
│                                          │
│ Railway Cron                             │
└──────────────────────────────────────────┘
                      │
                      │ seulement si requis
                      ▼
             External GPU worker
             ├── Chronos full
             └── TimesFM
```

---

# 24. Jobs Railway

## Forecast production

Fréquence :

```text
daily
```

Il peut recalculer la projection, même si l'horizon est 12 mois.

---

## LightGBM retrain

```text
mensuel
```

---

## HMM retrain

Avec le pipeline LightGBM :

```text
mensuel
```

---

## NHITS retrain

Initialement :

```text
mensuel
```

mais un retrain moins fréquent pourra suffire.

---

## Chronos

Zero-shot :

```text
aucun retrain
```

Uniquement inference.

---

# 25. Gestion des modèles

## Table

```sql
CREATE TABLE forecast_models (
    model_id            text PRIMARY KEY,
    model_family        text NOT NULL,
    version             text NOT NULL,
    config              jsonb NOT NULL,
    artifact_uri        text,
    is_champion         boolean DEFAULT false,
    created_at          timestamptz DEFAULT now()
);
```

Pour :

```text
LightGBM / NHITS / HMM
```

les artifacts peuvent être stockés :

- volume Railway ;
- object storage ;
- ou PostgreSQL si la taille reste raisonnable.

Les foundation models doivent plutôt être téléchargés depuis leur repository/cache d'image, pas sérialisés dans PostgreSQL.

---

# 26. Champion / challenger promotion

Ne pas remplacer automatiquement le champion lorsqu'un modèle gagne une métrique.

## Conditions proposées

Un challenger devient champion si :

### Condition A — performance

```text
Mean Pinball <= champion × 0.97
```

soit au moins ~3 % d'amélioration.

OU :

### Condition B — calibration

```text
Mean Pinball comparable
+
calibration nettement meilleure
```

OU :

### Condition C — ensemble

Le modèle améliore significativement un ensemble avec le champion.

---

## Contraintes opérationnelles

Même s'il est meilleur :

```text
runtime
RAM
reproductibilité
stabilité
licence
maintenance
```

doivent être acceptables.

---

# 27. Score composite facultatif

Pour aider la décision :

```text
score =
0.50 × normalized_mean_pinball
+
0.20 × calibration_error
+
0.10 × interval_score
+
0.10 × normalized_runtime
+
0.10 × stability_penalty
```

Ce score ne remplace pas les métriques brutes.

Il sert uniquement à classer les solutions proches.

---

# 28. Critères de No-Go

Un modèle est rejeté s'il présente l'un de ces symptômes.

## No-Go 1

```text
ne bat pas la baseline historique
```

sur une majorité de folds.

---

## No-Go 2

```text
excellent sur un fold
catastrophique sur les autres
```

---

## No-Go 3

Calibration :

```text
Q05 observé à 20 %
Q95 observé à 80 %
```

par exemple.

---

## No-Go 4

Le gain existe uniquement avec un hyperparamètre sélectionné après avoir regardé le test.

---

## No-Go 5

Runtime/infrastructure disproportionnés par rapport au gain.

Exemple :

```text
+0.3 % Pinball
mais GPU externe permanent requis
```

=> rejet probable.

---

# 29. Roadmap recommandée

## Sprint 1 — Benchmark framework

- [ ] implémenter folds purgés ;
- [ ] anchors mensuels ;
- [ ] métriques probabilistes ;
- [ ] tables PostgreSQL ;
- [ ] baseline B0 ;
- [ ] champion LightGBM reproductible.

### Exit criteria

```text
mêmes folds
mêmes anchors
mêmes métriques
```

pour tous les modèles.

---

## Sprint 2 — Chronos Small

- [ ] installer `chronos-forecasting` ;
- [ ] CPU smoke test Railway ;
- [ ] backtest `close` ;
- [ ] backtest `log(close)` ;
- [ ] vérifier Q25/Q75 interpolés ;
- [ ] mesurer RAM/runtime ;
- [ ] comparer à LightGBM.

### Exit criteria

Décision :

```text
abandon
ou
promotion vers Chronos full
```

---

## Sprint 3 — NHITS

- [ ] NeuralForecast ;
- [ ] MQLoss 5 quantiles ;
- [ ] input 730 ;
- [ ] input 1095 ;
- [ ] input 1460 ;
- [ ] 3 seeds sur meilleure config ;
- [ ] performance + stabilité + runtime.

---

## Sprint 4 — Regimes

- [ ] HMM 2 states ;
- [ ] HMM 3 states ;
- [ ] fit HMM par fold ;
- [ ] soft probabilities ;
- [ ] LightGBM + regimes ;
- [ ] analyser performance par état.

---

## Sprint 5 — Escalade

Si nécessaire :

- [ ] Chronos-2 full ;
- [ ] TimesFM 2.5 ;
- [ ] external GPU POC seulement si nécessaire.

---

## Sprint 6 — Ensemble

Seulement si :

```text
>= 2 modèles crédibles
+
erreurs suffisamment décorrélées
```

Alors :

- [ ] equal-weight ;
- [ ] optimized-weight ;
- [ ] calibration ;
- [ ] quantile crossing ;
- [ ] comparaison champion.

---

# 30. Recommandation finale

La stratégie à suivre n'est pas :

```text
LightGBM vs LSTM vs Transformer
```

comme une compétition de complexité.

La stratégie est :

```text
                Baselines
                    │
                    ▼
             LightGBM champion
                    │
        ┌───────────┼────────────┐
        │           │            │
        ▼           ▼            ▼
    Chronos       NHITS        Regimes
  pretrained    long horizon    HMM
        │           │            │
        └───────────┼────────────┘
                    │
                    ▼
           performance commune
                    │
              ┌─────┴─────┐
              │           │
             non         oui
              │           │
              ▼           ▼
          garder       ensemble
          champion      éventuel
```

### Priorité n°1

**Chronos-2-small**.

Pourquoi :

- zéro training ;
- 28M paramètres seulement ;
- contexte suffisamment grand pour tout l'historique ;
- horizon 365 compatible ;
- probabiliste ;
- test peu coûteux conceptuellement ;
- réellement différent de LightGBM.

### Priorité n°2

**NHITS + MQLoss**.

Pourquoi :

- architecture explicitement long-horizon ;
- quantiles natifs exactement alignés sur le besoin ;
- trajectoire probabiliste complète ;
- meilleur challenger neural from-scratch que LSTM/TFT dans ce contexte.

### Priorité n°3

**HMM + LightGBM**.

Pourquoi :

- faible coût ;
- conserve l'architecture actuelle ;
- peut capter les régimes BTC ;
- probablement meilleur ratio complexité/risque après Chronos.

### Priorité n°4

**Chronos-2 complet** si le small est déjà prometteur.

### Priorité n°5

**TimesFM 2.5**, comme foundation benchmark secondaire.

---

# 31. Décision cible après benchmark

Le résultat final pourrait être l'un des quatre scénarios suivants.

## Scénario A — LightGBM gagne

```text
Production = LightGBM Quantile
```

Aucune complexité supplémentaire.

---

## Scénario B — Chronos gagne

```text
Production =
Chronos zero-shot
+
PostgreSQL
+
Railway orchestration
```

Avec CPU si suffisamment performant, sinon inference externe ponctuelle.

---

## Scénario C — NHITS gagne

```text
Production =
NHITS
+
monthly retrain
+
daily inference
```

---

## Scénario D — aucun modèle domine

C'est probablement le résultat le plus intéressant.

Exemple :

```text
LightGBM meilleur en bear
Chronos meilleur en transition
NHITS meilleur en bull
```

ou :

```text
métriques proches
+
erreurs décorrélées
```

Dans ce cas :

```text
ensemble probabiliste
```

devient la meilleure architecture.

---

# 32. Ce qu'il ne faut pas faire

- ne pas choisir le modèle à partir d'une courbe visuellement jolie ;
- ne pas utiliser un random train/test split ;
- ne pas entraîner sur des fenêtres dont la target traverse le test ;
- ne pas comparer LightGBM J+365 à Chronos J+30 ;
- ne pas tuner sur le test final ;
- ne pas considérer les ~3650 jours comme ~3650 observations indépendantes pour un target 365d ;
- ne pas forcer TimesFM à produire Q05/Q95 par extrapolation non validée ;
- ne pas ajouter un GPU externe avant d'avoir démontré que le modèle en vaut la peine ;
- ne pas utiliser un LSTM juste parce qu'il est populaire dans les tutoriels Bitcoin ;
- ne pas remplacer le champion sur une seule seed ou un seul fold.

---

# 33. Sources techniques principales

## Chronos-2

- Amazon Chronos-2 repository / pipeline :  
  https://github.com/amazon-science/chronos-forecasting

- Chronos-2-small :  
  https://huggingface.co/autogluon/chronos-2-small

- Chronos-2 complet :  
  https://huggingface.co/amazon/chronos-2

- Chronos-2 paper :  
  https://arxiv.org/abs/2510.15821

Points vérifiés :

- Chronos-2-small : ~28M paramètres ;
- licence Apache-2.0 ;
- context length 8192 ;
- small quantiles natifs : 0.01, 0.05, 0.10, 0.20, ..., 0.95, 0.99 ;
- interpolation supportée pour les quantiles demandés non natifs ;
- Chronos-2 complet inclut Q25 et Q75 nativement.

---

## NHITS / NeuralForecast

- NHITS :  
  https://nixtlaverse.nixtla.io/neuralforecast/models.nhits.html

- Long-horizon NHITS :  
  https://nixtlaverse.nixtla.io/neuralforecast/docs/tutorials/longhorizon_nhits.html

- Probabilistic forecasting / MQLoss :  
  https://nixtlaverse.nixtla.io/neuralforecast/docs/tutorials/uncertainty_quantification.html

- MQLoss API :  
  https://nixtlaverse.nixtla.io/neuralforecast/losses.pytorch.html

---

## TimesFM 2.5

- Repository :  
  https://github.com/google-research/timesfm

- API reference :  
  https://github.com/google-research/timesfm/blob/master/timesfm-forecasting/references/api_reference.md

- Hugging Face :  
  https://huggingface.co/google/timesfm-2.5-200m-pytorch

Points vérifiés :

- ~200M paramètres ;
- context length 16 384 ;
- quantile horizon > 365 ;
- quantile output standard centré sur Q10–Q90 ;
- continuous quantile head disponible ;
- licence du checkpoint 2.5 : Apache-2.0.

---

## Railway

- Cron Jobs :  
  https://docs.railway.com/cron-jobs

- CPU / absence de GPU :  
  https://docs.railway.com/guides/ai-agent-workers

Le design de ce rapport suppose que :

```text
Railway = PostgreSQL + orchestration + CPU jobs
```

et qu'un GPU externe n'est ajouté que si un challenger suffisamment performant le justifie.

---

# 34. Note méthodologique

Ce projet produit des **prévisions probabilistes expérimentales** et non une certitude sur le prix futur du Bitcoin.

Même un modèle correctement backtesté peut subir :

- changement de régime structurel ;
- événement réglementaire ;
- choc macroéconomique ;
- changement de liquidité ;
- changement microstructurel ;
- événement propre au protocole Bitcoin ;
- distribution future différente de l'historique.

Le but du benchmark est donc de maximiser :

```text
calibration
robustesse
stabilité
transparence
```

plutôt que de produire un prix ponctuel artificiellement précis.

---

# 35. Résumé opérationnel en une page

```text
DONNÉES
BTC OHLC daily
~10 ans
        │
        ▼
PURGED WALK-FORWARD
365 jours de purge
anchors mensuels
        │
        ▼
BASELINES
Historical quantiles
Naive
        │
        ▼
CHAMPION
LightGBM Quantile
        │
        ├─────────────────────────┐
        │                         │
        ▼                         ▼
Chronos-2-small               NHITS + MQLoss
zero-shot                     h=365
        │                         │
        └──────────┐     ┌────────┘
                   ▼     ▼
                HMM + LightGBM
                 regime-aware
                       │
                       ▼
                 LEADERBOARD
                       │
     Mean Pinball / Calibration / Coverage
        MAE Q50 / Runtime / Stability
                       │
              ┌────────┴────────┐
              ▼                 ▼
        Champion unique      Ensemble
              │                 │
              └────────┬────────┘
                       ▼
                    PROD
                       │
        PostgreSQL + Railway Cron
```

**Ordre recommandé :**

```text
1. LightGBM baseline reproductible
2. Chronos-2-small
3. NHITS
4. HMM + LightGBM
5. Chronos-2 full si Small prometteur
6. TimesFM 2.5
7. Ensemble uniquement si les résultats le justifient
```

**Critère numéro un :**

```text
Le meilleur modèle est celui qui gagne sur un backtest temporel purgé,
pas celui dont la courbe semble la plus convaincante.
```
