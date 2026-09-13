# Recherche de modèles après le premier benchmark

## Complément du 13 septembre 2026

Trois nouvelles hypothèses causales ont été figées avant mesure, puis exécutées successivement sur le même snapshot. Elles échouent toutes. Aucun modèle prêt pour la production n'est établi. Le [dossier de préparation](READINESS.md) fixe la suite et la collecte prospective.

| Recette | WIS USD, 129 origines | Horizons en échec, sélection | Première période | Stress intermédiaire | Seconde période |
|---|---:|---:|---:|---:|---:|
| Variance EWMA, retour vers variance longue | 10 695,74 | 8 / 52 | 10 / 52 | 46 / 52 | 14 / 52 |
| 64 régimes historiques proches, labels matures | 14 055,04 | 43 / 52 | 45 / 52 | 44 / 52 | 42 / 52 |
| Erreurs normalisées regroupées entre horizons | 10 846,80 | 35 / 52 | 52 / 52 | 37 / 52 | 18 / 52 |

Les médianes restent le dernier close. Leur MAE est donc celle de la référence. Les échecs concernent les bandes. Les trois périodes ont déjà été consultées ; aucune n'est une confirmation indépendante. Le regroupement suppose une normalisation par racine de l'horizon, à tester, sans garantie de stabilité des régimes. Les voisins utilisent uniquement les états connus et les labels matures, avec standardisation sur ces seuls états.

Le manifeste de `regime_research.py` précise les équations, fenêtres et paramètres des trois recettes. Il archive le code, le lock et leurs empreintes avant scoring. Chaque worker vérifie les sources, les dépendances et le snapshot, puis conserve les prédictions, les 52 scores par période, les blocs temporels et un rechargement de contrôle. Les sorties finales sont des rejeux historiques, pas des émissions prospectives.

Mesures supervisées, dans l'ordre du tableau : 1,87 s et 67,40 Mio ; 104,31 s et 61,80 Mio ; 2,88 s et 62,18 Mio. Deux CPU, plafond 4 Gio et 30 minutes par recette. Aucun entraînement Railway.

Preuves conservées hors des dossiers temporaires dans `C:/Users/ggrft/forecast-evidence/20260913/regimes-a1/`, avec manifestes, rapports, prédictions, ressources, code et inventaire. L'ancien hybride est également conservé dans `hybrid-frozen/`. Les copies n'altèrent pas les mesures initiales.

Contrôle de la source vivante le 13 septembre : 581 semaines complètes, une seule clôture différente du snapshot figé. La semaine du 31 août passe de 79 853,98 à 80 339,13 USD. Les scores ci-dessus conservent le snapshot initial pour comparer les recettes sur les mêmes données. La cause de cette révision n'est pas établie ; les deux versions sont archivées dans `snapshot-drift.json` et les snapshots voisins. Les prévisions figées ne sont pas réécrites.

