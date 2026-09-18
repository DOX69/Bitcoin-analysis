# Confirmation prospective sur Railway Development

Le suivi utilise `bitcoin-cron` dans Development, avec PostgreSQL et les deux buckets privés existants. La recette reste en recherche, sans version active ni publication sur le dashboard. La production utilise un autre service et n'est pas ciblée par cette configuration.

## Horaire et entrée

L'objectif est 07:00 Europe/Paris chaque jour. Railway interprète les expressions cron en UTC. Configurer `0 5,6 * * *` et l'entrée `forecast.development_cron` : elle quitte aussitôt si l'heure locale n'est pas 07:00. Cela conserve le même horaire lors des changements été/hiver, sans ordonnanceur permanent ni deuxième traitement quotidien. Railway peut démarrer quelques minutes après l'heure prévue, selon sa [documentation cron](https://docs.railway.com/cron-jobs).

Build : `uv sync --locked --all-packages --extra forecast`.

Démarrage : `uv run --locked --extra forecast --no-sync python -m forecast.development_cron`.

Conserver `restartPolicyType=NEVER`. Utiliser Python 3.11.9 pour correspondre au runtime figé du candidat. Le worker refuse des versions numériques différentes. L'option `--run-now` permet une vérification manuelle du pipeline avec l'horloge réelle ; elle ne modifie jamais les dates des émissions.

Le binaire Python 3.11.9 publié en 2024 ne possède pas l'attestation GitHub exigée par le builder Mise actuel. Development utilise `MISE_PYTHON_GITHUB_ATTESTATIONS=false` pour ce seul outil, conformément au [réglage Mise](https://mise.jdx.dev/lang/python.html#python-github-attestations). Le journal confirme le calcul du checksum Python et la vérification de l'attestation uv. Les dépendances du modèle restent exactement figées. Le contrôle des sources accepte seulement la conversion LF/CRLF effectuée par Git, sans changement de contenu.

Les variables non secrètes sont :

```text
FORECAST_RESEARCH_CONFIG=/app/forecast/development-config.json
FORECAST_BACKUP_CONFIG=/app/forecast/development-config.json
```

Les commandes `RAILPACK_BUILD_CMD` et `RAILPACK_START_CMD`, si présentes, doivent correspondre au build et au démarrage ci-dessus. Les accès PostgreSQL et S3 restent dans les variables privées du service.

## Exécution et conservation

Après ingestion et dbt réussis, l'orchestrateur appelle `forecast.cloud_research` dans un worker limité à deux CPU, 4 Gio et cinq minutes. Son échec n'annule pas l'ingestion. Le mécanisme de sauvegarde existant s'exécute aussi après échec.

Le worker lit les clôtures directement dans PostgreSQL et vérifie leur concordance avec la révision bronze connue. Il recharge depuis S3 le manifeste, la distribution et la prévision figés du 10 septembre. Toutes les données sont conservées sous `development/research/hybrid-v1/` :

- `bundle/` : modèle de recherche et archive originale, vérifiés par empreinte.
- `snapshots/` : observations quotidiennes et révisions, adressées par SHA-256.
- `emissions/` : une émission par semaine, créée le lundi ou lors de la reprise du mardi.
- `reports/` : scoring daté sur cibles matures, avec les 52 horizons et leurs blocs.
- `budget/AAAA-MM.json` : relevé et projection mensuels exigés avant calcul.

Un verrou PostgreSQL empêche deux collectes concurrentes. Les écritures S3 sont conditionnelles et relues. Chaque snapshot, émission et rapport est aussi copié dans le bucket indépendant avant succès. Une reprise répare une copie interrompue sans réécrire l'original. Un nouveau conteneur recharge les émissions et leurs données sources ; aucun disque local persistant n'est nécessaire.

La première archive du 10 septembre est incluse uniquement si son empreinte exacte correspond à celle déjà consignée dans RESEARCH.md. Les nouvelles émissions restent aux jours autorisés. Les rapports ne déclarent jamais un modèle publiable automatiquement.

## Budget et exploitation

La collecte réutilise l'allocation « jobs forecast » du scénario [COST.md](COST.md), le modèle de production étant désactivé. Le relevé Railway du 13 septembre indique 2,139655 USD pour tout le projet depuis le 21 août. Ce total incluant août et la production sert de borne conservatrice du coût cumulé de septembre à cette date, pas de mesure marginale exacte. La projection Development retenue reste 4,72 USD, avec sauvegardes et transferts. Le premier chargement a vérifié 68 986 octets, copies indépendantes comprises.

Avant chaque nouveau mois, publier un nouveau relevé vérifié sous `budget/AAAA-MM.json` dans les deux buckets. Une absence de relevé, un mois périmé ou un total mesuré/projeté atteignant cinq USD suspend les nouveaux calculs. Les sauvegardes continuent. Le cron n'a pas d'identifiant d'administration Railway et ne peut pas inventer les prochains relevés de facturation.

