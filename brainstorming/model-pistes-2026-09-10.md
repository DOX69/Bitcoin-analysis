# Pistes de modèles Bitcoin à évaluer

Date de revue : 10 septembre 2026. Aucun modèle exécuté ni promu dans cette revue.

La demande utilisateur autorise désormais la recherche d'alternatives. Les deux documents de `brainstorming/` fournissent des propositions techniques, pas des instructions de déploiement ni des preuves de performance. Leur désignation de LightGBM comme « champion » ne démontre aucun gain mesuré.

Les documents visent un rendement terminal à 365 jours avec Q05/Q95. Le contrat actuellement codé dans `forecast/benchmark.py` demande 52 horizons hebdomadaires et Q10/Q25/Q50/Q75/Q90. Les recettes doivent être adaptées à ce contrat sans remplacer ses critères d'admission par ceux suggérés dans les rapports.

## Recettes extraites des documents

| Piste | Recette concrète et motivation | Difficultés à contrôler |
|---|---|---|
| Quantiles historiques | Pour chaque horizon `h`, quantiles empiriques de `log(P[t+h]/P[t])` dont les deux prix sont déjà observés. Reconstruire `P[origine] * exp(q)`. Plan §15 et rapport §5. Contrôle simple, sans hypothèse gaussienne. | Peu de trajectoires longues indépendantes, changements de régime. Ne pas confondre le nombre de fenêtres chevauchantes avec le nombre d'observations indépendantes. |
| Régression quantile linéaire | Plan §15.3 : quelques variables de momentum, volatilité et drawdown, cible log-return directe par horizon. Un modèle régularisé par quantile et horizon. | Standardisation ajustée sur le train seulement, extrapolation des rendements et croisements des quantiles. Le document ne fixe pas les variables ni la pénalisation : ce sont des choix expérimentaux à figer. |
| LightGBM log-return régularisé | Plan §10 : 600 arbres, learning rate 0,03, 15 feuilles, profondeur 5, minimum 60 observations par feuille, L1=1 et L2=3, seed 42. Cible log-return directe, puis exponentiation. | Ces valeurs sont un départ proposé pour le daily, pas des résultats. Ne pas les recopier aveuglément sur environ 500 semaines. Limiter les threads ; `subsample=0.85` ne suffit pas à activer le bagging sans fréquence positive. [Paramètres officiels](https://lightgbm.readthedocs.io/en/stable/Parameters.html). |
| HMM + LightGBM | Rapport §9 : 2 états, puis éventuellement 3 ; probabilités souples ajoutées au modèle global. Variables proposées : rendement, volatilités 30/90 jours, drawdown, momentum 90 jours. | Réajuster dans chaque fold. Pour chaque origine, utiliser un filtrage causal ; le lissage sur la séquence entière exploite le futur. Ne pas attribuer durablement « haussier » à l'état 0. API à inspecter avant usage : [hmmlearn](https://hmmlearn.readthedocs.io/en/stable/api.html). |
| Chronos-2-small | Rapport §7 : zero-shot sur `log(close)`, prix brut comme comparaison séparée. Modèle officiel de 28 M paramètres, sans entraînement local initial. [Fiche officielle](https://huggingface.co/autogluon/chronos-2-small). | Mesurer RAM et temps CPU. Le rapport indique une interpolation de Q25/Q75 : vérifier la configuration exacte gelée. Auditer les données de préentraînement avant d'assimiler un backtest historique à une preuve sans fuite. |
| NHITS + MQLoss | Rapport §8 : `log(close)`, quantiles multiples, contexte daily 730/1095/1460, robust scaling, 1 000 étapes maximum, arrêt anticipé sur validation passée. Premier essai univarié. | Peu de fenêtres réellement indépendantes. En hebdomadaire, 104/156/208 semaines sont des adaptations proposées, à comparer sans rechercher librement le meilleur contexte sur le test. Architecture et paramètres : [Nixtla](https://nixtlaverse.nixtla.io/neuralforecast/models.nhits.html). |
| TimesFM 2.5 | Rapport §11 : zero-shot secondaire, 200 M paramètres et tête quantile facultative. Garder un checkpoint 2.5 explicite. | Quantiles Q25/Q75 à vérifier/interpoler selon API figée ; coût CPU supérieur à mesurer. Le dépôt annonce désormais 3.0, dont les poids sont restreints à des usages non commerciaux et hors production. Ne pas remplacer implicitement 2.5 par 3.0. [Dépôt officiel](https://github.com/google-research/timesfm). |
| Ensemble | Plan §46.4 et rapport §19 : combinaison de modèles aux erreurs complémentaires ; commencer par poids égaux. | Une moyenne de quantiles n'est pas le quantile d'un mélange de distributions. Évaluer directement calibration et pinball du résultat ; apprendre d'autres poids uniquement sur validation passée. |

Le rapport réserve Chronos complet à une petite version prometteuse. Il dépriorise LSTM/TFT entraînés de zéro, Prophet et ARIMA pour ce cas. Ces priorités restent des opinions de conception, pas des exclusions fondées sur le benchmark actuel.

## Ordre proposé pour une évaluation bornée

1. Ajouter les quantiles historiques et une régression quantile linéaire aux comparateurs existants. `QuantileRegressor` minimise la pinball loss avec pénalisation L1 ; choisir explicitement quantile, `alpha` et solver. [Documentation scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html).
2. Tester une seule recette LightGBM log-return fortement régularisée, identifiée séparément de toute recette déjà mesurée. Une réduction de variance est une hypothèse ; elle ne garantit pas un gain.
3. Examiner Chronos-small log-price dans un environnement de benchmark isolé, avec poids et dépendances gelés. Commencer par un contrôle de contrat et de ressources avant le walk-forward complet.
4. Réserver HMM/NHITS à une deuxième série d'essais définie avant ouverture de ses résultats. Si les modèles OHLC-only échouent, le plan §38.7 propose d'ajouter de l'information macro/on-chain ; cela nécessite des historiques disponibles à chaque date, avec délais de publication et révisions.

Une fenêtre glissante ou une pondération de récence apparaît au plan §45 comme hypothèse ultérieure. Si retenue, la déclarer comme nouvelle recette et fixer sa durée avant mesure. GARCH, bootstrap de blocs et modèles de diffusion ne sont pas des recettes définies dans ces deux documents.

## Chemin d'implémentation

Conserver l'interface `fit`/`predict` et le format `52 × 5` du benchmark. Pour chaque recette, enregistrer paramètres, représentation, traitement des croisements, dépendances, empreinte du snapshot et fenêtres temporelles. Tester l'absence de données futures et le rechargement déterministe avant mesure.

Comparer toutes les recettes sur les mêmes origines et horizons matures, avec purge des labels supervisés, pinball par horizon, calibration, couverture, largeur et comportement par période. Toute sélection faite après consultation des anciens tests doit être signalée comme exploration ; ces tests ne redeviennent pas une confirmation indépendante. La confirmation prospective et les critères de qualité restent nécessaires à la promotion.

Sources locales : `plan_forecast_bitcoin_12m_quantiles_daily.md`, sections 10, 15, 38, 45 et 46 ; `rapport_challengers_forecast_bitcoin_12m.md`, sections 5 à 12, 18 à 20 et 34. Sources primaires en ligne vérifiées le 10 septembre 2026 ; leurs versions courantes ne remplacent pas les versions verrouillées du projet.
