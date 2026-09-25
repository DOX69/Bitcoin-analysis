# Chronos-2 quotidien multivarié

Essai borné exécuté le 20 septembre 2026. Il reste séparé de `daily-v1` et ne
modifie ni les émissions Development ni le registre Production.

## Protocole

- Snapshot OHLCV Development du 17 septembre 2026, du 20 juillet 2015 au 13
  septembre 2026, 4 074 jours, empreinte
  `f2b595b15dc68d512bbdf69dec65ec16e7cfdc60f18f4da4eb156212b942f491`.
- Checkpoint `autogluon/chronos-2-small`, révision
  `ddec01313e50b6bc58ebaa92ede81bc24a3d9f9a`, licence Apache-2.0.
- Package isolé `chronos-forecasting==2.3.2`, PyTorch CPU, deux threads.
- Entrée multivariée causale composée de `log(close)`, `log1p(volume)` et
  `log(high / low)`. Chaque origine utilise seulement les journées jusqu'au
  dimanche inclus.
- Contexte fixé à 2 048 jours, horizon fixé à 365 jours, quantiles
  Q10/Q25/Q50/Q75/Q90. Le checkpoint expose un contexte maximal de 8 192 et un
  horizon maximal de 1 024, donc le contrat testé reste dans ses limites.
- Origines du dimanche après 1 095 jours de chauffe, avec 365 cibles matures et
  26 origines annuelles antérieures pour calibrer la référence prix inchangé.
  Le runner a évalué 295 origines. Les tableaux de comparaison contiennent 139
  origines anciennes et 104 récentes, comme les essais quotidiens précédents.
  Les 52 origines de transition autour de la date de coupure ne sont pas
  mélangées aux deux partitions.
- Aucune calibration Chronos n'a été ajoutée après coup. La référence prix
  inchangé utilise les erreurs log matures disponibles avant chaque origine.
  Le filtre de recherche était fixé avant le calcul : MAE et WIS au plus égales
  à 0,98 fois la référence dans les deux partitions, et MAE au plus égale à
  1,05 fois la référence à J+1, J+7, J+30, J+90, J+180 et J+365.

## Résultats

| Partition | Origines | MAE Chronos / référence | WIS Chronos / référence | Couverture 50 % | Couverture 80 % |
|---|---:|---:|---:|---:|---:|
| Ancienne | 139 | 17 011,60 / 15 173,32 USD | 13 357,87 / 12 864,41 | 0,452 | 0,776 |
| Récente déjà examinée | 104 | 22 373,90 / 21 763,80 USD | 15 539,11 / 15 243,85 | 0,467 | 0,803 |

Les ratios MAE sont 1,121 et 1,028. Les ratios WIS sont 1,038 et 1,019.
Chronos dépasse donc la référence dans les deux partitions et échoue le filtre
avant toute question de promotion.

Aux points longs, le ratio de MAE à J+365 vaut 1,164 dans la partition
ancienne et 1,090 dans la récente. À six mois, il vaut 1,163 et 1,015. Le
modèle reste donc trop mauvais sur l'année complète, et son gain apparent à
J+180 dans la partition récente ne suffit pas à compenser les autres échéances.

Le modèle est meilleur que le LightGBM quotidien prix seuls sur les deux
partitions, mais cette comparaison ne change pas la décision : le LightGBM
perdait déjà face au prix inchangé et Chronos-2 le perd aussi.

## Coût et archive

Le run supervisé a duré 101,10 secondes, avec un pic RSS de 567,79 Mio. Son
équivalent Railway indicatif est de 0,0031 USD. L'archive complète est hors Git
dans `C:/Users/ggrft/forecast-evidence/20260920/chronos2-daily-v2/`.

- `manifest.json` :
  `8278989781901AE13152E4044B13E817A17F97C89CB70A3F2DA18CAC085AC5CB`
- `report.json` :
  `55F56A36761F5086303EF609A4D7F054FBE19594A711376E4C5D1BEAC529AB1D`
- `predictions.json` :
  `85BDEFA2345EB5E715E678022A19289E1B709852FDB2E826B412296478032CBC`

Décision : `reject_all_challengers`. Aucun déploiement, changement d'interface
ou promotion n'est justifié par cet essai. La preuve prospective reste requise
pour toute recette future.

Les limites du modèle préentraîné et son support multivarié sont décrits dans le
[model card Chronos-2](https://huggingface.co/autogluon/chronos-2) et le dépôt
[chronos-forecasting](https://github.com/amazon-science/chronos-forecasting).
