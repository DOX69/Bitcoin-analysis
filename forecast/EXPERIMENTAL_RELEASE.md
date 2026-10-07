# Publication expérimentale à six mois

Décision produit du 7 octobre 2026 : afficher en production les prévisions réelles LightGBM comme expérimentales. Cette décision ne valide pas leur qualité prédictive et ne promeut aucun modèle dans `forecast.publication`.

Le modèle numérique reste figé. Le collecteur Development vérifie son manifeste, ses fichiers, les snapshots, le rejeu des émissions et leur copie indépendante. Le cron d'ingestion production utilise le hook optionnel `FORECAST_EXPERIMENTAL_PUBLISH_CONFIG` pour relire ces preuves et publier une vue des six mois calendaires suivant chaque émission, uniquement pour l'empreinte explicitement autorisée dans `FORECAST_EXPERIMENTAL_MODEL_SHA256`. Il ne réentraîne rien et ne crée aucune émission supplémentaire. PostgreSQL reste privé ; aucun proxy TCP n'est ajouté.

Les valeurs hebdomadaires Q10, Q25, Q50, Q75 et Q90 proviennent du modèle. La médiane et les bandes nominales 50 % et 80 % restent accompagnées de la mention « Qualité prédictive non confirmée ». Les FX sont les dernières observations réellement connues à l'heure de l'émission ; ils restent constants sur toute sa courbe. Aucun point n'est inventé à la date exacte des six mois si ce jour n'est pas un dimanche.

## Mise en service

1. Vérifier le benchmark historique ciblé, les tests, l'empreinte du modèle et l'émission réelle du 5 octobre. Les historiques consultés restent exploratoires.
2. Appliquer `migrations/003_experimental.up.sql` à PostgreSQL production. Ce schéma séparé ne modifie ni dbt ni le registre validé.
3. Configurer deux buckets privés propres à la production. Le producteur copie le bundle numérique, chaque émission source, son snapshot et sa vue publique, relit leurs empreintes et vérifie la copie indépendante avant l'insertion PostgreSQL.
4. Fournir au seul cron production les variables serveur `FORECAST_EXPERIMENTAL_MODEL_SHA256`, `FORECAST_EXPERIMENTAL_PUBLISH_CONFIG=/app/forecast/experimental-production-config.json` et, pour `SOURCE`, `SOURCE_BACKUP`, `ARTIFACT` et `BACKUP`, les suffixes `ENDPOINT`, `BUCKET`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY` après `FORECAST_EXPERIMENTAL_`. Les sources pointent vers les deux buckets Development ; les destinations vers les deux buckets production. Le cron conserve son accès PostgreSQL privé existant. Installer l'extra forecast au build et conserver `--no-sync` au démarrage.
5. Archiver un budget vérifié du mois courant dans `development/experimental/lightgbm-v1/budget/AAAA-MM.json`. Le seuil existant de cinq USD reste appliqué ; un nouveau mois sans relevé suspend la publication. Les coûts comprennent les copies, le stockage et les transferts.
6. Dans le web production, définir `FORECAST_EXPERIMENTAL_ENABLED=true` et la même empreinte de modèle. Déployer le web et le cron depuis le commit fusionné, puis vérifier API, desktop, mobile, devises, bande 80 %, désactivation et absence de doublons. Pour la première publication du jour, exécuter le même worker borné, puis restaurer le démarrage ingestion et son calendrier existant. Le quotidien ne recharge le modèle que si une nouvelle émission est disponible.

Le dashboard active la courbe expérimentale par défaut, avec son statut et sa date réelle. L'API ne fournit ni secrets, ni chemins S3, ni manifeste de recherche. Une émission de plus de huit jours est signalée comme ancienne. Les filtres historiques excluent les prévisions non connues à la date demandée.

Budget du 7 octobre : relevé projet courant de 2,8383 USD, période du 21 septembre au 21 octobre (borne supérieure des dépenses d'octobre déjà connues, facturation retardée). La projection conditionnelle de 4,92 USD conserve son allocation de 31 workers forecast de cinq minutes à deux CPU et 4 Gio : désormais affectée au producteur production, elle ne finance aucun entraînement quotidien Development. Le collecteur figé dispose déjà de sa provision distincte de 0,20 USD. Les copies production restent dans l'enveloppe existante de 2 Go de buckets et 2 Go de sortie réseau. Cette réaffectation ne garantit pas la facture et doit être revue chaque mois.

## Arrêt et restauration

Retirer `FORECAST_EXPERIMENTAL_PUBLISH_CONFIG` suspend les nouvelles publications sans arrêter la collecte ni l'ingestion. Mettre `FORECAST_EXPERIMENTAL_ENABLED=false` retire l'affichage expérimental. Ne supprimer ni les émissions, ni les modèles, ni les objets privés.

La restauration se fait depuis les objets `production/experimental/lightgbm-v1/` du bucket indépendant : vérifier les empreintes du manifeste et des fichiers, rejouer le snapshot, puis comparer les cinq quantiles de l'émission source. Pour restaurer l'index public dans une base isolée, appliquer la migration et réinsérer chaque `public.json` vérifié avec les empreintes de son source et de son contenu. Ne pas écraser une origine déjà publiée.

La confirmation prospective et les conditions de [READINESS.md](READINESS.md) restent requises pour présenter un modèle comme validé. [DEVELOPMENT_RESEARCH.md](DEVELOPMENT_RESEARCH.md) décrit le scoring des échéances au fil de leur arrivée.

## Contrôle historique du 7 octobre

Snapshot réel de 585 semaines, modèle des folds rechargé et inchangé. Deux fenêtres chronologiques, chacune avec 91 origines dont les 26 cibles sont matures. Les modèles des folds n'utilisent aucun label au-delà de leur coupure d'apprentissage. Le modèle final utilisé par la collecte reste distinct de ces modèles de mesure.

Sur les 26 horizons et les deux fenêtres, la MAE moyenne LightGBM vaut 17 795,96 USD, contre 12 128,75 USD pour le dernier close connu. WIS : 12 049,83 USD. Couvertures moyennes nominales 50 % et 80 % : 34,26 % et 73,10 %. À 26 semaines, les MAE sont respectivement 15 405,68 et 36 935,64 USD, contre 13 549,82 et 24 145,76 USD pour la référence. Le contrôle ne valide donc pas la qualité prédictive ; la publication conserve son statut expérimental.

Preuves locales hors Git : `C:/Users/ggrft/AppData/Local/Temp/bitcoin-forecast-six-month-20261007/`, avec `six-month-protocol.json`, `six-month-targeted-review.json`, `snapshot.csv` et les modèles reproductibles sous `benchmark.run/`. Aucun résultat de ce dossier ne constitue un holdout final vierge.
