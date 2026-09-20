# Pipeline du forecast Bitcoin V1

Le cycle compare les deux recettes candidates acceptées dans [Réexaminer le contrat et les recettes après les nouveaux rapports](https://github.com/DOX69/Bitcoin-analysis/issues/91#issuecomment-5575374789).

- `gaussian_random_walk` conserve la dérive et l'écart-type de population des rendements log d'apprentissage.
- `lightgbm_quantile` apprend `log(P[t+h]/P[t])`, puis reconstruit `P[t] * exp(q)`. Les variables et paramètres acceptés restent inchangés. Les cinq quantiles sont réordonnés.

La référence `last_close_holdout_reference` n'est pas une recette ni un modèle enregistré. Elle est calculée séparément sur les origines hors échantillon : pour chaque origine de test, elle répète le dernier close connu et mesure ensuite les cibles arrivées à maturité. Le suivi prospectif applique la même règle au `origin_close` de l'émission et aux observations réelles reçues après l'émission.

Aucune recette n'applique de recalibration. L'ancien `ResidualQuantileCalibrator` reste disponible pour comprendre les résultats exploratoires précédents ; le pipeline ne l'appelle pas.

## Contrat et fenêtres figés

Le CSV contient `date,close`. `date` désigne le lundi UTC de la semaine ISO complète dont `close` est le prix BTC/USD du dimanche. Le fetch quotidien refuse doublons, trous, valeurs invalides et semaines incomplètes. Un CSV hebdomadaire importé doit provenir de cette agrégation ou d'une source vérifiée équivalente. Sa structure ne prouve pas à elle seule la présence des sept observations sources.

Le manifeste précède tout entraînement. Il archive l'empreinte du snapshot, `uv.lock`, les versions Python et numériques, les paramètres LightGBM complets par quantile, l'ordre des variables, une copie du code avec ses empreintes, les limites et la tolérance de rechargement.

Pour `n` semaines, deux coupures expansives utilisent `floor(0.6*n)` et `floor(0.8*n)` observations d'apprentissage. Dans chaque période suivante, seules les origines dont les 52 cibles arrivent avant la fin de période sont évaluées. Les bornes d'indices sont inclusives au début et exclusives à la fin. Les labels LightGBM vérifient `origine+h < train_end`. Les variables d'inférence n'utilisent que les closes jusqu'à l'origine. La référence holdout n'entre jamais dans `recipes` et ne peut pas être entraînée, chargée ou publiée.

Après les deux évaluations, chaque recette est entraînée sur le snapshot complet. Cet artefact final reste candidat. Les scores appartiennent aux modèles des folds, pas à une évaluation indépendante de ce modèle final.

Les rapports conservent les scores pour les 52 horizons, chaque période, les prédictions appariées et les blocs temporels contigus de `h` origines pour l'horizon `h`. Ils signalent les derniers blocs incomplets. Ces blocs ne prouvent pas l'indépendance des erreurs. Le WIS applique exactement `(0.5*erreur_mediane + 0.25*IS_0.5 + 0.10*IS_0.2)/2.5`. Les origines ont le même poids par horizon, puis les 52 horizons le même poids global.

## Exécution locale

```powershell
uv run --locked --extra benchmark python -m forecast.benchmark snapshot `
  --base-url https://bitcoin-web-development.up.railway.app `
  --start-date 2015-07-20 --end-date 2026-09-06 `
  --output "$env:TEMP\forecast-snapshot.csv"

uv run --locked --extra benchmark python -m forecast.pipeline prepare `
  --snapshot "$env:TEMP\forecast-snapshot.csv" `
  --directory "$env:TEMP\forecast-cycle"

uv run --locked --extra benchmark python -m forecast.pipeline run `
  --directory "$env:TEMP\forecast-cycle"
```

La commande historique `forecast.benchmark benchmark --snapshot ... --output ...json` prépare et exécute le même pipeline. Elle conserve ses artefacts dans le dossier voisin `...run`.

Chaque recette s'exécute dans son propre processus, successivement. L'affinité limite le worker à deux processeurs et les bibliothèques numériques à deux threads. Le superviseur mesure la somme des RSS du worker et de ses descendants toutes les 25 ms et arrête son worker au dépassement de 4 Gio ou 30 minutes, entraînements des folds, prédictions, sérialisation et entraînement final compris. Ce contrôle échantillonné n'est pas une réservation matérielle de mémoire. Les pages partagées peuvent être comptées plusieurs fois, ce qui rend le seuil conservateur. Un dépassement ou un échec interrompt le cycle, sans nouvel essai automatique. Un dossier déjà commencé est refusé.

Un verrou local au dépôt empêche deux cycles simultanés, même avec des dossiers de sortie différents. Si le superviseur est tué brutalement, le verrou reste en place. Vérifier que son PID n'existe plus avant de supprimer ce seul verrou et de décider explicitement du prochain cycle. Ne jamais supprimer automatiquement un verrou présumé ancien.

## Artefacts et inférence

Chaque fold et le modèle final disposent d'un dossier avec `manifest.json` et un état JSON ou 260 fichiers LightGBM natifs. Aucun pickle. Le manifeste indique `recalibration: null`, les variables, les versions et l'empreinte de chaque fichier. Le chargement vérifie le contrat, les versions et les empreintes avant de lire les modèles. `inventory.json` donne les empreintes et tailles de tous les fichiers du cycle. Le stockage privé et la vérification de ces références côté serveur relèvent du lot stockage.

Le rechargement est comparé aux prévisions en mémoire pour toutes les origines de chaque fold et la dernière origine du modèle final. Tolérance fixée avant mesure, `rtol=1e-10`, `atol=1e-8` USD, sur les 52 fois 5 valeurs. Les quantiles doivent être finis, strictement positifs et ordonnés.

```python
from pathlib import Path
from forecast.artifacts import load_model, emit_forecast
from forecast.benchmark import _read_weekly_csv

candidate = load_model(Path("cycle/gaussian_random_walk/final"))
weekly = _read_weekly_csv(Path("snapshot.csv"))
forecast = emit_forecast(candidate, weekly, "2026-09-07", {
    "EUR": {"date": "2026-09-07", "rate": 0.9},
    "CHF": {"date": "2026-09-07", "rate": 0.8},
})
```

Les taux ci-dessus illustrent le contrat. L'appelant fournit le dernier taux connu à l'émission ; le pipeline refuse une date FX future et un taux invalide. Le même taux multiplie tous les quantiles et horizons. Les dates cibles sont les 52 dimanches suivant le dernier dimanche observé. Les fichiers `preview.json` sont des rejeux historiques marqués comme tels, jamais des émissions publiées ou antidatées.

## Vérification et portée

```powershell
uv run --locked --extra dev --extra benchmark pytest forecast
```

La CI exécute cette suite séparément de l'ingestion. Elle couvre recettes, maturité des labels à 52 semaines, absence de recalibration, fenêtres, dates/FX, empreintes, rechargement LightGBM, limites de ressources et cycle complet sur fixture synthétique.

Le rapport signale les horizons qui échouent aux garde-fous historiques de première version. Il conserve `publishable: false` pour toutes les recettes. Une confirmation prospective et une décision manuelle restent nécessaires. Les comparaisons à une future version active appartiennent à la validation de promotion. Aucune publication ni dépense Railway n'est déclenchée ici.

La [recherche complémentaire de modèles](RESEARCH.md) documente les nouvelles recettes demandées après ce premier cycle, leurs résultats et leurs limites. Ses runners restent séparés du registre de production.
