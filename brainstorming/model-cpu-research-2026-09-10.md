# Trois recettes à examiner sur CPU

Recherche documentaire du 10 septembre 2026, suivie des essais autorisés de Bolt tiny et Chronos-2-small décrits en fin de document. Aucun modèle activé. Le jeu décrit dans `forecast/VALIDATION.md` contient 581 semaines et la sortie reste de 52 horizons, avec Q10, Q25, Q50, Q75 et Q90 pour les intervalles 80 % et 50 %. Budget matériel à vérifier par processus : deux CPU, 4 Gio, 30 minutes par recette, folds et entraînement final compris.

Je retiens Chronos-Bolt tiny, NHITS compact et une marche aléatoire Student sans dérive. Les deux premiers cherchent un gain prédictif ; le troisième sert de contrôle probabiliste. Sa médiane est le dernier prix et ne peut donc satisfaire un gain MAE strict face à cette même référence.

## Recettes proposées

### 1. Chronos-Bolt tiny sur le logarithme des prix

Le checkpoint `amazon/chronos-bolt-tiny` compte environ 9 millions de paramètres et son fichier de poids pèse 34,6 Mo. Sa configuration accepte 2 048 observations et prédit directement 64 pas : les 581 semaines et 52 horizons entrent dans ces limites. Bolt small compte 48 millions de paramètres et 191 Mo ; ce serait un remplacement ultérieur de tiny, pas une quatrième recette dans ce cycle. Sources : [famille Chronos](https://github.com/amazon-science/chronos-forecasting), [poids tiny](https://huggingface.co/amazon/chronos-bolt-tiny/tree/main), [configuration tiny](https://huggingface.co/amazon/chronos-bolt-tiny/blob/main/config.json), [poids small](https://huggingface.co/amazon/chronos-bolt-small/tree/main).

Interface documentée à adapter dans un environnement isolé : `ChronosBoltPipeline.from_pretrained("amazon/chronos-bolt-tiny", device_map="cpu", torch_dtype=torch.float32)`, puis `predict_quantiles(inputs, prediction_length=52, quantile_levels=[0.1,0.25,0.5,0.75,0.9])`. Utiliser une seule série par appel et `torch.set_num_threads(2)`. Fournir `log(close)` et exponentier chaque quantile obtenu. Q25/Q75 sont interpolés entre déciles, Q50 est natif. Le deuxième retour nommé `mean` est en réalité la médiane dans cette implémentation. Ne pas demander Q05/Q95 : le code borne ces niveaux aux extrémités entraînées Q10/Q90. Source : [implémentation Bolt](https://github.com/amazon-science/chronos-forecasting/blob/main/src/chronos/chronos_bolt.py).

Pas de réentraînement local initial. Les tailles de poids ne mesurent pas la RAM totale : PyTorch, buffers et chargement s'ajoutent. La faisabilité sous 4 Gio semble plausible pour tiny, mais aucune durée sur notre CPU n'est prouvée. Fixer la révision du checkpoint, conserver ses empreintes et rejouer hors réseau. Vérifier les périodes et données de préentraînement avant de qualifier un backtest historique de réellement hors échantillon.

### 2. NHITS compact, quantiles directs

Proposition fixe : `NHITS(h=52, input_size=104, n_blocks=[1,1,1], mlp_units=[[64,64]]*3, n_pool_kernel_size=[2,2,1], n_freq_downsample=[4,2,1], windows_batch_size=32, inference_windows_batch_size=32, batch_size=1, max_steps=300, random_seed=42, scaler_type="standard", accelerator="cpu", devices=1, logger=False, enable_checkpointing=False)`. Entraîner sur `log(close)`, puis exponentier. Ces petites dimensions sont notre choix de départ, pas une configuration validée sur Bitcoin. Paramètres et transfert vers le Trainer sont documentés par [Nixtla NHITS](https://nixtlaverse.nixtla.io/neuralforecast/models.nhits.html).

Ajouter `loss=MQLoss(quantiles=[0.1,0.25,0.5,0.75,0.9])`. Cette perte estime directement les niveaux demandés. Une seule configuration, sans AutoNHITS ni recherche Ray. Réserver dans chaque fold des données d'entraînement antérieures pour validation et calibration. Contrôler les croisements et figer toute correction avant les tests externes. Source : [MQLoss](https://nixtlaverse.nixtla.io/neuralforecast/losses.pytorch.html).

Aucun checkpoint distant requis. Les paquets `neuralforecast` et PyTorch restent à télécharger. Les petites couches réduisent les paramètres, mais le pic mémoire et les 300 étapes doivent être chronométrés ; aucune promesse de durée ne découle de la documentation. Avec une seule série et peu d'origines indépendantes, le surapprentissage est un risque concret.

### 3. Marche Student sans dérive, contrôle probabiliste

Recette proposée : ajuster l'échelle d'une Student à cinq degrés de liberté sur les seuls rendements logarithmiques hebdomadaires du train, avec `scipy.stats.t.fit(returns, fdf=5, floc=0)`. Simuler 10 000 trajectoires de 52 innovations indépendantes, graine fixe, puis sommer les innovations et exponentier depuis le dernier close. Une matrice float64 de cette taille représente 4,16 Mo, hors copies et runtime. Aucun poids externe. SciPy documente `fit`, `rvs` et les paramètres `df`, `loc`, `scale` ; les cinq degrés et le nombre de trajectoires sont nos choix. Source : [Student SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html).

Ne pas remplacer la simulation par une Student multipliée par racine de l'horizon : une somme d'innovations Student n'a généralement pas cette distribution. Des innovations antithétiques rendent la symétrie explicite et Q50 reste exactement le dernier close. Une éventuelle correction d'échelle utilise uniquement une validation interne chronologique. Aucune indépendance temporelle des vrais rendements ni supériorité du modèle n'est présumée.

## TimesFM et propositions antérieures

TimesFM 2.5 reste une réserve, exclue des trois essais initiaux. Le checkpoint pèse 925 Mo avant runtime ; son modèle de 200 millions de paramètres dispose d'une tête quantile supplémentaire. L'API propose `TimesFM_2p5_200M_torch`, `ForecastConfig(max_context=1024, max_horizon=64, per_core_batch_size=1, normalize_inputs=True, use_continuous_quantile_head=True)` et `forecast(horizon=52, inputs=[...])`. La sortie standard décrit les déciles ; ne pas déduire un support Q25/Q75 natif du seul mot « continuous ». Sources : [checkpoint](https://huggingface.co/google/timesfm-2.5-200m-pytorch/tree/main), [API 2.5](https://github.com/google-research/timesfm/blob/master/timesfm-forecasting/references/api_reference.md).

Le rapport `rapport_challengers_forecast_bitcoin_12m.md` propose 365 jours et Chronos-2-small. Ce n'est pas le protocole hebdomadaire V1. Chronos-2-small existe bien sous `autogluon/chronos-2-small`, environ 28 millions de paramètres ; il ne faut pas confondre ce nom avec Bolt small. Les gains attendus sur Bitcoin et la vitesse CPU restent des hypothèses. Le dépôt TimesFM présente maintenant 3.0 ; conserver explicitement 2.5 évite un changement silencieux de modèle. Source : [dépôt TimesFM actuel](https://github.com/google-research/timesfm).

## Préparation et critères de poursuite

Les dépendances Chronos, NeuralForecast et TimesFM ne figurent pas dans le `pyproject.toml` du projet. Préparer un environnement de recherche distinct, résoudre et verrouiller les versions compatibles. Utiliser PyTorch CPU depuis l'index officiel, puis `chronos-forecasting` et `neuralforecast` ; ne pas installer CUDA, torchvision, torchaudio ou toutes les familles TimesFM pour ces essais. Le téléchargement des roues Python s'ajoute aux poids indiqués et doit être inventorié. Source : [installation CPU PyTorch](https://docs.pytorch.org/get-started/locally/).

Mesurer d'abord un fold sous superviseur, puis poursuivre seulement si le cycle complet reste dans ses limites. Conserver les mêmes origines, cibles et métriques que les recettes existantes. Ni interpolation, ni calibration, ni hyperparamètre ne se choisit après examen des folds externes. Rapporter WIS, MAE, couvertures par horizon, durée, pic RSS, octets téléchargés et reproductibilité après rechargement. Une réussite rétrospective ouvre une évaluation prospective ; elle ne constitue pas une promotion.

## Essai Bolt tiny exécuté

Le runner `forecast/chronos_research.py` a évalué les origines 348 à 411 puis 464 à 528 incluses du snapshot vérifié de 581 semaines. Son manifeste a figé avant l'inférence la révision `a0e552de83495b5c28c14c71c374f3e33280b340`, les empreintes du snapshot et du code, les dépendances et les paramètres ci-dessus. Environnement Python 3.12 isolé dans le dossier temporaire ; `chronos-forecasting==2.3.2`, `torch==2.14.0+cpu`, `transformers==5.17.0`. Le lock du projet reste inchangé.

| Mesure sur 129 origines | Résultat |
| --- | ---: |
| Durée du processus supervisé, imports et téléchargement inclus | 35,65 s |
| Pic RSS cumulé mesuré par le superviseur | 458 129 408 octets |
| Chargement initial du modèle | 14,83 s |
| CPU du worker | 18,16 s |
| Fichiers du cache, hors dépendances Python et protocole réseau | 34 623 667 octets |
| MAE USD | 24 559,13 |
| MAE / MAE prix inchangé | 1,5200 |
| WIS | 20 696,32 |
| WIS / WIS prix inchangé | 1,2809 |
| Couverture 50 % | 67,50 % |
| Couverture 80 % | 94,02 % |

L'affinité du worker était limitée à deux CPU. Les deux folds passent matériellement, mais les métriques moyennes échouent aux critères existants. Les intervalles couvrent trop largement et la médiane fait moins bien que le dernier prix. Aucun calibrage ajouté après ce constat. Un rechargement sans réseau reproduit exactement les 52 horizons de la première origine. Les quatre tests vérifient causalité, validité des données, conversion et refus des quantiles croisés ; Ruff passe.

Preuves privées conservées dans `%TEMP%/bitcoin-chronos-research-20260910-a1/` : `manifest.json`, `manifest.sha256`, `predictions.json`, `report.json`, `resources.json`, `worker.log` et le checkpoint. Toutes les prédictions et observations sont exportées ; le score réutilise `forecast.benchmark._score`. Cet essai rétrospectif ne démontre pas l'absence de données Bitcoin dans le préentraînement. Il ne justifie aucune promotion ni modification des critères.

## Essai Chronos-2-small exécuté

Ce second essai reprend le modèle explicitement proposé dans le rapport antérieur, `autogluon/chronos-2-small`, révision figée `ddec01313e50b6bc58ebaa92ede81bc24a3d9f9a`. Même transformation logarithmique, mêmes 129 origines, 52 horizons et cinq quantiles ; aucune calibration. Le runner utilise `BaseChronosPipeline`, `batch_size=1` et `context_length=2048`. L'API Chronos-2 retourne une liste de tenseurs avec une dimension de variable supplémentaire. Q25/Q75 sont interpolés par la bibliothèque. Sources vérifiées : [configuration](https://huggingface.co/autogluon/chronos-2-small/blob/main/config.json) et [pipeline Chronos-2](https://github.com/amazon-science/chronos-forecasting/blob/main/src/chronos/chronos2/pipeline.py).

| Mesure | Résultat |
| --- | ---: |
| Durée supervisée | 19,70 s |
| Pic RSS cumulé | 509 685 760 octets |
| CPU du worker | 15,56 s |
| Fichiers du cache | 111 750 212 octets |
| MAE USD | 18 257,50 |
| MAE / MAE prix inchangé | 1,1300 |
| WIS | 14 292,46 |
| WIS / WIS prix inchangé | 0,8846 |
| Couverture 50 % | 64,25 % |
| Couverture 80 % | 93,66 % |

Le WIS s'améliore de 11,54 % face à la référence, mais la MAE augmente de 13 %. Les couvertures moyennes dépassent les seuils ; seuls 13 horizons sur 52 satisfont la plage 50 % et 14 la plage 80 %. Cette recette échoue donc également aux critères. Le rechargement hors réseau reproduit exactement la première origine. Cinq tests de causalité, conversion et options passent. Le modèle n'est pas activé.

Preuves dans `%TEMP%/bitcoin-chronos2-research-20260910-a1/`, avec manifeste préalable, code archivé, prédictions complètes, métriques par fold et horizon, mesures et checkpoint. Le source du premier essai Bolt reste archivé dans son propre dossier. Les deux essais sont successifs ; leur différence de durée inclut chargement réseau et caches, elle ne prouve pas que Chronos-2 est plus rapide. La [fiche du modèle](https://huggingface.co/autogluon/chronos-2-small) cite des corpus de préentraînement, mais leur absence de chevauchement avec Bitcoin n'a pas été établie ici.
