# Recherche multi-échelle quotidien / hebdomadaire

Contrat de recherche ajouté le 20 septembre 2026. Cette recette reste hors
Production et ne modifie ni `daily-v1`, ni le dashboard, ni le stockage
hebdomadaire.

## Hypothèse

Le modèle quotidien précédent extrapole seul la trajectoire sur un an. Des
ancres hebdomadaires pourraient mieux contraindre les horizons longs, tandis
qu'un résidu quotidien conserverait les effets de court terme et du jour de la
semaine.

Cette expérience teste une architecture différente. Elle ne transforme pas un
résultat historique en preuve prospective.

## Contrat causal

Chaque origine est un dimanche dont le close UTC est disponible.

1. Le composant hebdomadaire ajuste le `damped-trend-v1` existant sur les 104
   derniers closes dominicaux accessibles à l'origine. Il produit les ancres
   J+7, J+14, ..., J+364 en espace log.
2. Chaque ancre reçoit une calibration séparée. Les erreurs utilisées ont une
   origine antérieure et une cible arrivée à maturité avant l'origine courante.
   Au plus 104 erreurs sont conservées, avec un minimum de 26.
3. La trajectoire intermédiaire interpole linéairement les quantiles calibrés
   en espace log. J+365 prolonge d'un jour la pente entre J+357 et J+364.
4. Le résidu observé d'un jour est son log-close moins la droite log entre les
   deux closes dominicaux de sa semaine. La recette utilise les 26 dernières
   semaines terminées du même jour de semaine et rescale les écarts autour de
   leur médiane par la volatilité des rendements log passés sur 30 jours.
5. Les quantiles du résidu sont ajoutés à la trajectoire pour les jours qui ne
   sont pas des dimanches. Le résidu est exactement nul à J+7, J+14, ..., J+364.
   La prévision finale reprend donc exactement l'ancre hebdomadaire à ces
   horizons. Les cinq quantiles sont triés après combinaison.

Le résidu d'une semaine passée peut utiliser son close dominical parce que ce
close était connu avant toute origine ultérieure. Il ne peut jamais utiliser
une observation située après l'origine évaluée.

## Comparaison

Le benchmark utilise les mêmes origines dominicales matures que `daily-v1` et
la séparation du 13 septembre 2023 :

- référence prix inchangé avec calibration probabiliste ;
- modèle quotidien prix seul `ridge` déjà étudié ;
- composant hebdomadaire interpolé seul ;
- modèle multi-échelle complet.

Les scores incluent MAE, RMSE, WIS, couvertures et largeurs pour les 365
horizons, ainsi que J+1, J+7, J+30, J+90, J+180 et J+365. Les horizons du
dimanche sont comparés séparément au modèle hebdomadaire historique.

Le garde-fou de recherche reste celui de `daily_recovery` : un candidat doit
améliorer MAE et WIS de 2 % dans les deux partitions et rester à au plus 1,05
fois la MAE de la référence à chacun des six jalons. Un candidat qui échoue
reste rejeté, avec le prix inchangé comme fallback. Aucun seuil Production
n'est modifié.

## Implémentation et tests

Le code est isolé dans `forecast/multiscale_research.py`. Les tests de
`forecast/test_multiscale_research.py` vérifient :

- l'absence d'influence des prix futurs et des futurs dimanches ;
- la maturité des labels quotidiens et hebdomadaires ;
- la réconciliation exacte des 52 ancres ;
- les 365 dates, cinq quantiles finis et ordonnés ;
- la règle de partition commune aux candidats.

Le benchmark reste une relecture historique sur snapshot révisé. L'archive,
le manifeste, les prédictions, les scores et les ressources doivent être
écrits hors Git. Une réussite historique ne suffit pas à promouvoir la recette
en Production.
