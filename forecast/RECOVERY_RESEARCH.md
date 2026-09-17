# Reprise des recherches quotidiennes — 17 septembre 2026

## Problème

La recette daily-v1 sélectionnait obligatoirement Holt ou Ridge, même lorsque les
deux perdaient face au prix inchangé. Le Ridge affiché en Development atteint
42 792 USD de MAE contre 21 764 USD pour cette référence sur la période récente.
Une courbe mobile ne constitue donc pas une amélioration prédictive.

Les partitions historiques ont déjà été examinées. Tous les essais ci-dessous
sont exploratoires ; aucun ne constitue une confirmation prospective. Aucun
seuil de production, registre actif ou ancien fichier de prévision n'est modifié.

## Trois approches distinctes étudiées

### 1. Modèle quotidien non linéaire partagé entre horizons — retenu pour essai

- **Preuves examinées :** `daily_research.py` utilise six variables de prix et des
  régressions linéaires séparées ; `benchmark.py` contient déjà du LightGBM
  hebdomadaire. La nouvelle recette partage un modèle entre horizons et emploie
  les origines quotidiennes : elle ne répète pas le benchmark hebdomadaire.
- **Changement :** petits arbres LightGBM, objectif erreur absolue, horizon comme
  variable, rendement logarithmique divisé par la racine de l'horizon comme cible.
  Entraînement sur trois ans de jours, labels arrivés à échéance uniquement.
  Neuf horizons d'entraînement fixés avant l'essai ; 365 requêtes directes au modèle.
- **Bénéfice attendu :** capter des relations non linéaires et partager davantage
  d'exemples entre échéances sans extrapoler une régression linéaire indépendante.
- **Risques/coût :** surapprentissage, observations dépendantes et ruptures de
  régime ; le même historique ne fournit aucune information externe nouvelle.
  Deux threads, arbres peu profonds, une seule configuration sans recherche de paramètres.
- **Prérequis :** snapshot quotidien et LightGBM déjà présent dans les dépendances.
- **Pourquoi cela peut éviter l'échec :** la forme fonctionnelle et le partage des
  observations changent ; la sélection peut rejeter tous les candidats.

