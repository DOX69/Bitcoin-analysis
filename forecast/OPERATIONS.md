# Tâches forecast

Le cron d'ingestion existant reste le seul ordonnanceur. Après ingestion et dbt réussis, `raw_ingest.orchestrator.run_forecast` lance un seul processus pour émission, scoring et rapport mensuel. Sans `FORECAST_JOB_CONFIG`, cette étape reste désactivée. Ce lot ne configure aucun service Railway.

Le build de livraison doit installer `uv sync --locked --all-packages --extra forecast`, qui conserve aussi le package d'ingestion sans installer les dépendances de développement. Le cron activé démarre par `uv run --locked --package raw-ingest --no-sync raw-ingest`, depuis la racine du dépôt. Avec `FORECAST_JOB_CONFIG`, son appel dbt ajoute aussi `--no-sync` pour conserver les dépendances forecast préinstallées. Aucun de ces processus ne synchronise l'environnement pendant l'exécution. Le superviseur arrête son worker et ses descendants après 300 secondes ou dépassement de 4 Gio de RSS cumulée. Le worker utilise deux processeurs. La mesure RSS est échantillonnée, pas une réservation matérielle. L'ingestion reste réussie si le forecast échoue. Les journaux distinguent son statut et ne recopient pas les messages d'erreur des clients PostgreSQL/S3.

## Configuration avant activation

Exemple de fichier externe au dépôt, avec des valeurs à renseigner pour l'environnement concerné :

```json
{
  "environment": "development",
  "daily_schema": "development",
  "bronze_schema": "bronze",
  "artifact_bucket": "BUCKET_PRIVE_DEVELOPMENT",
  "cost_record": "/app/config/forecast-cost.json"
}
```

`daily_schema` désigne le schéma dbt réel contenant `obt_fact_day_btc`. Les variables serveur sont `DATABASE_URL`, `FORECAST_S3_ENDPOINT_URL` et les identifiants AWS reconnus par boto3. Development et production utilisent des bases, buckets et accès distincts. Le préfixe des artefacts commence obligatoirement par l'environnement. Aucun secret n'appartient au fichier JSON.

Le relevé externe des coûts doit contenir le mois courant, par exemple :

```json
{"month":"2026-09","measured_usd":0.0,"projected_usd":0.0}
```

Ces zéros illustrent le format. Ils ne sont pas un relevé réel. `projected_usd` représente le coût forecast total prévu du mois, nouveaux travaux compris. Chaque valeur doit être finie, positive ou nulle et strictement inférieure à 5 USD. Absence, mois périmé ou seuil atteint suspendent les nouveaux travaux avant accès aux données. Le relevé doit compter calculs, essais, reprises, stockage, snapshots, copies indépendantes et transferts, avec rapprochement à la facturation Railway. L'application et PostgreSQL restent actifs. Ce mécanisme applique un relevé fourni par l'exploitation ; il ne collecte pas automatiquement la facture et ne constitue pas une mesure du plafond absolu de 10 USD.

## Émission et reprise

L'émission vise le lundi UTC. Une seule tentative supplémentaire est possible le mardi. Le verrou PostgreSQL dédié protège l'ensemble du lot ; une contrainte unique conserve chaque tentative par semaine d'origine et jour. Une tentative interrompue reste consommée, même si son statut reste `started`. Après mardi, la semaine est sautée. Changer le modèle actif ne permet pas une seconde émission de la même semaine.

La série quotidienne doit contenir des semaines ISO consécutives complètes, jusqu'au dimanche précédent. Le loader compare chaque close dbt à la dernière observation bronze connue au démarrage. Il conserve son origine et son horodatage d'ingestion. Aucun trou n'est imputé. Les taux EUR/CHF proviennent de leur dernière observation réellement connue, avec sa date d'origine. Ils restent constants pour les 52 cibles.

Le worker recharge le modèle depuis le bucket et compare le manifeste PostgreSQL au manifeste téléchargé vérifié. Un modèle entraîné après la semaine d'origine est refusé. L'émission porte sa date réelle ; celle du mardi est `delayed`. Aucun argument CLI ne permet de choisir une date passée. `run_batch` accepte une horloge injectée pour les tests, avec provenance explicite `fixture` ou `historical_replay`, distincte de `prospective`.

Avant publication, les observations quotidiennes, leur provenance, les FX et la date de lecture sont sérialisés dans un objet S3 adressé par SHA-256 sous le préfixe du modèle. Le worker relit et vérifie cet objet. La publication échoue si sa sauvegarde échoue. La référence et l'empreinte restent dans l'émission. Les snapshots sont conservés sans purge programmée dans cette version, y compris les objets orphelins d'une tentative échouée. Leur coût doit être comptabilisé. La copie indépendante de ces objets et sa restauration restent à démontrer avant livraison.

## Scoring et rapports

Le scoring peut rattraper les cibles matures tous les jours, même sans émission récente. Un dimanche ne devient mature qu'après sa clôture UTC. Une cotation absente reste non scorée. Chaque score conserve son émission, horizon, révision source, prix observé, provenance et type de preuve. Une correction crée une nouvelle révision ; une relance identique ne crée rien. Les émissions invalidées sont exclues des nouveaux scores.

Les mesures USD comprennent MAE, WIS accepté, couvertures et largeurs 50/80 %, ainsi que MAE/WIS du dernier close connu à l'émission. Ce prix inchangé reste la même référence pour chaque cible. Les observations fictives gardent leur étiquette et ne deviennent pas une confirmation réelle en atteignant une date mature.

