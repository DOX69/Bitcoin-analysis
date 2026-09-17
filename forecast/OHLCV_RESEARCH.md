# Volumes et amplitudes quotidiens — 17 septembre 2026

## Résultat

Les volumes et amplitudes Coinbase n'améliorent pas l'erreur centrale dans cette
recette. Les trois variantes enrichies sont rejetées. Aucun changement au modèle
affiché en Development, au cron ni au registre Production.

| Variables du modèle | MAE ancienne, USD | MAE récente, USD | WIS ancien | WIS récent |
|---|---:|---:|---:|---:|
| Prix inchangé, référence | 15 173,32 | 21 763,80 | 12 864,41 | 15 243,85 |
| Prix seuls, modèle non linéaire | 18 527,96 | 32 493,58 | 14 787,45 | 23 786,21 |
| Prix + volume | 18 529,44 | 32 549,28 | 14 773,33 | 23 898,31 |
| Prix + amplitude | 18 541,37 | 32 932,19 | 14 602,65 | 23 744,96 |
| Prix + volume + amplitude | 18 548,16 | 32 898,81 | 14 590,52 | 23 795,03 |

L'ajout des deux variables augmente la MAE de 0,11 % sur l'ancienne période et
1,25 % sur la récente par rapport au modèle prix seuls. Le petit gain de WIS sur
l'ancienne période ne se retrouve pas sur la récente. Ces résultats ne démontrent
pas que le volume est inutile pour tout modèle ; ils rejettent cette recette fixe.

## Audit des données

Lecture seule de `Development bronze.btc_usd_ohlcv`, dernière révision stockée par
date lors de l'export. Ordre de révision : `ingest_date_time DESC, run_id DESC`.
Pas de nouvelle API, pas de nouvelle clé, aucune écriture dans Railway.

- 4 074 journées du 20 juillet 2015 au 13 septembre 2026, sans trou ni doublon.
- Clôtures strictement identiques au snapshot du benchmark précédent.
- Prix finis et positifs ; low ≤ open/close ≤ high ; volumes finis et non négatifs.
- Aucun volume nul dans cet export. Le validateur accepte toutefois zéro comme
  observation possible et les features utilisent `log1p`.
- Ingestions du 30 août au 14 septembre 2026 : ce ne sont pas des millésimes
  historiques connus à chaque origine. La validation reste rétrospective et
  exploratoire sur un historique déjà examiné.
- Volume de la source Coinbase ; il ne représente pas l'ensemble du marché Bitcoin.

SHA-256 de l'export OHLCV :
`f2b595b15dc68d512bbdf69dec65ec16e7cfdc60f18f4da4eb156212b942f491`.

## Comparaison gelée avant calcul

Les quatre variantes partagent le modèle LightGBM de
[`daily_pooled_research.py`](daily_pooled_research.py), ses paramètres, les mêmes
origines et les mêmes cibles. Aucun ajustement de paramètres après lecture des scores.

- Prix seuls : six features quotidiennes déjà définies.
- Volume : logarithme `log1p(volume)` du jour moins sa moyenne sur 30 jours,
  puis moyenne sur 7 jours moins moyenne sur 30 jours.
- Amplitude : moyennes sur 7 et 30 jours de `log(high/low)`.
- Toutes les fenêtres incluent uniquement les journées complètes connues jusqu'à
  l'origine. Pas de normalisation sur la série entière ni de valeurs futures.

Chaque variante effectue 373 entraînements aux origines du dimanche, simulant le
recalcul du lundi. Les exemples d'entraînement sont quotidiens, sur trois ans,
avec labels matures. Neuf horizons d'entraînement sont fixés ; le modèle produit
365 prédictions directes. Les quantiles sont calibrés sur les seules erreurs matures.

Évaluation : 139 origines anciennes et 104 récentes, avec 365 cibles matures par
origine. Une variante enrichie doit satisfaire le filtre existant contre le prix
inchangé **et** contre le modèle prix seuls : gain MAE et WIS d'au moins 2 % dans
chaque période, sans dépasser 5 % de surerreur MAE aux jours 1, 7, 30, 90, 180 et
365. Ce filtre de recherche ne remplace pas les critères de production.

Le recalcul prix seuls reproduit exactement toutes les métriques agrégées et
par horizon du précédent essai, ainsi que celles de la référence prix inchangé.
Les différences observées proviennent donc de l'ajout des features.

## Reproduction et vérifications

Runner : [`daily_ohlcv_research.py`](daily_ohlcv_research.py).
Archive locale : `C:/Users/ggrft/forecast-evidence/20260917/daily-ohlcv-v1/`.
Elle contient les deux snapshots, le manifeste écrit avant entraînement, les
sources Python, le lock, les versions, les métriques par horizon et les ressources.
Le dossier de sortie doit être nouveau ; aucun écrasement d'expérience.

```powershell
uv run --locked --extra forecast python -m forecast.daily_ohlcv_research --snapshot C:/Users/ggrft/forecast-evidence/20260917/ohlcv-snapshot.json --reference C:/Users/ggrft/forecast-evidence/20260914/trend-daily.json --output C:/Users/ggrft/forecast-evidence/20260917/daily-ohlcv-replay
```

L'essai exécuté a été lancé avec `forecast.pipeline.supervise`, limite de
30 minutes et 4 Gio pour l'arbre des processus, threads numériques limités à deux.
Mesure : 124,60 secondes, pic RSS de 172,13 Mio. La commande ci-dessus lance le
runner seul ; utiliser ce superviseur pour imposer également les limites temps/RAM.

145 tests forecast passent localement ; 18 tests dépendants de services sont
sautés localement et exécutés en CI. Les nouveaux tests couvrent les bornes OHLC,
les clôtures divergentes, les trous, les timestamps futurs, l'insensibilité aux
volumes/amplitudes futurs et l'obligation de battre les deux références. Ruff,
Black et la vérification du diff passent.

## Décision

Pas de déploiement de cette recette. Les pistes macroéconomiques à disponibilité
historique et modèles multivariés préentraînés restent celles documentées dans
[`RECOVERY_RESEARCH.md`](RECOVERY_RESEARCH.md), avec leurs prérequis. Aucun résultat
de cet essai ne justifie de les annoncer gagnantes ou de qualifier le forecast
actuel pour la production.
