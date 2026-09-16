# Prévisions quotidiennes, recalcul hebdomadaire

Recherche et premier benchmark du 16 septembre 2026. Le protocole initial ci-dessous est suivi des résultats exécutés et de l'intégration Development. Aucun modèle n'est validé pour la production.

## Recommandation

Conserver l'objectif d'un an : produire 365 clôtures quotidiennes BTC/USD, calculées chaque lundi à 07:00 Europe/Paris avec les journées UTC complètes disponibles. Comparer explicitement les résultats à six mois calendaires. Le quotidien répond mieux au besoin d'affichage immédiat, mais son avantage statistique reste à mesurer.

Trois paramètres sont indépendants : fréquence des observations, fréquence des cibles prédites, fréquence du recalcul. On peut entraîner sur des journées, prédire chaque journée et recalculer une fois par semaine. Il ne faut ni entraîner 365 fois par semaine, ni attendre la réalisation de la dernière prévision pour produire la suivante.

52 semaines représentent 364 jours ; 52 jours ne représentent pas un an. Le contrat proposé utilise 365 jours. Six mois calendaires représentent environ 181 à 184 jours ; J+180 reste un jalon de mesure, pas nécessairement la fin exacte des six mois.

## Ce que fait réellement le projet

`benchmark.aggregate_daily_rows` vérifie sept jours complets, puis retient seulement le dernier close, celui du dimanche. Ce n'est ni une moyenne ni une somme des prix. `trend_research.py` appelle cette fonction avant l'entraînement. Le lecteur serveur, `useForecast.ts` et le stockage V1 attendent 52 horizons hebdomadaires. Le choix weekly vient du contrat de première version, pas d'une impossibilité de travailler en daily.

Audit effectué sur le snapshot archivé le 14 septembre, sans le présenter comme une extraction à jour du 16 septembre :

| Contrôle | Résultat |
|---|---:|
| Période | 20 juillet 2015 au 13 septembre 2026 |
| Observations quotidiennes | 4 074 |
| Clôtures du dimanche retenues | 582 |
| Journées manquantes | 0 |
| Dates dupliquées | 0 |
| Clôtures non positives ou non finies | 0 |
| Corrélation entre log-prix de deux jours successifs | 0,99979 |
| Corrélation entre rendements logarithmiques de deux jours successifs | -0,04803 |

Ces deux corrélations sont descriptives, sans test de significativité. Des niveaux très proches d'un jour à l'autre ne démontrent pas qu'on sait prévoir leurs variations. Elles ne mesurent pas non plus toute dépendance non linéaire ou celle de la volatilité.

Source locale : `C:/Users/ggrft/forecast-evidence/20260914/trend-daily.json`. Empreinte SHA-256 : `31dd26899a74f86a7b968aa77bdcd9611f4b5d84ac88df57566c8b93ac94b4b1`. Audit enregistré dans `C:/Users/ggrft/forecast-evidence/20260916/daily-audit.json`.

Les horodatages d'ingestion vont du 30 août au 14 septembre 2026. Ce snapshot n'est donc pas une archive de toutes les versions réellement disponibles depuis 2015. Un rejeu utilisant ces prix sera causal dans son découpage, mais restera exposé aux révisions rétrospectives de la source. Ne pas antidater ces ingestions ni appeler ce rejeu une preuve prospective.

## Ce que les sources permettent de conclure

Le quotidien conserve les mouvements intrasemaine et peut aider les horizons courts ou l'estimation de volatilité. Il apporte aussi davantage de bruit et ne multiplie pas le nombre d'années, de crises ou de régimes observés. Les travaux sur les hiérarchies temporelles montrent un intérêt possible à combiner les fréquences ; ils ne démontrent pas que le quotidien domine pour Bitcoin. Attention : leur agrégation additive ne s'applique pas directement à des prix de clôture. Un close hebdomadaire est le close du dimanche, pas la somme des closes quotidiens. [Athanasopoulos et al., 2017](https://robjhyndman.com/publications/temporal-hierarchies/).

