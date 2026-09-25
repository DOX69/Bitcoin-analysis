# Audit en lecture seule du suivi hebdomadaire

La collecte et le modèle ont des critères distincts : un pipeline exécuté avec
copies vérifiées ne démontre pas une qualité prédictive. Le suivi de l'hybride
reste séparé des résultats quotidiens Ridge et des autres expériences.

## État documenté au 18 septembre 2026

`DEVELOPMENT_RESEARCH.md` documente le premier scoring du 14 septembre à
05:24 UTC, après la maturité de la cible du dimanche 13 septembre. Les journaux
Railway du 18 septembre à 05:04:35 UTC, déploiement
`d0abbfae-001e-4fa7-acee-0678f158b2ca`, indiquent `status=completed`, deux
émissions, une cible mature et `independent_copy_verified=True`.

Rapport identifié :
`development/research/hybrid-v1/reports/20260918T050433878123Z.json`.

Cela établit la trace d'exécution, pas les valeurs numériques du score. Le JSON
privé n'a pas été relu pendant la préparation de ce complément : l'accès OAuth
Railway expose les noms des variables, pas leurs valeurs. Aucun chiffre de MAE,
WIS ou couverture réel n'est donc ajouté ici. La mention « aucun score
prospectif » dans le compte rendu du 10 septembre est un état historique.

## Statuts explicites et compatibilité

Le rapport et chaque horizon exposent désormais `validation_status` :

| Statut | Signification |
|---|---|
| `insufficient_evidence` | Moins de 104 origines matures ou moins de deux blocs complets contigus pour au moins un horizon concerné. |
| `outside_guardrails` | Effectifs suffisants, mais au moins un garde-fou n'est pas satisfait. |
| `guardrails_met` | Effectifs et garde-fous satisfaits ; revue humaine encore nécessaire. |

Les booléens existants sont conservés. `guardrails_passed` décrit seulement le
passage numérique des seuils : à n=1, une couverture vaut 0 ou 1 et ne permet
pas de conclure sur la calibration. `ready_for_confirmation_review` reste la
conjonction des effectifs et des seuils. `publishable` reste toujours faux.
Les 104 observations ne prouvent pas l'indépendance ; les résultats par blocs
et les différences de régime doivent encore être examinés.

Les seuils ne changent pas : MAE au plus égale à 1,05 fois la référence centrale,
couverture 50 % entre 0,4 et 0,6, couverture 80 % entre 0,7 et 0,9, pour les
52 horizons. Les sources de la recette figée et ses empreintes ne changent pas.
Les nouveaux rapports incluent aussi `issued_at` et `origin_close` dans chaque
observation, pour tracer la référence figée malgré les révisions de source.

## Export d'un rapport cloud existant

Depuis un environnement autorisé à lire les deux buckets Development, utiliser
les variables S3 de la procédure `DEVELOPMENT_RESEARCH.md`. Des permissions de
lecture d'objets suffisent ; aucune connexion PostgreSQL, écriture S3,
réparation de copie, émission, entraînement ou relance du scoring n'est effectuée.

```bash
uv run --locked --extra forecast python -m forecast.research_audit \
  --config forecast/development-config.json \
  --report-key development/research/hybrid-v1/reports/20260918T050433878123Z.json \
  --format json
```

Le JSON conserve la précision des nombres archivés et expose les observations
individuelles : origine, cible, prix observé, cinq quantiles, MAE du modèle et de
la référence, WIS et inclusions dans les bandes. Il présente les 52 horizons,
y compris ceux sans observation. `--format markdown` produit un tableau de
synthèse arrondi, dont les couvertures sont des proportions entre 0 et 1.

Le lecteur exige un rapport de l'hybride connu, compare octet pour octet sa
copie indépendante et contrôle la cohérence entre agrégats et observations.
Il relit également le snapshot et sa copie, avec l'empreinte référencée par le
rapport. Il refuse une copie absente, différente ou un snapshot hors namespace.
Le journal des prochaines collectes inclut le statut et `report_sha256`.

Pour épingler une empreinte préalablement obtenue dans une source de confiance,
ajouter `--expected-sha256 <empreinte>`. Sans cette option, le résultat indique
`expected_checksum_verified=false` : deux copies identiques ne prouvent pas
qu'elles n'ont pas été modifiées ensemble. Cet audit n'est pas un rejeu des
émissions et ne certifie pas la justesse de la source des prix.

## Fichiers déjà téléchargés

```bash
uv run --locked --extra forecast python -m forecast.research_audit \
  --report /chemin/rapport-primaire.json \
  --copy /chemin/rapport-copie-independante.json \
  --format markdown
```

Les fichiers doivent être distincts et provenir des deux archives. Ce mode
contrôle les deux rapports uniquement (`snapshot_copy_verified=false`). Les
anciens rapports restent lisibles : les statuts sont dérivés avec le protocole
actuel inchangé, et les métadonnées absentes restent `null`, sans inventer une
date d'émission ou un prix d'origine. Aucun fichier source n'est modifié.

Auditer UN rapport daté à la fois : additionner ses observations à celles du
rapport du lendemain compterait plusieurs fois les mêmes couples origine/horizon.
En cas de révision de prix, conserver les deux rapports et leurs empreintes,
comparer la même origine/cible et garder la prévision initiale inchangée.

## Critères de revue de ce complément

- Audit en lecture seule, rejet d'une copie ou d'un checksum divergent.
- Compatibilité des anciens rapports, séparation stricte du modèle quotidien.
- Zéro ou un point reste insuffisant ; rescoring et révision n'augmentent pas n.
- Seuils de qualité et de blocs inchangés, y compris aux bornes.
- Aucune modification des prévisions, de la recette, du registre ou de la promotion.

Ce complément peut être revu comme une amélioration logicielle. Il ne résout
pas l'échec historique sur 46 horizons de stress et ne clôt pas l'issue #92.