Les distributions gaussiennes et la simulation de trajectoires sont décrites dans [Forecasting: Principles and Practice, intervalles prédictifs](https://otexts.com/fpp3/prediction-intervals.html). Les recettes de ce lot sont nos hypothèses, pas des résultats validés par cette source. La littérature sur [l'adaptation sous changement de distribution](https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html) motive la prudence sur les régimes ; aucune garantie conforme n'est revendiquée pour ces trois recettes.

## Recherche du 10 septembre 2026

Recherche du 10 septembre 2026, demandée par le propriétaire après les échecs du premier cycle. Suivi : [Rechercher et mesurer un modèle admissible après le premier benchmark](https://github.com/DOX69/Bitcoin-analysis/issues/92). Les propositions du dossier brainstorming ont servi à définir des expériences ; elles ne constituent pas des décisions de promotion.

## Résultats mesurés

Douze nouvelles recettes ont été exécutées. Un hybride satisfait les 52 garde-fous sur les 129 origines déjà consultées, mais échoue sur 46 horizons dans une période intermédiaire supplémentaire. Sa sélection utilise les résultats précédents : ce passage des seuils ne démontre pas une robustesse hors sélection. Aucun modèle livrable n'est établi par cette recherche.

La marche sans dérive avec volatilité sur les 104 semaines observées les plus récentes améliore nettement le premier benchmark : WIS de 10 683 USD, contre 16 157 pour le prix inchangé et 17 911 pour le gaussien initial. Cette nouvelle recette change à la fois la dérive et l'estimation de volatilité. Le gain ne peut pas être attribué à un seul de ces changements.

Elle respecte la limite de MAE et la couverture 80 % sur les 52 horizons. Deux horizons échouent encore pour la couverture 50 % : 1 semaine, 62,79 %, et 41 semaines, 38,76 %. Elle n'est donc pas admissible en l'état.

| Nouvelle recette | WIS USD | MAE USD | Horizons hors seuils MAE / couverture 50 % / couverture 80 % | Horizons en échec, union |
|---|---:|---:|---:|---:|
| Gaussien sans dérive, volatilité glissante 104 semaines | 10 683,20 | 16 157,37 | 0 / 2 / 0 | 2 / 52 |
| Bandes empiriques absolues, 156 labels matures par horizon | 11 847,54 | 16 157,37 | 0 / 47 / 42 | 49 / 52 |
| Bandes empiriques, dérive réduite au dixième | 12 160,17 | 16 353,13 | 6 / 46 / 42 | 48 / 52 |
| Régression quantile linéaire L1, alpha 0,01 | 52 134,25 | 74 528,88 | 51 / 45 / 46 | 51 / 52 |
| Bandes empiriques normalisées par la volatilité | 10 893,36 | 16 157,37 | 0 / 13 / 19 | 22 / 52 |
| Chronos-Bolt tiny, zero-shot sur log-prix | 20 696,32 | 24 559,13 | 52 / 43 / 51 | 52 / 52 |
| Chronos-2-small, zero-shot sur log-prix | 14 292,46 | 18 257,50 | 52 / 39 / 38 | 52 / 52 |
| Student à 5 degrés, dérive latente centrée | 10 789,35 | 16 157,37 | 0 / 0 / 23 | 23 / 52 |
| NHITS compact, 300 étapes | 20 695,63 | 24 073,08 | 52 / 49 / 51 | 52 / 52 |
| Combinaison gaussien / Student apprise par horizon et quantile | 10 901,84 | 16 157,37 | 0 / 0 / 5 | 5 / 52 |
| Combinaison avec un poids commun par horizon | 10 784,80 | 16 157,37 | 0 / 0 / 13 | 13 / 52 |
| Hybride sélectionné : Student central, gaussien externe | 10 656,49 | 16 157,37 | 0 / 0 / 0 | 0 / 52 |

Les couvertures sont vérifiées sans arrondi : 117 observations couvertes sur 129 donnent 90,6977 %, au-dessus du maximum 90 %. Les erreurs par horizon sont calculées sur les mêmes origines que la référence.

La Student et la combinaison apprise corrigent la bande centrale, mais élargissent trop la bande externe à long terme. Chronos-2-small améliore le WIS du prix inchangé, mais sa MAE dépasse la limite sur chacun des 52 horizons. Les modèles neuronaux essayés n'apportent donc pas une solution admissible dans ces recettes précises.

### Contre-épreuve et candidat concret

L'hybride garde Q10/Q90 du gaussien glissant et Q25/Q50/Q75 de la Student. Il refuse les croisements au lieu de les masquer par un tri. Ce choix a été fait après avoir vu quel composant satisfait chaque bande : ses 52 réussites sur le benchmark de sélection sont attendues, pas une découverte indépendante. La médiane reste le dernier prix ; le gain mesuré porte sur la prévision probabiliste, pas sur une meilleure direction centrale.

La recette a ensuite été appliquée sans changement aux origines `[412, 464)`, absentes de la comparaison initiale. Ce test de sensibilité reste rétrospectif et ses cibles chevauchent les autres périodes. WIS 13 422,27 USD, amélioration de 35,73 % face à sa référence centrale, mais 46 horizons échouent. À 52 semaines, couvertures 50 % et 80 % de seulement 21,15 % et 48,08 %. Le défaut de couverture dans ce régime empêche de présenter l'hybride comme une solution validée.

Une prévision locale a été figée le **10 septembre 2026 à 18:03:51 UTC**, depuis le dernier close observé de 79 853,98 USD. Elle contient 52 cibles du 13 septembre 2026 au 5 septembre 2027, avec statut `research_shadow_local`. Elle n'est ni publiée ni enregistrée comme version active. Le fichier `research-shadow.json` et son empreinte dans l'inventaire permettent un suivi ultérieur ; aucun score prospectif n'existe encore. Le manifeste de cette expérience porte l'empreinte `3c8b3864ce908e1acdbb01c635ddd82eb1f61337b95c2c6a3d04377fb92d24c3`.

Empreinte SHA-256 de cette prévision, consignée dans ce commit : `6e3b828e2b34b416ea4aee780d9db531b34917238e2ec4f018d16a54cfeb2aff`.

La prochaine amélioration doit corriger la dépendance des bandes au régime de marché, puis résister à des périodes distinctes. Retoucher les seules bornes qui échouent sur ce tableau ne fournirait pas cette preuve. Les nouvelles données réellement observées après gel de la recette devront être conservées pour la confirmation ; les résultats déjà consultés restent disponibles pour développer les modèles.

## Protocole et limites

- Snapshot inchangé : 581 semaines complètes, SHA-256 `95fa242dd1a907a8cb7b122fb1ea974542c0541b0d3e14135197ac2e3c4d571b`.
- Origines d'indices `[348, 412)` et `[464, 529)`, soit 129 origines avec leurs 52 cibles matures. Calcul Q10/Q25/Q50/Q75/Q90 et scoring commun de `benchmark.py`.
- Seuils conservés pour chaque horizon : MAE au plus égale à 1,05 fois la référence centrale, couverture 50 % entre 40 et 60 %, couverture 80 % entre 70 et 90 %.
- Une médiane égale au dernier prix peut satisfaire le garde-fou de première version. Le gain WIS de 5 % concerne le remplacement d'un modèle actif ; il ne constitue pas une condition supplémentaire inventée pour ce premier modèle.
- Les modèles statistiques réestiment leurs paramètres avec les données connues à chaque origine. Linear et NHITS gardent leurs entraînements de folds ; Chronos garde ses poids préentraînés et reçoit le contexte connu. Ces différences appartiennent aux recettes comparées.
- La sélection des poids de combinaison emploie uniquement des labels `j+h <= origine`, sur les 156 origines matures les plus récentes. Grille fixe `0, 0.25, 0.5, 0.75, 1`, pinball loss, égalités départagées par proximité de 0,5 puis poids inférieur. Les cinq quantiles sont triés après combinaison.
- Chaque recette est définie et identifiée par empreinte avant son premier score. Les normalisations, la Student et les combinaisons sont des hypothèses supplémentaires formulées après examen des résultats précédents. La série entière reste une exploration adaptative ; figer le code avant un essai ne rend pas ce jeu de données indépendant.
- Les labels longs se chevauchent. Les 129 origines ne représentent pas 129 années indépendantes. Les résultats agrégés masquent des différences entre périodes : le gaussien glissant échoue sur 13 horizons dans la première période et 11 dans la seconde.
- Un chevauchement des données de préentraînement Chronos avec Bitcoin n'est pas exclu. Le rechargement exact hors réseau des deux checkpoints a été vérifié pour les 52 horizons de la première origine ; cela démontre la reproductibilité de cette inférence, pas l'absence de contamination historique ni un rejeu complet des 129 origines.

Les critères de confirmation prospective et la revue de promotion restent applicables. Aucun résultat de ce document ne constitue une preuve prospective. La livraison reste ouverte ; aucun seuil ni registre de production n'est modifié par les runners de recherche.

## Ressources locales

Les modèles ont été exécutés successivement, sous supervision de l'arbre des processus, avec affinité de deux CPU, 4 Gio maximum et 30 minutes maximum par recette. Aucun entraînement Railway ni service permanent ajouté.

| Exécution | Durée supervisée s | Pic RSS arbre Mio |
|---|---:|---:|
| Trois premières recettes statistiques, ensemble du lot | 1,85 | 44,63 |
| Linear | 16,38 | 155,88 |
| Normalisation | 6,53 | 42,99 |
| Bolt tiny, chargement et rechargement inclus | 35,65 | 436,91 |
| Chronos-2-small, chargement et rechargement inclus | 19,70 | 486,07 |
| Student | 1,00 | 173,45 |
| NHITS, deux entraînements et prédictions | 65,15 | 489,14 |
| Combinaison par quantile | 8,23 | 173,30 |
| Combinaison à poids commun | 7,36 | 173,26 |
| Hybride, comparaison et contre-épreuve | 1,11 | 173,41 |

Ces durées n'incluent pas l'installation des dépendances. Les environnements neuronaux sont isolés dans le dossier temporaire ; `pyproject.toml` et `uv.lock` du projet restent inchangés. Deux démarrages NHITS ont échoué avant entraînement à cause de fichiers manquants dans des paquets installés. Les mêmes versions ont été réinstallées avec copie des fichiers, puis la recette inchangée a été mesurée.

## Sources et reproduction

Les notes [pistes des documents](../brainstorming/model-pistes-2026-09-10.md) et [modèles CPU](../brainstorming/model-cpu-research-2026-09-10.md) contiennent les sources primaires et les choix d'adaptation au contrat hebdomadaire.

Les preuves locales sont sous `%TEMP%` :

| Recette | Dossier |
|---|---|
| Statistiques initiales | `bitcoin-forecast-challengers-20260910-a1` |
| Linear | `bitcoin-forecast-linear-20260910/run` |
| Normalisation | `bitcoin-forecast-normalized-20260910-a1` |
| Bolt tiny | `bitcoin-chronos-research-20260910-a1` |
| Chronos-2-small | `bitcoin-chronos2-research-20260910-a1` |
| Student | `bitcoin-forecast-student-20260910-a1` |
| NHITS | `bitcoin-nhits-research-20260910-run2` |
| Combinaison par quantile | `bitcoin-forecast-stacking-20260910-a1` |
| Combinaison à poids commun | `bitcoin-forecast-shared-stacking-20260910-a1` |
| Hybride et prévision locale figée | `bitcoin-forecast-hybrid-20260910-a1` |

Les dossiers conservent manifestes, métriques par horizon et période, prédictions et ressources ; la combinaison exporte aussi ses poids. Les scripts sont dans `forecast/*research.py` et `forecast/challengers.py`. Pour Linear et NHITS, utiliser le superviseur `forecast.pipeline.supervise` autour de leur CLI : lancer ces modules seuls ne garantit pas les limites de mémoire et de durée. La commande NHITS complète figure dans son `execution.json`.

Les archives des runners et du scorer ont été comparées aux empreintes de leurs manifestes. Certaines copies auxiliaires ont été ajoutées après exécution ; quand leur empreinte n'était pas dans le manifeste initial, leur inventaire l'indique. Le runner Chronos a ensuite été généralisé pour les deux checkpoints et formaté ; le code exact de chaque mesure demeure dans son archive. Les manifestes enregistrent les versions, mais tous les runners ne les refusent pas automatiquement si l'environnement change : reconstruire et vérifier l'environnement enregistré avant tout rejeu.

Les tests dédiés vérifient notamment l'insensibilité aux valeurs futures, la maturité des labels, la standardisation sur l'entraînement seul, les quantiles, la simulation antithétique et la sélection causale des poids. Les contrôles de compilation, style et scoring sont exécutés avant les commits. Ces tests logiciels ne démontrent pas une qualité prédictive future.

Vérifications de cette série : **53 tests Python ciblés distincts passent**, exécutés en plusieurs lots, dont 24 tests des nouveaux runners et 29 du benchmark/pipeline existant. Black vérifie les 18 nouveaux fichiers Python ; Ruff et `git diff --check` passent. Les revues indépendantes ne trouvent pas de fuite future dans les recettes. La carte locale, maintenue hors Git, passe ses quatre tests et présente les 18 issues dans les vues Workflow et Kanban vérifiées dans Chrome. Il ne s'agit pas d'une nouvelle exécution de toute la suite applicative ni de la CI distante.
