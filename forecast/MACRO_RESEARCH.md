# Ablation macro avec millésimes ALFRED

Essai borné exécuté le 20 septembre 2026. Il reste séparé de `daily-v1` et ne
modifie ni les émissions Development ni le registre Production.

## Contrat point-in-time

Le snapshot Bitcoin est `C:/Users/ggrft/forecast-evidence/20260914/trend-daily.json`,
du 20 juillet 2015 au 13 septembre 2026. Les origines sont les mêmes dimanches
que dans les essais quotidiens précédents. La partition ancienne contient 139
origines et la partition récente 104.

Les trois séries macro sont `DFF`, `CPIAUCSL` et `UNRATE`. Pour chaque dimanche,
le collecteur demande à ALFRED le dernier millésime dont la date est antérieure
ou égale à l'origine. Pour chaque série, il ne conserve ensuite que les
observations dont la date est antérieure ou égale à cette origine, puis reporte
la dernière valeur connue. Les features sont le niveau et la variation à sept
jours. Une valeur future ou une révision future ne peut donc pas modifier une
ligne passée.

ALFRED a retourné au plus 12 colonnes de millésime par CSV, même lorsque
25 dates étaient demandées. Le parseur vérifie l'en-tête et les lots ont été
refaits avec 12 dates. Les fichiers bruts vérifiés sont conservés hors Git dans
`C:/Users/ggrft/forecast-evidence/20260920/macro-alfred-v5/raw/`.

L'archive complète de l'essai est
`C:/Users/ggrft/forecast-evidence/20260920/macro-alfred-v6/`. Elle contient le
snapshot macro fusionné, le manifeste avec les empreintes des 147 fichiers
bruts, le rapport et le journal supervisé. Le run a duré 77,6 secondes avec un
pic RSS cumulé de 1,14 Gio, sous les limites de 2 threads, 4 Gio et 30 minutes.

## Comparaison gelée

`daily_pooled_research.py` est utilisé sans changement. Prix seul et prix plus
macro partagent les mêmes lignes quotidiennes, origines, 365 cibles, paramètres,
calibration et métriques. Le candidat macro devait battre le prix inchangé et
le modèle prix seul dans les deux partitions, avec les garde-fous à J+1, J+7,
J+30, J+90, J+180 et J+365.

| Partition | Modèle | MAE USD | WIS |
|---|---|---:|---:|
| Ancienne | Prix inchangé | 15 173 | 12 864 |
| Ancienne | Prix seuls | 18 528 | 14 787 |
| Ancienne | Prix + macro | 28 722 | 20 113 |
| Récente | Prix inchangé | 21 764 | 15 244 |
| Récente | Prix seuls | 32 494 | 23 786 |
| Récente | Prix + macro | 30 472 | 25 519 |

Le macro améliore la MAE du prix seul de 6,2 % dans la partition récente, mais
il perd le prix inchangé de 40,0 %. Dans la partition ancienne, il perd le prix
seul de 55,0 % et le prix inchangé de 89,3 %. Son WIS est supérieur à la
référence dans les deux partitions.

Décision : `reject_all_challengers`. Le signal externe est réellement différent,
mais cette recette ne fournit pas un gain robuste. Aucun modèle n'est promu.
Le fallback prix inchangé reste la référence opérationnelle, sans être présenté
comme une capacité prédictive. Une suite devrait changer l'hypothèse, pas
simplement retuner cette recette sur les mêmes résultats.

## Limites

Les millésimes ALFRED évitent la révision rétrospective des valeurs, mais ne
prouvent pas à eux seuls l'heure exacte de publication dans la journée. Le
contrat conservateur utilise des snapshots du dimanche et peut donc retarder
une information publiée pendant la semaine. Les trois séries sont américaines
et ne couvrent pas toute l'information macro mondiale. L'essai reste une
relecture historique ; il ne constitue pas une confirmation prospective.

Le protocole ALFRED décrit les périodes temps réel et les millésimes dans la
[documentation FRED](https://fred.stlouisfed.org/docs/api/fred/series_observations.html).