Les journaux `Forecast research status` indiquent le nombre d'émissions, de cibles matures et la clé du rapport. `ready_for_confirmation_review` dans ce rapport déclenche le besoin d'examiner les blocs temporels ; ce booléen n'est pas une promotion. Toute recette nouvelle demande sa propre confirmation.

Rollback : retirer `FORECAST_RESEARCH_CONFIG` pour suspendre seulement la recherche, ou restaurer l'image précédente du cron. Conserver les objets et leurs copies. Ne pas appliquer de migration descendante pour annuler ce déploiement.

## Preuve cloud du 13 septembre 2026

Le déploiement `7434f703-c1e3-4d0e-a870-6d6487c0194f`, issu du commit `b78f8a53`, a exécuté le pipeline réel. dbt termine avec 92 succès, aucune erreur. La collecte dure 2,00 secondes, avec 126 054 400 octets de RSS maximal. La sauvegarde termine aussi, avec 1 229 273 octets archivés. Le runtime Python et les cinq dépendances numériques correspondent au manifeste original.

Le rapport `development/research/hybrid-v1/reports/20260913T194010364418Z.json` porte l'empreinte `1f3c0a8b1e24c898cc2662063535b9bc249b711bf928b91638b94ce972a6926b`. Son snapshot porte l'empreinte `3ad3d1979bd22a249de109efdf7cf85fbcea7c8c0db181e155c3426f70a2aded`. Une relecture indépendante a vérifié les deux objets dans les deux buckets. Le rapport contient l'émission originale et zéro cible mature ; `publishable=false`.

L'automatisation Codex de 09:00 a été supprimée après cette vérification. Le démarrage permanent n'inclut pas `--run-now`. La prochaine échéance annoncée par Railway est le 14 septembre à 05:00 UTC, soit 07:00 Europe/Paris.

## Première émission hebdomadaire du 14 septembre

Le lancement planifié à 07:03 Europe/Paris a échoué sur un timeout de lecture Frankfurter après dix secondes. Le forecast n'a pas été exécuté ; la sauvegarde a réussi. La reprise manuelle avec l'horloge réelle a terminé à 07:24. dbt passe ses 92 contrôles. Le collecteur conserve deux émissions, dont l'archive du 10 septembre, et une cible mature. Le modèle reste en recherche.

L'émission de la semaine d'origine `2026-09-07` a été créée le `2026-09-14T05:24:02.309673+00:00`, avec 52 horizons. Son objet `development/research/hybrid-v1/emissions/2026-09-07.json` porte l'empreinte `11125d88dba0e5e99f1a4ffa3a6897fa85b09d2b8873d90f1b8df29fe097c942`. Le rapport `development/research/hybrid-v1/reports/20260914T052402309673Z.json` porte l'empreinte `1e8dd065cac5e36852473e66901846543c83f2608224585280b16e586f9a8ade`. Émission, rapport et snapshot ont été relus dans les deux buckets avec égalité des octets.

Le fetcher Frankfurter ajoute deux reprises de la même page sur timeout ou coupure de connexion, espacées de une puis deux secondes. Chaque tentative conserve le timeout de dix secondes. Après trois échecs, il propage l'erreur sans retourner les pages partielles. Les réponses HTTP invalides et les erreurs de contenu restent des échecs immédiats.

## Aperçu dans le dashboard Development

À la demande du propriétaire, le dashboard réutilise le prototype Wayfinder validé : bouton Forecast éteint au chargement, médiane Q50 dorée pointillée, bande Q25–Q75 et sélection des trois dernières émissions. L'aperçu lit les émissions hebdomadaires réelles dans le bucket privé. Il porte la mention « Prévision expérimentale · erreur historique supérieure au prix inchangé · non validée pour la production ». Les taux EUR/CHF proviennent des révisions bronze connues au moment de l'émission ; aucun taux futur n'est appliqué.

Le web active cette lecture uniquement si `RAILWAY_ENVIRONMENT_NAME=Development` et `FORECAST_RESEARCH_PREVIEW=true`. Définir côté serveur `FORECAST_RESEARCH_BUCKET`, `FORECAST_S3_ENDPOINT_URL` et les identifiants S3 du bucket d'artefacts. Aucun identifiant ni chemin d'artefact n'est renvoyé par l'API. Le lecteur ne modifie ni le registre ni les émissions ; la production conserve son modèle publié et son circuit existant. Retirer `FORECAST_RESEARCH_PREVIEW` désactive l'aperçu.

Depuis le 14 septembre après-midi, cet aperçu lit le modèle de tendance amortie dans `development/research/damped-trend-v1/emissions/`. Il est entraîné localement et son erreur historique reste supérieure au prix inchangé. Voir [les résultats et limites](RESEARCH.md). La collecte quotidienne de l'hybride conserve son espace séparé.
