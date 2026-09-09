# Contexte métier

## Prévision Bitcoin V1

- **Forecast V1** : prévision probabiliste du prix du Bitcoin jusqu'à 12 mois, avec des émissions hebdomadaires et une validation des échéances arrivées à maturité.
- **Benchmark** : comparaison contrôlée de candidats sur les mêmes données, horizons et devises. Il mesure la qualité des prévisions, la mémoire, la durée, la taille des artefacts et le coût marginal.
- **Candidat** : modèle ou configuration évalué pendant un benchmark, mais pas encore promu.
- **Promotion** : décision manuelle de rendre un candidat validé disponible pour l'inférence en Production.
- **Calibrateur du forecast** : correction versionnée des quantiles d'un modèle, estimée sur des observations réservées à la calibration. Sa révision ne modifie pas les émissions antérieures.
- **Résultat exploratoire** : résultat déjà examiné pour choisir une recette ou ses paramètres. Sa réutilisation ne constitue pas une confirmation indépendante.
- **Confirmation prospective** : évaluation d'une recette figée sur des observations futures, à mesure que les cibles des prévisions émises arrivent à maturité.
- **Job forecast** : exécution ponctuelle qui entraîne, évalue ou produit les artefacts nécessaires au forecast. Il ne doit pas arrêter les services existants.

## Contrat de données du forecast

- **Cible hebdomadaire** : prix de clôture BTC/USD d'une semaine ISO complète. Ce n'est pas un rendement hebdomadaire.
- **Semaine complète** : semaine ISO du lundi au dimanche avec sept observations quotidiennes valides. Une cible incomplète n'est pas imputée.
- **Snapshot d'émission** : observations et variables disponibles à la date de production d'une émission. Une correction reçue plus tard ne modifie pas une émission déjà publiée.
- **Taux FX de l'émission** : dernier taux USD/EUR ou USD/CHF connu à la coupure de l'émission. Il convertit le forecast USD sur tous les horizons sans constituer une prévision de change.
- **Forecast converti** : expression en EUR ou CHF du même forecast USD avec le taux FX de l'émission. Il ne s'agit pas d'un modèle indépendant par devise.

## Quantiles du forecast

- **Q25, Q50 et Q75** : quantiles de niveaux 25 %, 50 % et 75 % du prix prévu à une échéance. Q50 est la médiane.
- **Bande centrale à 50 %** : intervalle entre Q25 et Q75, dont la couverture nominale est 50 %. Sa couverture réelle dépend de la calibration du modèle et doit être mesurée.