Des données journalières peuvent avoir plusieurs saisonnalités. Cela justifie de rechercher un éventuel effet du jour de semaine ; cela ne prouve pas que Bitcoin possède une saisonnalité annuelle stable. Ne pas imposer une saisonnalité de 365 jours ou un cycle de halving sur la seule base du calendrier. [Hyndman, données quotidiennes](https://robjhyndman.com/hyndsight/dailydata/).

L'étude Bitcoin de Berger et Koubová, publiée en 2024, compare des modèles économétriques et neuronaux sur des horizons de 1, 5 et 10 jours. Le classement dépend de la métrique ; les architectures plus complexes n'apportent pas systématiquement de gain. Sa référence naïve utilise le rendement précédent, ce qui diffère de notre référence à prix inchangé, équivalente à un rendement futur nul. Cette étude ne valide donc ni un horizon de 365 jours, ni une supériorité face à notre référence exacte. [Article original, tableaux 4 à 8](https://d-nb.info/1345670222/34).

Une prévision à 365 jours est calculable. Sa précision n'est pas garantie : les distributions futures s'élargissent généralement avec l'horizon et restent dépendantes des hypothèses du modèle. Afficher 365 points n'apporte pas 365 certitudes. Une courbe centrale lisse ou plate peut être légitime ; ne pas ajouter de zigzags pour donner une apparence de précision. [FPP3, distributions et intervalles](https://otexts.com/fpp3/prediction-intervals.html).

La référence à prix inchangé doit rester dans l'évaluation, même si elle n'est pas le produit attendu visuellement. Elle peut être difficile à battre sur une série financière. Notre tendance amortie hebdomadaire a une MAE historique supérieure de 21,5 % à cette référence : passer en daily ne corrige pas automatiquement ce défaut. [FPP3, références simples](https://otexts.com/fpp3/simple-methods.html), [mesure du projet](RESEARCH.md).

## Définir les dates sans ambiguïté

Exemple : émission le lundi 14 septembre à 07:00 Paris, dernier close complet du dimanche 13 septembre UTC.

| Horizon depuis le dernier close | Cible |
|---|---|
| h=1 | Close du lundi 14 septembre, connu après la fin de cette journée UTC |
| h=2 | Close du mardi 15 septembre |
| h=7 | Close du dimanche 20 septembre |
| h=365 | Close du 13 septembre 2027 |

Le premier point peut donc concerner le jour même de l'émission, sans utiliser sa clôture encore inconnue. « J+1 depuis l'émission » désignerait au contraire le mardi. Utiliser `issued_at`, `observed_through`, `target_date` et `horizon_days` explicitement ; privilégier les dates dans l'interface.

Un visiteur du mercredi voit les prévisions du lundi pour mercredi et les jours suivants. Elles ne prennent pas en compte les nouvelles observations de lundi/mardi tant qu'on conserve un recalcul hebdomadaire. Afficher la date de calcul et séparer les cibles déjà observées des cibles futures. Mettre la courbe à jour avec le dernier prix tous les jours serait une autre politique d'inférence, à tester séparément.

## Expérience proposée

Le principe retenu est celui des origines glissantes : rejouer les lundis successifs et prévoir plusieurs horizons à chaque passage. Ne jamais mélanger aléatoirement les dates. [FPP3, validation chronologique multi-horizon](https://otexts.com/fpp3/tscv.html).

1. Archiver un snapshot et figer les recettes, fenêtres, métriques, budgets et règles de sélection avant les scores. Commencer les émissions après au moins trois années d'historique, sans prétendre que ce minimum garantit une précision donnée.
2. À chaque lundi, reconstruire les observations accessibles avant 07:00 Paris et exclure la journée en cours de l'entraînement. Pour les années sans archives de révisions, expliciter l'approximation du rejeu.
3. Ajuster les paramètres une fois pour ce lundi, puis émettre et archiver les 365 dates. Pour un exemple d'entraînement d'origine j et de cible j+h, exiger j+h au plus égal au dernier jour observé. Même règle pour les erreurs de calibration.
4. Calculer indicateurs, normalisation et sélection de variables sur le passé admissible seulement. Pour les validations internes, exclure les labels traversant leur frontière. Un découpage chronologique des lignes seul ne suffit pas si leurs cibles sont futures. `TimeSeriesSplit` fournit des découpages et un `gap`, mais le filtrage des cibles doit respecter chaque horizon. [Documentation scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html), [Kapoor et Narayanan, erreurs de fuite](https://reproducible.cs.princeton.edu/).
5. Mesurer h=1, 7, 30, 90, 180, la date à six mois et h=365, ainsi que toute la courbe d'erreur. Comparer le daily et le weekly sur leurs dates communes du dimanche. Ne pas interpoler les points weekly puis prétendre qu'ils étaient des prévisions quotidiennes du modèle.
6. Comparer les modèles sur les mêmes origines pour chaque horizon. Pour comparer les horizons entre eux, publier aussi un tableau limité aux origines dont les 365 cibles sont toutes matures, afin de ne pas confondre effet d'horizon et période de marché.

Pour distinguer l'effet de fréquence de celui de mémoire historique, comparer des fenêtres de même durée : 104 semaines face à 728 jours, et non 104 semaines face à 104 jours. Comparer une fenêtre plus longue constitue une expérience distincte. Aucun indicateur, volume ou taux de change futur observé ne peut être injecté pour produire les 365 points.

### Effectif historique disponible

Comptage sur le snapshot audité, avec un dernier close d'origine le dimanche et au moins 1 095 journées initiales. Il s'agit d'effectifs, pas de résultats de modèles.

| Horizon en jours | Émissions du lundi évaluables | Origines dans les trois dernières années du snapshot |
|---|---:|---:|
| 1 | 425 | 156 |
| 7 | 425 | 156 |
| 30 | 421 | 152 |
| 90 | 413 | 144 |
| 180 | 400 | 131 |
| 184 | 399 | 130 |
| 365 | 373 | 104 |

Ces observations ne sont pas indépendantes. Deux prévisions annuelles émises à une semaine d'intervalle traversent presque la même période. Présenter les différences d'erreur par blocs calendaires et une analyse de sensibilité par blocs d'origines. Éviter les intervalles de confiance obtenus en traitant toutes les lignes origine/horizon comme indépendantes. Onze années de prix ne deviennent pas des centaines de régimes annuels distincts.

### Modèles à comparer d'abord

| Famille | Question testée |
|---|---|
| Prix inchangé avec distribution d'erreurs calibrée | Le candidat apporte-t-il quelque chose au-delà d'une référence simple ? |
| Tendance amortie quotidienne, même durée de mémoire que le weekly | Conserver les jours intermédiaires aide-t-il cette recette ? |
| Régression directe régularisée des rendements cumulés, par horizon | Les signaux connus permettent-ils d'estimer chaque échéance sans itérer 365 erreurs à un jour ? |
| Petit modèle d'arbres en régression quantile, avec horizon explicite | Des relations non linéaires ajoutent-elles un gain stable ? |

Pour la régression directe, n'utiliser que les labels matures propres à chaque horizon ; ne pas jeter inutilement les exemples récents du court terme pour aligner toutes les cibles à 365 jours. Limiter la recherche de paramètres avant mesure. Les stratégies récursive et directe ont des compromis différents ; aucune n'est universellement supérieure. [Ben Taieb et Hyndman, stratégies multi-horizon](https://robjhyndman.com/publications/rectify/).

Les modèles neuronaux lourds ou préentraînés ne sont pas la première étape recommandée : commencer par des références auditables et un protocole fiable. Une extension ultérieure devra documenter les données de préentraînement et un éventuel chevauchement avec la période évaluée.

### Mesures et décision

Évaluer séparément l'erreur de la médiane, les bandes et la qualité opérationnelle. Retenir la MAE par horizon, la différence et le ratio face au prix inchangé, puis la RMSE pour les grosses erreurs. Rapporter aussi les résultats par période pour que les niveaux de prix récents ne masquent pas les autres régimes.

Conserver Q10/Q25/Q50/Q75/Q90. Mesurer couvertures, largeur et WIS ; comparer aussi à une référence probabiliste calibrée, pas uniquement à une distribution de largeur nulle. Un WIS meilleur peut coexister avec une médiane moins bonne. Les bandes sont marginales par date : une bande 50 % ne signifie pas que toute la trajectoire annuelle y restera avec 50 % de probabilité. [Bracher et al., évaluation des intervalles](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1008618).

Avant le prochain benchmark, figer les critères du nouveau contrat daily. Pour recommander son remplacement du weekly, demander un gain de MAE et de WIS sur les échéances communes pertinentes, des couvertures acceptables et une stabilité entre périodes. Ne pas convertir les 52 seuils existants en 365 seuils par simple substitution. Ne pas choisir après coup seulement les horizons gagnants. Cette note ne change aucun seuil de promotion existant.

Garder 365 jours comme cible expérimentale. Si les six premiers mois sont défendables et les suivants trop incertains, limiter la portée validée à six mois et identifier séparément la partie exploratoire. Si même six mois ne sont pas défendables, le besoin minimum reste non atteint ; ne pas annoncer une réussite en raccourcissant silencieusement à 30 jours.

## Intégration à prévoir après benchmark

Créer une version et un espace d'artefacts quotidiens distincts. Adapter le contrat API, les validateurs client/serveur, les dates et les contraintes de stockage, aujourd'hui limités à 52 semaines. Conserver les émissions weekly comme archives comparables. 365 dates avec cinq quantiles représentent 1 825 nombres par émission, contre 260 actuellement ; ce volume seul ne bloque pas le dashboard. Le coût d'entraînement dépend du modèle et doit être mesuré.

Conserver le recalcul du lundi à 07:00 Paris, la collecte des observations quotidiennes et les copies indépendantes. Pour le premier lot, entraîner localement sous les limites de ressources existantes. Afficher la médiane et la bande quotidienne dans le prototype actuel, avec l'âge de l'émission. Les valeurs EUR/CHF restent des conversions à taux figé, pas une prévision conjointe de change.

Le 21 septembre à 19:00 reste un point de contrôle local. Aucune raison scientifique n'oblige à attendre cette date pour entraîner ou backtester. En revanche, vérifier en temps réel une prévision annuelle nécessite que sa cible annuelle arrive. La règle précédente de 104 observations prospectives est un choix conservateur du dossier V1, pas un théorème ni une condition pour rendre un aperçu Development consultable. Toute révision de cette règle doit être explicite, justifiée et définie avant les résultats concernés.

## Benchmark exécuté le 16 septembre

Le premier lot compare deux candidats bornés, Holt quotidien et régression ridge directe, au prix inchangé avec bandes probabilistes. L'ancien Holt weekly est recalculé sur les mêmes origines et cibles du dimanche. Le modèle d'arbres reste une expérience ultérieure ; ce lot ne permet pas de conclure sur tous les modèles possibles.

Holt utilise 728 clôtures quotidiennes. Ridge utilise les rendements sur 7, 30, 90 et 365 jours, et les volatilités sur 30 et 90 jours. Chaque horizon possède une régression directe, avec ses propres labels arrivés à échéance et sa normalisation calculée sur le passé. Les exemples d'entraînement ridge sont les 156 derniers dimanches éligibles, minimum 52 ; les observations quotidiennes servent aux variables et aux cibles, sans traiter les journées corrélées comme autant d'expériences indépendantes. La pénalité vaut 30. Ces choix sont fixés dans le manifeste avant calcul.

La calibration utilise au plus 104 erreurs de prévision déjà matures par horizon, minimum 26. Elle ajuste les cinq quantiles, y compris la médiane des candidats. Pour le prix inchangé, les corrections sont recentrées pour conserver exactement le dernier prix en Q50.

Sélection : 139 origines, du 19 janvier 2020 au 11 septembre 2022, dont toutes les cibles annuelles sont antérieures ou égales au 13 septembre 2023. Critère fixé : moyenne des ratios de MAE au prix inchangé à J+7, J+30, J+90, J+180 et J+365. Ridge obtient 1,533 contre 1,771 pour Holt. Ridge est donc sélectionné pour l'aperçu expérimental, sans gain revendiqué.

Contrôle : 104 origines du 17 septembre 2023 au 7 septembre 2025, toutes entièrement réalisées dans le snapshot arrêté au 13 septembre 2026. Cette période ne choisit pas le candidat. Elle reste un rejeu sur des données révisées, pas une preuve prospective ni 104 années indépendantes. Les journées cibles sont les clôtures UTC et J+1 désigne le lendemain du dimanche d'origine, donc le lundi du recalcul.

| MAE en USD, période de contrôle | Prix inchangé | Holt daily | Ridge daily sélectionné |
|---|---:|---:|---:|
| J+1 | 1 653 | 1 652 | 1 710 |
| J+7 | 3 340 | 3 421 | 3 441 |
| J+30 | 7 557 | 8 650 | 8 581 |
| J+90 | 15 438 | 19 954 | 19 037 |
| J+180 | 23 180 | 30 684 | 35 436 |
| J+365 | 35 663 | 85 144 | 84 208 |
| Moyenne des 365 horizons | 21 764 | 35 233 | 42 792 |

La médiane ridge a une erreur moyenne supérieure de 96,6 % à celle du prix inchangé sur les 365 horizons. Sur les 184 premiers jours, sa MAE est de 18 652 USD contre 14 705 USD, soit environ 26,8 % de plus. Réduire à six mois ne suffit donc pas à justifier une validation. L'aperçu conserve les 365 dates demandées, avec cette limite affichée.

Le WIS moyen ridge est de 31 344 contre 15 244 pour la référence probabiliste. Sa bande Q25-Q75 couvre 40,3 % des réalisations, contre 50 % nominalement ; Q10-Q90 couvre 66,8 %, contre 80 % nominalement. Ces bandes sont sous-calibrées sur le contrôle. Une jolie courbe ne corrige pas ce défaut.

Aux seules cibles communes du dimanche, la MAE est de 43 160 USD pour ridge daily, 35 542 USD pour Holt daily, 28 311 USD pour l'ancien Holt weekly et 22 011 USD pour le prix inchangé. Ce lot ne démontre aucun avantage statistique du passage au quotidien. Aucun seuil de promotion n'est abaissé après ce constat.

Le rapport contient MAE, RMSE, WIS, couvertures et largeurs pour chacun des 365 horizons, les deux partitions et la comparaison sur les dimanches. Il ne fournit pas d'intervalle de confiance fondé sur une fausse indépendance des origines. Une éventuelle expérience suivante devra annoncer sa sélection et ses périodes avant calcul ; cette période de contrôle est désormais consultée.

## Intégration Development exécutée

`daily_research.py` calcule les cibles quotidiennes ; `daily-selection.json` fige la recette retenue et l'empreinte du rapport. `daily_cloud.py` recalcule le lundi après ingestion/dbt, sous supervision de 300 secondes, deux CPU et 4 Go. Le cron d'ingestion reste quotidien à 07:00 Europe/Paris et score les cibles quotidiennes matures ; il ne réentraîne ce modèle que le lundi. Une option explicite `--bootstrap` autorise la première émission hors lundi avec l'horloge réelle.

L'émission initiale utilise les 4 076 clôtures complètes du 20 juillet 2015 au 15 septembre 2026, extraites de la base Development. Elle prédit du 16 septembre 2026 au 15 septembre 2027. Elle n'est pas antidatée au lundi. Snapshots, distributions et rapports sont immuables dans `development/research/daily-v1`, avec une copie indépendante relue. Le namespace de l'ancien weekly et la collecte prospective de l'hybride sont conservés.

L'API et le client distinguent 365 jours de 52 semaines et rejettent les dates ou nombres de points incohérents. Le prototype Wayfinder affiche les quantiles calculés, conserve le sélecteur des trois dernières émissions, et précise le recalcul du lundi. Les monnaies restent des conversions avec un taux connu lors de l'émission. Le stockage PostgreSQL de production V1 reste hebdomadaire ; l'aperçu quotidien utilise les artefacts S3, sans migration de production.

Le manifeste et le rapport du benchmark se trouvent dans `C:/Users/ggrft/forecast-evidence/20260916/daily-v1-run1/`, et dans les deux buckets sous `development/research/daily-v1/benchmark/`. SHA-256 du rapport : `58132a612c0180c121401324be82fc4ffdd9f37ed6cc3ff5692edd6be396db5a`. Le code exact avant formatage est archivé avec le manifeste ; le formatage ultérieur ne change pas la recette.

Conclusion de ce lot : besoin d'affichage quotidien satisfait en Development, avantage prédictif non démontré, livraison production non validée.
