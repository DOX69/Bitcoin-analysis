# Préparation d'un forecast pour la production

État du 14 septembre 2026 : objectif non atteint. La première émission hebdomadaire réelle à 52 horizons est enregistrée dans Railway Development et sa copie indépendante est vérifiée. Une cible de l'archive précédente est mature. Aucun modèle ne réunit encore les preuves statistiques et les conditions de promotion. Les trois nouveaux essais sont documentés dans [RESEARCH.md](RESEARCH.md).

## Décision de travail

Le propriétaire demande de poursuivre jusqu'à disposer d'un forecast prêt pour la production et délègue le choix du minimum d'observations nouvelles. Les seuils de qualité, les 52 horizons et la séparation historique/prospectif restent inchangés. Le passage de seuils sur des données déjà consultées ne suffit pas.

L'hybride du 10 septembre reste le candidat à observer : il passe les 52 horizons du benchmark de sélection, mais échoue sur 46 horizons du stress. Il reste en recherche. Ses équations et sa distribution sont conservées sans retouche. Le suivi ne constitue ni une sélection validée ni une activation de modèle.

## Confirmation prospective

Le collecteur `prospective_research.py` conserve les émissions locales du lundi, avec reprise possible le mardi, sous l'empreinte de manifeste `3c8b3864ce908e1acdbb01c635ddd82eb1f61337b95c2c6a3d04377fb92d24c3`. Il vérifie le code de recette, les versions numériques et la distribution archivée. Il ne contient aucun accès au registre de production.

- Minimum choisi : 104 observations matures à chacun des 52 horizons, et au moins deux blocs complets de h origines hebdomadaires contiguës pour chaque horizon h. À un an, cela fournit au moins deux blocs annuels pour examiner les différences de régime. Ce minimum est une règle de travail conservatrice, pas un seuil de significativité ni une preuve d'indépendance.
- Vérifier les garde-fous existants sur tous les horizons, puis examiner les scores et couvertures des blocs, leur dépendance et les écarts de régime. Des effectifs suffisants ne valent pas automatiquement confirmation suffisante.
- Toute modification de recette après examen de ces résultats exige une nouvelle version et une nouvelle confirmation. Conserver les observations antérieures comme développement.
- Les cibles deviennent matures le lundi UTC suivant leur dimanche de clôture. Les fichiers fictifs, historiques, antidatés, les doublons et les horizons absents ne comptent pas.
- Conserver les données quotidiennes reçues à chaque passage et les empreintes des émissions. Les révisions de source produisent un nouveau rapport, sans réécrire les prévisions.

Si la première émission régulière est créée le 14 septembre 2026, sa première cible annuelle sera le 12 septembre 2027. Avec une émission chaque semaine sans interruption, la 104e cible annuelle sera le 2 septembre 2029, scorée au plus tôt le lendemain. Ce calendrier exprime le temps nécessaire au minimum choisi ; il ne promet pas une validation à cette date.

La prévision du 10 septembre est désormais incluse dans les rapports prospectifs, sans modifier son fichier original. Son empreinte était déjà consignée dans RESEARCH.md avant ses cibles. Le collecteur vérifie cette empreinte exacte, le snapshot et le rejeu complet avant de l'admettre. Cette exception concerne uniquement ce document précis créé le jeudi 10 septembre à 18:03:51 UTC ; les nouvelles émissions restent limitées au lundi/mardi. Sa première cible est évaluable le 14 septembre 2026, et sa première cible annuelle le 6 septembre 2027 après la clôture du dimanche 5 septembre. Une seule observation annuelle ne suffira pas à confirmer sa couverture.

## Exécution locale

Les archives et observations sont conservées hors Git dans `C:/Users/ggrft/forecast-evidence/20260913/`. Le précontrôle réel a relu les 52 quantiles du modèle et les sept observations quotidiennes de la dernière semaine du snapshot. La source présente une révision de clôture documentée dans RESEARCH.md.

Depuis la racine du dépôt :