Les paramètres de complexité et l'objectif proviennent de la
[documentation LightGBM](https://github.com/lightgbm-org/LightGBM/blob/main/docs/Parameters.rst).
Cette documentation ne garantit aucun gain sur Bitcoin.

### 2. Variables macroéconomiques avec leurs dates réelles de disponibilité

- **Preuves examinées :** les features actuelles dérivent uniquement du prix.
  Les collecteurs du dépôt couvrent Coinbase, Frankfurter et BGeometrics ; ils ne
  constituent pas une archive ALFRED des publications et révisions macroéconomiques.
- **Changement :** construire des jointures à la date de disponibilité avec des
  séries macroéconomiques ALFRED, puis une ablation prix seuls/prix et macro.
- **Bénéfice attendu :** apporter une information différente du seul passé de Bitcoin.
- **Risques/coût :** ingénierie de données supplémentaire, fréquences mixtes,
  retards de publication ; les séries révisées actuelles introduiraient une fuite.
- **Prérequis :** accès API FRED autorisé et archives des millésimes, contrôles des
  dates de publication ; aucune recherche ni copie de secret effectuée ici.
- **Pourquoi cela peut éviter l'échec :** ajoute un signal absent des recettes de prix,
  si ce signal possède une relation stable avec les rendements futurs.

FRED distingue les données connues aujourd'hui des données connues à une date
passée via les [périodes temps réel](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).
Son API de [dates de millésimes](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html)
documente les révisions et l'authentification. Cette piste n'est pas implémentée.

### 3. Modèle préentraîné multivarié quotidien avec covariables

- **Preuves examinées :** `RESEARCH.md` décrit déjà Chronos-2-small en hebdomadaire
  univarié ; le retester à l'identique ne serait pas une nouvelle approche.
  Chronos-2 prend en charge séries multiples et covariables passées.
  Le modèle dbt `obt_fact_day_eth.sql` est actuellement une table vide de
  remplacement (`LIMIT 0`) : sa présence dans le dépôt ne prouve pas un historique ETH.
- **Changement :** contexte quotidien Bitcoin et séries connexes disponibles à
  l'origine, par exemple Ethereum et volume, avec prévision à 365 jours.
- **Bénéfice attendu :** transférer des motifs appris et les relations entre séries,
  sans entraîner un grand réseau local sur les seules observations Bitcoin.
- **Risques/coût :** dépendances isolées, mesure CPU/mémoire à refaire à cette taille,
  contexte/horizon supportés à vérifier, couverture historique des covariables,
  chevauchement possible avec le corpus de préentraînement.
- **Prérequis :** checkpoint figé, licence et provenance examinées, covariables
  alignées sans valeurs futures, preuve de faisabilité à 365 jours sous budget.
- **Pourquoi cela peut éviter l'échec :** exploite des relations multivariées et un
  apprentissage externe plutôt que la seule extrapolation du prix local.

La capacité multivariée est décrite par
[Amazon Science](https://www.amazon.science/blog/introducing-chronos-2-from-univariate-to-universal-forecasting).
Elle ne démontre ni une supériorité à un an sur Bitcoin ni l'indépendance du test.
Cette variante quotidienne multivariée n'est pas implémentée.

## Diagnostic préalable

Archive locale : `C:/Users/ggrft/forecast-evidence/20260917/daily-recovery-v1`.
Snapshot : SHA-256 `31dd26899a74f86a7b968aa77bdcd9611f4b5d84ac88df57566c8b93ac94b4b1`.

| Recette | MAE période ancienne, USD | MAE période récente, USD |
|---|---:|---:|
| Ridge affiché en Development | 27 113 | 42 792 |
| Médiane Ridge préservée lors de la calibration | 20 143 | 30 122 |
| Rendement Ridge atténué après 30 jours | 15 225 | 21 756 |
| Prix inchangé | 15 173 | 21 764 |

La calibration de médiane explique une partie de la surerreur. Atténuer le
rendement rapproche presque entièrement la prévision du prix inchangé : gain
récent de seulement 0,034 %, perte ancienne de 0,34 %. Aucun candidat retenu.
Ces deux modifications de Ridge appartiennent à la même approche ; elles ne
comptent pas comme trois solutions distinctes.

## Essai retenu et protocole gelé

`daily_pooled_research.py` écrit son manifeste et archive ses sources avant
entraînement. Le runner calcule les prévisions à partir des closes du dimanche,
pour simuler le recalcul du lundi. La calibration utilise les dernières erreurs
arrivées à échéance à chaque horizon ; la médiane brute est conservée.

Filtre de recherche, distinct des critères de production : MAE et WIS au moins
2 % meilleurs que le prix inchangé dans chacune des deux partitions ; MAE au
plus 5 % pire aux jours 1, 7, 30, 90, 180 et 365 dans chaque partition. Sinon,
aucun candidat retenu. Un passage exigerait encore validation et suivi prospectif.

Reproduction :

```powershell
uv run --locked --extra forecast python -m forecast.daily_pooled_research --daily C:/Users/ggrft/forecast-evidence/20260914/trend-daily.json --output C:/Users/ggrft/forecast-evidence/20260917/daily-pooled-v1
```

## Résultat du modèle partagé

373 entraînements hebdomadaires terminés. Évaluation sur 139 origines anciennes
et 104 récentes, avec 365 cibles matures par origine.

| Période | MAE modèle / référence, USD | WIS modèle / référence | Décision |
|---|---:|---:|---|
| Ancienne | 18 528 / 15 173 | 14 787 / 12 864 | Rejet |
| Récente déjà examinée | 32 494 / 21 764 | 23 786 / 15 244 | Rejet |

L'erreur augmente respectivement de 22,1 % et 49,3 %. À J+180, elle dépasse la
référence de 17 % et 20 % ; réduire l'horizon à six mois ne résout donc pas
l'échec de cette recette. À J+365, les excès sont de 30 % et 90 %.

Les tests vérifient que modifier les prix futurs ne change ni les exemples
d'entraînement ni les 365 prédictions ; ils vérifient aussi la présence d'origines
quotidiennes et l'exclusion des labels immatures. Le filtre refuse un candidat
qui perd dans une période ou à un horizon contrôlé, même si sa moyenne est bonne.

## Décision opérationnelle

Ne pas déployer cette nouvelle recette. La prévision Ridge déjà visible en
Development reste une expérimentation désactivée par défaut avec son avertissement.
Le présent changement ajoute des outils de recherche et un rejet explicite des
candidats perdants ; il ne remplace pas rétroactivement la recette daily-v1 figée.

La prochaine piste recommandée est l'ajout de variables externes avec historique
de disponibilité, en commençant par auditer les séries déjà collectées avant
d'ajouter une API. Les essais sur le seul prix n'ont pas fourni de gain robuste.
Le collecteur Coinbase expose déjà les colonnes OHLCV ; leur volume et leur
amplitude quotidienne sont les premières variables à auditer, sans nouvelle clé
API. Leur disponibilité et leur qualité dans le snapshot de recherche restent à
vérifier ; le snapshot utilisé ici ne contient que le close et sa provenance.
Il faudra comparer prix seuls et prix avec variables sur des origines identiques,
geler la recette, puis conserver les nouvelles émissions et observations réelles.
Le 21 septembre est une date de suivi, pas une validation automatique à un an.

La livraison Production reste non acquise. Aucun accès supplémentaire n'est
nécessaire pour reproduire l'essai terminé ; une collecte ALFRED demanderait un
accès API et un chantier de données distinct. Aucun achat ni déploiement de modèle
préentraîné supplémentaire n'a été engagé.
