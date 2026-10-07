# Conditions de publication du forecast

La seule piste de confirmation prospective active est `lightgbm_quantile`, hebdomadaire, sur 52 horizons et cinq quantiles. Elle conserve `publishable=false` pour la promotion d'un modèle validé. La publication expérimentale à six mois autorisée le 7 octobre utilise un schéma séparé et un affichage explicitement expérimental, selon [EXPERIMENTAL_RELEASE.md](EXPERIMENTAL_RELEASE.md). L'ancien aperçu quotidien Ridge est retiré.

Le benchmark historique et les tests de fixtures ne prouvent pas la qualité prédictive future. Gaussian random walk reste un comparateur ; le prix inchangé et le random walk sans dérive restent les baselines d'évaluation. Aucune recalibration n'est appliquée.

Avant promotion, il faut :

- Une recette, un snapshot, des paramètres et des versions numériques figés, avec artefacts vérifiés et copie indépendante.
- Au moins 104 origines matures par horizon et deux blocs temporels contigus complets, puis une revue de la dépendance des erreurs, des scores et de la couverture.
- Un holdout final réellement vierge, ou son indisponibilité explicite accompagnée de confirmation prospective. Un historique déjà examiné ne devient pas un test final.
- Une vérification du modèle concret en Development, du coût complet, des sauvegardes et du rejeu, puis une décision manuelle selon [RELEASE.md](RELEASE.md).

La collecte n'antidate aucune émission : lundi UTC, avec reprise mardi seulement. Un signal `ready_for_confirmation_review` demande une revue ; il n'active aucun modèle.

Le dernier contrôle consigné dans les documents avant ce nettoyage date du 2 octobre 2026 : rapport `development/research/lightgbm-v1/reports/20261002T094130228276Z.json`, zéro émission, zéro cible mature, copie indépendante vérifiée. Ce constat daté ne décrit pas l'état cloud actuel. Les rapports et preuves antérieurs restent dans [l'archive](ARCHIVE.md).

Voir [DEVELOPMENT_RESEARCH.md](DEVELOPMENT_RESEARCH.md) pour l'exploitation et [README.md](README.md) pour les contrats de données et de mesure.
