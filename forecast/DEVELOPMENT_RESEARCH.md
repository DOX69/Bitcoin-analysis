# Confirmation prospective sur Railway Development

Le suivi utilise `bitcoin-cron` dans Development, avec PostgreSQL et les deux buckets privés existants. La recette reste en recherche, sans version active ni publication sur le dashboard. La production utilise un autre service et n'est pas ciblée par cette configuration.

## Horaire et entrée

L'objectif est 07:00 Europe/Paris chaque jour. Railway interprète les expressions cron en UTC. Configurer `0 5,6 * * *` et l'entrée `forecast.development_cron` : elle quitte aussitôt si l'heure locale n'est pas 07:00. Cela conserve le même horaire lors des changements été/hiver, sans ordonnanceur permanent ni deuxième traitement quotidien. Railway peut démarrer quelques minutes après l'heure prévue, selon sa [documentation cron](https://docs.railway.com/cron-jobs).

Build : `uv sync --locked --all-packages --extra forecast`.

Démarrage : `uv run --locked --extra forecast --no-sync python -m forecast.development_cron`.

Conserver `restartPolicyType=NEVER`. Utiliser Python 3.11.9 pour correspondre au runtime figé du candidat. Le worker refuse des versions numériques différentes. L'option `--run-now` permet une vérification manuelle du pipeline avec l'horloge réelle ; elle ne modifie jamais les dates des émissions.

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
