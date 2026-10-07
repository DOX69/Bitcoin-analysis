# Prototype des projections Bitcoin

Le propriétaire demande une intégration minimale au dashboard existant : checkbox, modèle recommandé par défaut, liste de modèles et explication courte dans un « i ». Les premiers prototypes de journal et de comparaison ont été rejetés.

Les variantes utilisent DashboardClient et son véritable graphique Chart.js. Contrôles historiques, indicateurs, devises et statistiques restent en place. Le mode développement fournit des données de démonstration sans PostgreSQL. Le dashboard normal conserve son chargement habituel.

Le prototype A validé est la seule version conservée : contrôles au-dessus, médiane dorée pointillée, contours ocre et bande chaude translucide.

Ouvrir le serveur local déjà actif : http://localhost:3000/dashboard?variant=A, puis cocher Forecast. Le prototype est disponible uniquement en développement.

Les projections comportent 52 valeurs hebdomadaires simulées par émission. Modèle recommandé et alternative servent à comparer l’interface ; aucune recette n’est promue. Seule la dernière prévision du modèle choisi est sélectionnée par défaut. La liste multisélection propose au maximum les trois dernières prévisions disponibles et permet de les superposer à leurs dates d’origine. Changer de modèle rétablit la dernière prévision seule. Une période passée n’ajoute pas de projection plus récente. Cette limite d’affichage ne change pas la conservation des anciennes prévisions en base.

Les valeurs sont présentées comme estimation basse, médiane et estimation haute. Aucun tableau d’émissions ni texte statistique n’est ajouté au produit.

Validation : TypeScript, ESLint ciblé, 16 tests existants du dashboard et du graphique, contrôles navigateur du prototype, sélecteur, popover et absence de débordement de page à 320, 390 et 768 px. Captures desktop et mobile dans le comparatif local temporaire. Le propriétaire a validé cette version A.
