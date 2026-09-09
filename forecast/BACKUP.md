# Sauvegarde indépendante du forecast

Le forfait Railway courant ne fournit pas les sauvegardes natives ni le PITR. La décision [Choisir le stockage versionné et l’exécution ponctuelle sur Railway](https://github.com/DOX69/Bitcoin-analysis/issues/81#issuecomment-5562135983) autorise le choix du mécanisme : sauvegarder les données forecast chaque jour et chaque artefact conservé dans une destination indépendante.

## Mécanisme

Le cron d'ingestion existant exécute une sauvegarde même si ingestion, dbt ou forecast échouent. Le sous-processus dispose de cinq minutes et 4 Gio. Son échec est signalé séparément. Il ne relance pas l'ingestion. Les calculs forecast peuvent rester suspendus par le budget ou faute de modèle admissible pendant que les sauvegardes continuent.

La sauvegarde logique utilise PostgreSQL COPY, une transaction cohérente et les migrations versionnées. Elle couvre uniquement le schéma forecast. Les autres schémas du site ne font pas partie de cette sauvegarde. Tables, colonnes, comptes et empreintes sont consignés dans un manifeste. Les objets sont écrits dans le bucket indépendant puis relus ; une clé existante n'est acceptée que si ses octets correspondent. Aucun objet n'est supprimé automatiquement.

Les modèles et snapshots du bucket primaire sont copiés sous leurs clés d'origine dans le second bucket. La restauration lit ce second bucket, vérifie migrations et empreintes avant écriture et refuse une base contenant déjà le schéma forecast. Elle ne remplace jamais silencieusement une base existante.

## Configuration serveur

`FORECAST_BACKUP_CONFIG` désigne un fichier JSON externe au dépôt :

```json
{"environment":"development","artifact_bucket":"BUCKET_ARTEFACTS","backup_bucket":"BUCKET_INDEPENDANT"}
```

L'URL PostgreSQL est fournie par `DATABASE_URL`. La source utilise `FORECAST_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`. La copie indépendante utilise `FORECAST_BACKUP_S3_ENDPOINT_URL`, `FORECAST_BACKUP_ACCESS_KEY_ID`, `FORECAST_BACKUP_SECRET_ACCESS_KEY`, `FORECAST_BACKUP_REGION`. Ces identifiants restent dans les variables privées du service.

Installer `uv sync --locked --all-packages --extra forecast`. Le cron conserve son entrée `uv run --locked --package raw-ingest --no-sync raw-ingest`. Pour un essai manuel de la sauvegarde :

```powershell
uv run --locked --extra forecast --no-sync python -m forecast.backups backup --config C:\config\forecast-backup.json
```

## Exploitation

La cadence quotidienne vise une perte maximale de 24 heures. Une panne du service ou du bucket peut dépasser cet objectif : les journaux de sauvegarde doivent être contrôlés et une sauvegarde dépassant 24 heures doit déclencher une intervention. Aucun forfait ne transforme cet objectif en garantie de disponibilité.

Les copies sont conservées sans purge dans cette V1. Le relevé mensuel doit donc inclure la croissance cumulée, les transferts et les reprises. La conservation durable des données, des copies et des artefacts reste celle du contrat ; aucune règle de suppression à 30 jours n'est introduite.

Le test cloud `python -m forecast.cloud_validation --config ... --database-name forecast_validation_<hex>` crée deux nouvelles bases isolées Development, exécute les vrais jobs avec preuves explicitement synthétiques, sauvegarde et restaure la seconde base, puis compare les lignes. Un superviseur mesure la durée et le pic RSS. Le rapport est copié dans le bucket indépendant. Ce test n'active aucun modèle dans la base habituelle.
