# Collecte prospective LightGBM en Development

`forecast.candidate_cloud` collecte la recette figée `lightgbm_quantile`. `forecast.cloud_research` reste un alias de compatibilité. Le fichier `development-config.json` exige Development ; aucun accès au registre de production ni publication automatique n'est ajouté.

## Exécution

Le cron d'ingestion vise 07:00 Europe/Paris : expression UTC `0 5,6 * * *`, entrée `forecast.development_cron`, sortie immédiate hors de cette heure locale. Conserver `restartPolicyType=NEVER`.

```sh
uv sync --locked --all-packages --extra forecast
uv run --locked --extra forecast --no-sync python -m forecast.development_cron
```

Variables non secrètes :

```text
FORECAST_RESEARCH_CONFIG=/app/forecast/development-config.json
FORECAST_BACKUP_CONFIG=/app/forecast/development-config.json
```

Le runtime du modèle reste Python 3.11.9 avec les versions numériques figées dans le manifeste et `uv.lock`. `railpack.json` ajoute `libgomp1`. Les accès PostgreSQL et S3 restent privés. Development utilise `MISE_PYTHON_GITHUB_ATTESTATIONS=false` pour le téléchargement de cet ancien binaire Python ; la vérification du checksum reste requise. Ne pas changer les versions pour contourner un refus de rechargement.

Après ingestion et dbt, `raw_ingest.orchestrator.run_forecast_research` supervise directement le collecteur : deux CPU, 4 Gio et cinq minutes. Un échec de recherche n'annule pas l'ingestion ; la sauvegarde reste exécutée. La collecte dédiée configurée le 2 octobre utilise `30 6 * * *` et la même fonction :

```sh
uv run --locked --extra forecast --no-sync python -c "import json; from raw_ingest.orchestrator import run_forecast_research; print(json.dumps(run_forecast_research()))"
```

Pour une revue manuelle sans nouvelle émission :

```sh
uv run --locked --extra forecast --no-sync python -m forecast.candidate_cloud --score-only
```

Ces commandes décrivent la configuration à déployer ; un nettoyage local ne met pas à jour les services Railway.

## Artefacts et garde-fous

Les observations proviennent de PostgreSQL et sont vérifiées contre la révision bronze connue. Le modèle est entraîné une fois au bootstrap, puis rechargé avec vérification du manifeste, des versions et des empreintes. Il conserve ses paramètres, variables, cinq quantiles et 52 horizons. Les émissions ne sont créées que lundi UTC, avec reprise mardi ; aucun rattrapage antidaté.

Le namespace actif est `development/research/lightgbm-v1/` :

- `bundle/model/` et reçu de bootstrap : modèle figé et provenance.
- `snapshots/` : observations et révisions adressées par SHA-256.
- `emissions/` : émissions hebdomadaires immuables.
- `reports/` : scores des cibles matures, horizons et blocs temporels.

Le namespace historique `development/research/hybrid-v1/` reste conservé. **Les relevés de budget restent sous `development/research/hybrid-v1/budget/AAAA-MM.json`**, conformément au collecteur actuel. Leur emplacement ne sélectionne pas l'ancienne recette.

Un verrou PostgreSQL empêche deux collectes simultanées. Chaque objet est écrit conditionnellement, relu et copié dans le bucket indépendant avant succès. Une reprise répare la copie sans réécrire l'original. Ne pas effacer les anciens objets S3 ni leurs copies.

Un relevé vérifié du mois courant est exigé avant calcul. Un montant mesuré ou projeté atteignant cinq USD suspend la collecte ; les sauvegardes continuent. Renouveler le relevé chaque mois à partir de la facturation réelle. Le cron ne peut pas inventer ce relevé.

`publishable=false` reste forcé. La confirmation exige 104 origines matures par horizon, deux blocs complets et une décision manuelle ; voir [READINESS.md](READINESS.md). Les scores historiques et les tests ne remplacent pas cette confirmation.

## Dashboard et arrêt

L'ancien aperçu quotidien Ridge, son collecteur et son lecteur S3 sont retirés. Avec `RAILWAY_ENVIRONMENT_NAME=Development`, le drapeau historique `FORECAST_RESEARCH_PREVIEW=true` retourne un forecast absent. Il ne sert pas à afficher LightGBM. Une future publication doit suivre le chemin validé du registre et la décision manuelle.

Pour suspendre la recherche, retirer `FORECAST_RESEARCH_CONFIG`. Conserver les objets, copies et données ; ne pas appliquer de migration descendante. Les recettes et preuves retirées sont récupérables depuis [ARCHIVE.md](ARCHIVE.md).