Le premier lot réussi du mois archive le rapport du mois précédent pour chaque version. Il contient les 52 horizons, y compris ceux sans observation. Seule la dernière révision de chaque émission/horizon compte ; les cibles doivent appartenir au mois demandé. Le rapport automatique filtre les preuves prospectives et n'active aucun modèle. Une lecture manuelle peut recalculer le rapport après correction :

```powershell
uv run --locked --extra forecast --no-sync python -m forecast.jobs report --config C:\config\forecast.json --version-id VERSION --month 2026-09
```

## Candidats et promotion manuelle

```powershell
uv run --locked --extra forecast --no-sync python -m forecast.jobs quarterly --config C:\config\forecast.json --snapshot C:\data\snapshot.csv --directory C:\data\cycle
uv run --locked --extra forecast --no-sync python -m forecast.jobs register --config C:\config\forecast.json --directory C:\data\cycle\gaussian_random_walk\final --version-id VERSION
uv run --locked --extra forecast --no-sync python -m forecast.jobs check-promotion --report C:\data\decision.json
```

Le cycle trimestriel est limité à Development. Une réservation PostgreSQL par trimestre interdit de recommencer après échec avec un nouveau dossier. Le pipeline conserve les trois recettes acceptées, successives, avec deux processeurs, 4 Gio et 30 minutes chacune. L'enregistrement vérifie le bundle, écrit ses objets immuables puis ajoute `storage_sha256` au seul manifeste PostgreSQL. Il ne modifie pas les octets du manifeste de l'artefact et n'active rien.

Le rapport de décision doit identifier la recette, les 52 lignes `per_horizon` avec `origins`, `mae`, `naive_mae`, `wis`, `coverage_50` et `coverage_80`, son type de preuve `prospective`, la référence `confirmation_review` à la revue de dépendance temporelle, et les contrôles `data_verified` et `resources_verified`. Pour un remplacement, fournir aussi `active_per_horizon` sur les mêmes origines et cibles. Les horizons sans observation, les preuves fictives, les couvertures hors seuils et une recette prix inchangé sont refusés. Les seuils de gain et les garde-fous par horizon sont ceux de [Choisir le modèle, la calibration et les critères de promotion](https://github.com/DOX69/Bitcoin-analysis/issues/80) et [Réexaminer le contrat et les recettes après les nouveaux rapports](https://github.com/DOX69/Bitcoin-analysis/issues/91).

Le contrôle numérique n'authentifie pas un rapport rédigé à la main et ne juge pas la suffisance statistique des blocs. Le propriétaire doit examiner le rapport, ses données appariées et la dépendance temporelle, puis autoriser la version exacte. Sans preuve suffisante, conserver la version active ou rester en Development.

Après cette décision seulement, un opérateur utilise `ForecastStore.activate_version(version_id, verify_artifacts)`. Le callback doit accepter exactement `manifest, prefix`. Il appelle le loader avec ces deux arguments et la semaine d'origine actuelle, puis exécute `emit_forecast` sur des semaines complètes contrôlées par `fresh_weekly`, à la date réelle et avec les FX connus. Cette inférence de contrôle doit réussir avant que le callback retourne. Ne pas passer directement `artifact_loader` ou son résultat au stockage, car le loader attend trois arguments et ne réalise pas cette inférence. `ForecastStore.rollback` exige le même callback de vérification et de calcul. L'activation est atomique et ne réécrit aucune émission. Un rollback vise les prochaines émissions. L'invalidation d'une émission conserve son contenu et ses scores historiques.

## Conservation

La commande `purge --config ...` applique les durées décidées aux seuls fichiers de bundles. Le callback de suppression s'exécute sous le verrou transactionnel de publication. Les versions active et rollback sont protégées ; les artefacts liés aux émissions attendent au moins deux ans après leur dernière cible. Un candidat sans émission doit avoir une date de rejet explicite dans `forecast.maintenance.rejected_at`, puis attendre 90 jours. Aucun autre candidat n'est supprimé. Émissions, scores, rapports et métadonnées de versions restent présents. Les snapshots ne sont pas supprimés par cette commande.

Les migrations `001_storage` puis `002_jobs` s'appliquent avant activation. Le retour arrière de `002_jobs` retire les tables de suivi des jobs, pas le stockage des émissions ; il doit précéder celui de `001_storage`. Une migration descendante retire son historique de suivi et n'est pas une procédure de rollback opérationnel du modèle.

## Vérification locale

```powershell
$env:FORECAST_JOBS_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55432/forecast_jobs_test'
uv run --locked --extra dev --extra forecast pytest forecast/test_jobs.py
```

Les fixtures destructives refusent une base autre que `forecast_jobs_test` ou `bitcoin_test` sur localhost. La suite vérifie les reprises lundi/mardi, l'absence de doublons, les verrous réels PostgreSQL, les cibles immatures et manquantes, les corrections, l'isolation de l'ingestion, les coûts, le roundtrip d'un bundle réel, la sauvegarde préalable du snapshot, les refus de promotion et les références protégées. La preuve des timeouts réels appartient aussi aux tests existants du superviseur dans `test_pipeline.py`. Les appels S3 de ces tests utilisent un bucket en mémoire ; disponibilité, facturation et copie indépendante Railway restent des preuves de validation Development, pas des résultats de ce lot.
