# Livraison Forecast V1

Procédure préparée pour [Livrer la V1 sur Railway et vérifier sa première exécution](https://github.com/DOX69/Bitcoin-analysis/issues/89). Livraison non exécutée.

## Prérequis

Le propriétaire valide le dossier [INTEGRATION.md](INTEGRATION.md), les résultats Development, la configuration finale et son coût. Un seul modèle peut être publié après confirmation prospective suffisante et décision manuelle. Le benchmark actuel n'identifie aucun modèle probabiliste admissible. Conserver le forecast désactivé tant que ces conditions manquent.

## Configuration à examiner

Réutiliser les services web, PostgreSQL et cron existants. Aucun second ordonnanceur. Installer l'extra Python `forecast` au build du cron, puis conserver son entrée `raw-ingest`. Le hook ne s'active qu'avec sa configuration explicite. Les variables S3 et l'URL PostgreSQL restent côté serveur.

Pour le cron activé, build `uv sync --locked --all-packages --extra forecast`, puis démarrage `uv run --locked --package raw-ingest --no-sync raw-ingest`. Le mode `--no-sync` évite de retirer les dépendances forecast avant le calcul. Le passage dbt du cron activé doit aussi conserver cet environnement installé.

Créer un bucket privé avec séparation Development/production et une copie indépendante des artefacts. Présenter les coûts de stockage, sauvegarde et transfert avec le coût CPU/RAM avant activation. Le mécanisme indépendant [BACKUP.md](BACKUP.md) a été restauré dans Development ; le configurer avec des accès et buckets propres à la production avant toute activation. Le scénario de coût Development figure dans [COST.md](COST.md).

## Séquence

1. Identifier le commit livré, le modèle validé, ses empreintes et la version de rollback. Vérifier les tests et la compatibilité de l'environnement Python figé.
2. Sauvegarder PostgreSQL et les artefacts. Vérifier que cette sauvegarde se restaure ailleurs sans accès aux ressources originales.
3. Appliquer `001_storage.up.sql`, puis `002_jobs.up.sql` dans l'environnement explicitement ciblé. Vérifier les tables, contraintes et verrous sans reconstruire les tables dbt.
4. Charger le bundle validé sous une clé immuable, relire les fichiers, vérifier leurs empreintes et effectuer le calcul de contrôle. Enregistrer la version avant son activation manuelle.
5. Déployer le web et le cron issus du même commit. Vérifier l'API sans secrets, puis activer le hook avec le relevé complet de coût du mois. Ne pas modifier une limite globale susceptible d'arrêter le site ou sa base.
6. Vérifier le premier lundi admissible, ou son unique reprise du mardi. Relever l'heure UTC réelle, l'origine, les 52 cibles, la version et les journaux. Ne pas antidater une émission pour terminer la livraison.
7. Vérifier le rendu USD/EUR/CHF et les dates d'origine depuis l'API et le navigateur. Rejouer le lot et constater l'absence de doublon.
8. Observer la consommation marginale, compléter le dossier puis fermer le ticket et la carte seulement si tous leurs critères sont atteints.

## Retour arrière

Désactiver le hook forecast pour suspendre ses nouveaux calculs, sans arrêter l'ingestion. Revenir à la version précédente du web si nécessaire. Un rollback de modèle revérifie les artefacts et refuse une version retirée. Les émissions déjà publiées restent inchangées ; invalider explicitement une émission erronée conserve sa trace.

Les migrations descendantes suppriment l'historique. Elles servent au test de réversibilité sur base jetable et ne constituent pas la procédure normale de rollback en production. Restaurer une sauvegarde validée uniquement lors d'une récupération explicitement décidée.

## Suivi

Le propriétaire examine le rapport mensuel de calibration et le coût total. Un cycle de candidats trimestriel reste borné à deux recettes, exécutées successivement, sans promotion automatique. La référence holdout reste hors du registre des candidats. Consigner les horizons encore immatures. Les commandes et contrats de travail figurent dans [OPERATIONS.md](OPERATIONS.md).
