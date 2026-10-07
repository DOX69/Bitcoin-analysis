# Validation Railway Development — 9 septembre 2026

Dossier de [Valider la V1 de bout en bout et son coût en Development](https://github.com/DOX69/Bitcoin-analysis/issues/88). La validation logicielle inclut désormais les sauvegardes indépendantes et le worker Railway ; résultats complémentaires ci-dessous.

## Infrastructure et preuve logicielle

PostgreSQL Railway 18.6 est atteint par un tunnel local privé. Deux bases réservées à la validation ont été créées : `forecast_validation_20260909a1` et `forecast_validation_20260909a1_restore`. Deux buckets privés Development, `forecast-v1-artifacts` et `forecast-v1-backups`, séparent les objets actifs et leur copie indépendante. La production n'a pas été modifiée.

Le harnais `python -m forecast.development_validation` entraîne, sauvegarde et recharge un modèle gaussien sur des données synthétiques. Il utilise les vrais jobs, PostgreSQL et S3. Résultats : une émission de 52 horizons, rejeu sans doublon, un score sur cible connue, rejeu sans nouveau score, rollback vérifié. Les dates sont fixes ; ce test ne constitue aucune promotion ni observation prospective.

Le bucket refuse l'écrasement conditionnel avec HTTP 412. Les objets sont relus et leurs empreintes vérifiées. Un dump PostgreSQL est restauré dans la seconde base ; toutes les lignes forecast sont comparées et les modèles/snapshots rechargés depuis la copie locale indépendante, sans le bucket original. Une deuxième copie de huit objets, dump et rapport compris, a ensuite été téléversée dans le bucket de sauvegarde et relue octet pour octet : 195 212 octets.

| Mesure | Résultat |
| --- | ---: |
| Durée du harnais | 13,48 s |
| Restauration et vérification | 3,62 s |
| CPU du processus local | 1,58 s |
| RSS finale locale, sans mesure du pic | 78 196 736 octets |
| Base source | 8 378 047 octets |
| Relations forecast | 311 296 octets |
| Dump compressé | 24 236 octets |
| Objets primaires | 168 579 octets |
| Payloads S3 envoyés par le harnais | 168 588 octets |
| Payloads S3 relus par le harnais | 343 194 octets |

Les compteurs S3 excluent les reprises internes du SDK et les en-têtes HTTP. Le rapport historique nomme encore le champ upload `s3_upload_attempt_bytes` ; le harnais corrigé utilise `s3_upload_payload_bytes`. Les copies ultérieures dans le second bucket ne sont pas comprises dans ces deux compteurs.

Avant les migrations additives de la base Development habituelle, son dump de 1 055 345 octets a été copié et relu dans le bucket indépendant. SHA-256 : `045139670d114cf400691ea6b134fb7f814ed13920f01d9326fc524fb8cb1a50`. Les migrations `001_storage` puis `002_jobs` ont ensuite été appliquées ; aucun modèle n'y a été activé.

Une reconstruction dbt dans la seule base restaurée passe neuf modèles et 87 tests. L'émission reste unique et son payload inchangé. L'historique de démonstration 2024–2025 et la projection synthétique de septembre 2026 sont volontairement distincts.

## API et navigateur Railway

Le web du commit `d718134` a été chargé depuis un export des fichiers suivis. Pour le test, sa connexion a temporairement ciblé la base restaurée. L'API `/api/forecast` renvoie HTTP 200, une émission et 52 horizons ; les 156 valeurs Q25/Q50/Q75 correspondent aux conversions EUR 0,92 et CHF 0,85 figées. Chrome affiche la médiane et la bande sur bureau et mobile 391 × 844, sans débordement horizontal ni erreur console. Les captures `desktop.png` et `mobile.png` restent dans le dossier de preuves privé.

Attention à la source Railway existante : modifier une variable avec redéploiement automatique reconstruit la branche liée `feat/mobile-dashboard-layout`, qui ne contient pas cet endpoint. Le test a corrigé ce cas en utilisant `variable set --skip-deploys`, puis `railway up` sur l'export exact. La connexion initiale est rétablie par le même mécanisme après les vérifications ; aucun modèle de fixture n'est activé dans la base habituelle. Le dépôt distant et la branche source du service ne sont pas modifiés par ce chargement manuel.

## Sauvegardes et coût

La commande native Railway de programmation quotidienne retourne `UNAUTHORIZED: Failed to update the backup schedule`. La liste des plannings reste vide. Une restauration réussie ne prouve donc pas une perte maximale de 24 heures. Aucun contournement de ce refus n'a été tenté.

Sur la période de facturation du 21 août au 21 septembre, le relevé passe de 1,467500 à 1,469250 USD pour tout le projet. Les deltas Development sont 0,000434 USD pour le web, 0,000336 USD pour PostgreSQL et zéro pour le cron. Ce relevé est retardé, inclut l'activité habituelle et ne permet pas d'attribuer un coût marginal définitif au forecast. L'absence de montant de sauvegarde n'est pas une preuve de gratuité.

La métrique Railway PostgreSQL sur une heure atteint 0,0192 CPU au maximum et 0,1155 Go de RAM. Elle couvre le service complet. Les mesures CPU/RSS du harnais sont locales : elles ne mesurent pas un worker Railway.

Les tests vérifient le refus des nouveaux jobs à 5 USD mesurés ou prévus, ainsi que l'absence ou la péremption du relevé. Le hook reste désactivé sans `FORECAST_JOB_CONFIG`. Le budget complet de production doit encore inclure sa sauvegarde quotidienne effective, les rétentions et les ressources du worker cloud. Les bornes de calcul de [INTEGRATION.md](INTEGRATION.md) ne remplacent pas cette mesure.

## Reproduction et limites

Le harnais requiert les dépendances `forecast`, un client PostgreSQL de même version majeure que le serveur, `DATABASE_URL`, `FORECAST_S3_ENDPOINT_URL`, `FORECAST_S3_BUCKET` et les identifiants AWS standards. `FORECAST_PG_DUMP` et `FORECAST_PG_RESTORE` acceptent les chemins des exécutables. Fournir les secrets par l'environnement ; jamais dans le dépôt ou les arguments de commande.

```powershell
uv run --locked --extra forecast python -m forecast.development_validation --database-name forecast_validation_0123456789ab --output C:\Temp\forecast-validation-new
```

Le dossier de sortie et les deux bases doivent être nouveaux. Le harnais conserve ses ressources pour examen ; il ne les supprime pas. Les tests locaux supplémentaires passent neuf cas, dont PostgreSQL réel, avec `FORECAST_VALIDATION_TEST_DATABASE_URL` sur localhost. La revue indépendante et Ruff passent.

Preuves détaillées hors dépôt : `%TEMP%/bitcoin-forecast-development-20260909/`, notamment `run-a1/report.json`, `run-a1/independent-bucket.json`, `migration-evidence.json`, `dbt-restore/summary.json` et les relevés de facturation. Les dumps restent privés.

La livraison production demeure bloquée par l'absence de modèle admissible confirmé prospectivement. La restriction des sauvegardes natives a été résolue par le mécanisme indépendant décrit ci-dessous. Le benchmark décrit dans [VALIDATION.md](VALIDATION.md) ne justifie aucune activation.

## Complément : sauvegardes et worker cloud

Chrome confirme que les sauvegardes natives et le PITR exigent le forfait Pro. Le contrat laisse le mécanisme à l'implémentation : une sauvegarde logique indépendante répond au besoin sans changement de forfait. Le commit `dc7a0c3` ajoute ce mécanisme au cron existant, avec tests et procédure [BACKUP.md](BACKUP.md).

Le test est exécuté dans le conteneur Railway Development, sur deux nouvelles bases isolées. Il valide émission, rejeu, scoring, rollback, suspension aux deux seuils de cinq USD, copie indépendante et restauration des huit tables avec comparaison complète des lignes. Sauvegarde : 2,31 secondes, 370 918 octets comptabilisés ; restauration depuis le second bucket : 0,81 seconde, onze objets vérifiés. Le superviseur mesure 4,92 secondes et un pic RSS de 75 624 448 octets. CPU du worker après imports : 0,42 seconde. Ces chiffres remplacent l'absence antérieure de mesure du worker cloud.

Rapport indépendant : `development/validation-reports/forecast_validation_20260909b1.json`. Copie locale privée : `%TEMP%/bitcoin-forecast-finish-20260909/cloud-report.json`. Les bases initiales, puis `_restore`, restent réservées aux fixtures ; aucun modèle n'est activé dans la base Development habituelle.

Le cron normal est reconfiguré pour 03:00 UTC chaque jour, avec sa même entrée `raw-ingest`, sans second ordonnanceur. La sauvegarde s'exécute aussi après une ingestion défaillante. Les secrets restent dans ses variables serveur ; le fichier de configuration sans secret doit être fourni avec chaque déploiement.

Le scénario [COST.md](COST.md) projette 4,72 USD pour un mois de 31 jours, en comptant tout le web/PostgreSQL Development et une provision de 20 %. Il inclut sauvegardes, copies, essais, transferts et cycle trimestriel complet. Ses allocations sont confrontées à l'inventaire et à une heure de métriques ; la projection doit être recalculée avec la croissance et les moyennes quotidiennes. Ce n'est pas une facture marginale définitive.

Le lancement manuel du cron normal depuis Chrome réussit : neuf modèles dbt et 83 tests hors fixtures passent (`PASS=92`, zéro erreur). La sauvegarde de la base habituelle est créée à 18:25:21 UTC, avec huit tables, aucune version active et onze objets indépendants. Son manifeste relu est `development/backups/20260909T182521361673Z/manifest`. Chrome affiche la prochaine exécution quotidienne à 03:00 UTC. Cela vérifie le mécanisme et sa cadence configurée ; une panne future exige toujours surveillance et reprise pour respecter l'objectif de 24 heures.

La suite Python complète après intégration des sauvegardes passe 193 tests en 242 secondes, avec les bases PostgreSQL locales activées. Les vérifications TypeScript/Jest/lint/build et navigateur décrites plus haut restent celles du code web inchangé.