```powershell
uv run --locked --extra forecast python -m forecast.prospective_research `
  --bundle C:/Users/ggrft/forecast-evidence/20260913/hybrid-frozen `
  --directory C:/Users/ggrft/forecast-evidence/20260913/prospective `
  --base-url https://bitcoin-web-development.up.railway.app `
  --include-legacy-shadow
```

Le dimanche et du mercredi au samedi, la commande retourne `not_due`. Une reprise conserve l'émission existante. Avant scoring, le collecteur vérifie aussi le snapshot associé à chaque émission, son prix d'origine et le rejeu de ses 260 quantiles avec la recette figée. Les rapports successifs restent disponibles dans des dossiers datés. `ready_for_confirmation_review` demande une revue quand les effectifs et les seuils passent ; `publishable` reste faux. Une empreinte seule protège contre une modification accidentelle, pas contre un opérateur qui remplacerait simultanément le fichier et son reçu.

L'option `--score-only` permet de vérifier les émissions déjà archivées à tout moment, sans en créer. Elle a été exécutée sur les vraies données le 13 septembre 2026 à 16:10:54 UTC. Le rapport contient la prévision originale du 10 septembre et zéro cible mature pour chacun des 52 horizons. Rapport local : `prospective/20260913T161054755242Z/report.json`. L'automatisation inclut désormais cette archive vérifiée.

Le cron Railway Development remplace l'automatisation Codex initiale à 07:00 Europe/Paris. La [procédure Development](DEVELOPMENT_RESEARCH.md) décrit le worker, les buckets, la reprise et le budget. Le traitement cloud du 13 septembre à 19:40 UTC a réussi, avec vérification du rapport et du snapshot dans les deux buckets. Le suivi Codex a ensuite été supprimé. La commande locale reste disponible pour audit ; aucun rattrapage ne doit antidater une émission.

## Vérifications du 13 septembre

Avant publication, la suite Python complète a passé 242 tests avec PostgreSQL local. Les 159 tests frontend, TypeScript, lint, build Next.js et dbt debug/compile/build complet puis incrémental passent aussi. La correction LF/CRLF ajoute un test ; les 16 tests du collecteur et de son entrée cloud passent après correction. La CI GitHub du commit `b78f8a53` réussit ses trois jobs. Ces vérifications remplacent les résultats partiels ci-dessous pour l'état de livraison du code ; elles ne constituent pas une validation statistique du modèle.

La suite forecast exécutée après ajout des recettes passe 103 tests, avec 18 tests ignorés faute de configuration PostgreSQL ou de dépendances optionnelles. Les huit tests ajoutés ensuite pour le collecteur passent aussi, dont un parcours émission lundi, reprise mardi, conservation du snapshot et détection de modification. Total de 111 tests distincts réussis sur ces exécutions. Les 17 nouveaux tests couvrent notamment causalité, maturité, quantiles, snapshots figés et archives. Les tests du collecteur vérifient aussi le refus d'un snapshot modifié et la portée exacte de l'exception du 10 septembre.

Ruff, Black et `git diff --check` passent sur les changements. Les 42 entrées des deux inventaires d'archives copiées correspondent à leurs empreintes. L'appel réel du collecteur ce dimanche retourne `not_due`, sans émission antidatée. Le premier lancement planifié du lundi a échoué sur Frankfurter ; sa reprise réelle du 14 septembre a créé l'émission hebdomadaire. Les preuves figurent dans [DEVELOPMENT_RESEARCH.md](DEVELOPMENT_RESEARCH.md). Aucun test PostgreSQL ignoré, test de fixture ou contrôle de code n'est compté comme preuve de qualité prédictive.

## Conditions encore nécessaires

Une confirmation concluante doit précéder l'intégration de la recette au format d'artefact accepté par le registre de production. Le registre actuel accepte seulement les recettes initiales. Il faudra ensuite vérifier ce modèle concret en Development, relire le coût complet et les sauvegardes, puis préparer la promotion et la livraison selon [RELEASE.md](RELEASE.md). Aucun de ces contrôles ne peut être remplacé par les tests d'une fixture.

La règle minimale de 104 observations est appliquée au rapport local de cette collecte. Elle ne modifie pas silencieusement le validateur de promotion des autres recettes.
