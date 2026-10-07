# Archive des recettes et matériaux retirés

Nettoyage local du 7 octobre 2026, depuis le commit `86fe0207493e68ae5edbcafedbef7278268f6035`. La seule collecte prospective conservée est LightGBM hebdomadaire. Gaussian random walk et les baselines restent nécessaires aux comparaisons et aux tests du registre.

## Récupération

Archive hors Git : `C:/Users/ggrft/forecast-evidence/cleanup-20261007-86fe020/`.

- `repository-before-cleanup.zip` : checkout complet suivi par Git, avec ancien verrou, sources, tests et documents. SHA-256 : `99abaf214b82714fbaa839a274b5f2dc4beee0bf27723a1a00a96c684479eda0`.
- `retired-files-exact.zip` : les 69 fichiers retirés, avec leurs octets Windows exacts, vérifiés avant suppression. SHA-256 : `4f00d5091ea8188930454d177787b684e7886092bb55a8c1ffa906e0cbcf0ef0`.
- `cleanup-state.json` : inventaire, commit, paramètres, variables, quantiles et versions numériques conservés.
- `before-model/` : modèle LightGBM entraîné avant nettoyage sur la fixture synthétique des tests, pour vérifier la parité après nettoyage. Ce modèle de test n'est pas une preuve de qualité prédictive.

Pour rejouer un résultat ancien, extraire le checkout complet dans un dossier séparé, puis superposer l'archive exacte si les octets locaux sont nécessaires. Utiliser le verrou et le manifeste de ce résultat ; ne pas remplacer son code par le checkout nettoyé. Le commit d'origine reste aussi récupérable dans l'historique Git.

## Contenu retiré

Les expériences Chronos, Chronos2, N-HiTS, linéaires, régimes, normalisation, empilement, Student, tendance amortie, OHLCV, macro, multiscale et récupération quotidienne ne sont plus des runners actifs. Le suivi hybride, son audit et le forecast quotidien Ridge sont archivés avec leurs tests et documents. Leurs résultats exploratoires ne valident pas une promotion.

Les longs plans de brainstorming et rapports de challengers, les variantes de layout sans consommateurs, le calibrateur inutilisé, les configurations Databricks désactivées, le verrou Python imbriqué, l'export requirements et les sorties locales de tests sont également retirés.

Les rapports cloud, émissions immuables, modèles, snapshots et sauvegardes historiques restent dans leurs namespaces S3. Les preuves locales antérieures sous `C:/Users/ggrft/forecast-evidence/20260913/` restent conservées. Ce nettoyage ne déploie rien et ne supprime aucun objet distant.

Les documents actifs sont [le contrat du pipeline](README.md), [l'exploitation Development](DEVELOPMENT_RESEARCH.md) et [les conditions de publication](READINESS.md). Le verrou de dépendances actif est `uv.lock` à la racine.
