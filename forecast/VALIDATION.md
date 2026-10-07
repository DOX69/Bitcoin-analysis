# Validation locale du pipeline Forecast V1

Mesure du 9 septembre 2026 pour [Implémenter le pipeline du modèle et les artefacts reproductibles](https://github.com/DOX69/Bitcoin-analysis/issues/84). Contrat et commandes dans [README.md](README.md).

## Résultat

Le pipeline et ses contrôles logiciels sont validés localement. Aucun candidat probabiliste ne passe tous les garde-fous historiques de première version. Aucune promotion. Ces observations restent exploratoires et ne remplacent pas une confirmation prospective. La référence de dernier close est affichée séparément à titre de contrôle, pas comme une recette candidate.

| Recette | WIS USD | MAE USD | Durée totale s | Pic RSS arbre Mio | Artefacts recette Mio | Horizons en échec |
|---|---:|---:|---:|---:|---:|---:|
| référence holdout — dernier close | 16157.37 | 16157.37 | — | — | — | contrôle |
| gaussian_random_walk | 17911.19 | 22781.65 | 0.76 | 59.79 | 1.44 | 52/52 |
| lightgbm_quantile | 17148.07 | 24198.92 | 71.37 | 244.91 | 77.59 | 51/52 |

La référence holdout répète le dernier close connu à chaque origine de test et n'est jamais entraînée ni publiée. Elle n'a pas de bande probabiliste : ses quantiles identiques ne servent qu'à comparer la médiane et le WIS. Les échecs comptent les horizons ne respectant pas au moins un contrôle de MAE ou de couverture. Les contrôles ne se limitent pas aux moyennes du tableau.

Les deux recettes candidates passent les limites de ressources. Le processus de calcul LightGBM a été observé avec une affinité de deux processeurs. Les durées incluent deux entraînements de folds, leurs prédictions et contrôles de rechargement, puis un entraînement final sur 581 semaines. Tous les rechargements passent la tolérance figée de `rtol=1e-10`, `atol=1e-8` USD.

Taille totale du dossier vérifié, rapports et inventaire inclus : 85417979 octets. Aucune dépense Railway. Les estimations CPU/RAM équivalentes du JSON ne comprennent pas le futur stockage, les sauvegardes ou les transferts.

## Protocole et provenance

- 581 semaines complètes, du lundi 20 juillet 2015 au dimanche 6 septembre 2026. Le dernier label CSV est le lundi 31 août 2026.
- Coupures de 348 et 464 observations. Respectivement 64 et 65 origines évaluées, avec 52 cibles matures par origine.
- Première période : origines du 21 mars 2022 au 5 juin 2023. Deuxième période : du 10 juin 2024 au 1er septembre 2025. Ces dates désignent le lundi de la semaine observée.
- Modèles, variables, paramètres et quantiles conformes à la recette acceptée. Aucune recalibration.
- Snapshot SHA-256 : `95fa242dd1a907a8cb7b122fb1ea974542c0541b0d3e14135197ac2e3c4d571b`.
- Manifeste vérifié SHA-256 : `3183b4e20768032da2ade261ad4a8c185cca9d5d9ea91efa8671f9e765bbac9a`.
- Dossier local : `%TEMP%\bitcoin-forecast-84-verified`. Il contient snapshot, lock, code archivé, modèles des folds et finaux, prévisions, rapports et inventaire SHA-256.

Un premier passage a révélé que Windows lançait un interpréteur enfant non compté par le superviseur initial. La mesure retenue additionne tous les RSS descendants. Le test reproduit ce défaut avec 128 Mio alloués dans un enfant, puis vérifie son arrêt. Les mêmes recettes ont été rejouées après cette correction de surveillance. Les prévisions et les 780 fichiers LightGBM sont identiques octet par octet entre les deux passages. Aucun paramètre de modèle ni aucune fenêtre modifiés.

## Horizons de synthèse

| Recette | Horizon semaines | WIS USD | MAE USD | Couverture 50 % | Couverture 80 % |
|---|---:|---:|---:|---:|---:|
| référence holdout — dernier close | 1 | 2686.82 | 2686.82 | 0.0% | 0.0% |
| référence holdout — dernier close | 4 | 5616.13 | 5616.13 | 0.0% | 0.0% |
| référence holdout — dernier close | 13 | 11439.15 | 11439.15 | 0.0% | 0.0% |
| référence holdout — dernier close | 26 | 16725.06 | 16725.06 | 0.0% | 0.0% |
| référence holdout — dernier close | 52 | 26539.07 | 26539.07 | 0.0% | 0.0% |
| gaussian_random_walk | 1 | 2196.83 | 2754.63 | 76.0% | 93.8% |
| gaussian_random_walk | 4 | 4679.58 | 6106.10 | 66.7% | 91.5% |
| gaussian_random_walk | 13 | 9814.15 | 13263.73 | 58.9% | 91.5% |
| gaussian_random_walk | 26 | 16469.04 | 19679.47 | 69.0% | 86.0% |
| gaussian_random_walk | 52 | 36513.11 | 47228.61 | 55.0% | 79.1% |
| lightgbm_quantile | 1 | 2063.71 | 2880.22 | 42.6% | 80.6% |
| lightgbm_quantile | 4 | 4307.88 | 6468.09 | 41.9% | 80.6% |
| lightgbm_quantile | 13 | 9062.30 | 11783.75 | 50.4% | 73.6% |
| lightgbm_quantile | 26 | 18704.64 | 27247.39 | 37.2% | 70.5% |
| lightgbm_quantile | 52 | 28788.32 | 32041.55 | 48.1% | 65.9% |

Le JSON conserve les 52 horizons, les deux périodes, les prédictions appariées et les blocs contigus de longueur h. Les blocs annuels sont peu nombreux et les erreurs se chevauchent. Aucune inférence d’indépendance ni intervalle binomial utilisé comme preuve.

## Vérifications exécutées

- `uv run --locked --extra dev --extra benchmark pytest forecast -q` : 29 tests réussis.
- `uv lock --check`, Ruff, Black et `git diff --check` : réussis.
- Nouveau job CI forecast configuré avec les dépendances verrouillées. CI distante non exécutée dans cette session, aucun push.
- Pas de modification UI, stockage distant, promotion ou déploiement. Les autres lots conservent leur périmètre.
