# Validation de l'intégration Forecast V1

Vérification du 9 septembre 2026 pour [Valider la V1 de bout en bout et son coût en Development](https://github.com/DOX69/Bitcoin-analysis/issues/88).

## Portée

Les premiers essais ci-dessous concernent une instance locale et des données synthétiques. Une seconde validation utilise PostgreSQL 18 et deux buckets privés Railway Development ; ses résultats figurent dans [DEVELOPMENT.md](DEVELOPMENT.md). Aucune fixture ne constitue une preuve prospective.

La seconde validation crée les buckets Development d'artefacts et de sauvegarde, deux bases isolées, applique les migrations additives après sauvegarde à la base Development et déploie le web. La production reste inchangée. Les sauvegardes natives exigent Pro ; une sauvegarde indépendante a ensuite été implémentée, restaurée et intégrée au cron quotidien, voir [BACKUP.md](BACKUP.md).

## Parcours vérifié

Le test `test_integration.py` entraîne un gaussien sur une série synthétique, sauvegarde son manifeste et son état, recharge le modèle, émet 52 horizons, persiste l'émission puis la rejoue. PostgreSQL conserve un seul enregistrement, identique au payload initial, avec les conversions EUR/CHF figées.

Pour le navigateur, trois émissions synthétiques datées du 24 août, du 31 août et du 7 septembre 2026 sont persistées dans une autre base locale. Next.js les lit par le véritable endpoint `/api/forecast`. Le nom de version `synthetic-browser-fixture` identifie leur usage. L'historique dbt de démonstration est volontairement distinct et ancien ; l'écart entre sa fin et les projections n'est pas une prévision reconstruite depuis le cours courant.

Une reconstruction dbt complète après insertion conserve les trois émissions. Les neuf modèles et 87 tests dbt passent, comme lors du premier build et du rejeu incrémental. Les 90 tests existants d'ingestion passent avant intégration du nouveau hook forecast.

L'application passe 159 tests dans 24 suites, TypeScript, ESLint et le build Next.js. Chrome vérifie le bureau et un viewport mobile réel de 391 × 844 pixels sans débordement horizontal, la sélection de trois émissions au clavier, le taux EUR figé à 0,92, l'échelle logarithmique et une période passée sans émission future. Aucune erreur console observée.

Captures locales hors dépôt : `%TEMP%/forecast-v1-desktop.png`, `%TEMP%/forecast-v1-mobile-390.png`, `%TEMP%/forecast-v1-mobile-selection.png`, `%TEMP%/forecast-v1-mobile-eur-log.png`, `%TEMP%/forecast-v1-past-period.png`. Les deux captures de sélection et de devise utilisent un viewport de 520 pixels ; le nom `mobile-390` correspond aux 391 pixels CSS mesurés.

## Rejouer les tests PostgreSQL

Les bases sont jetables, locales et réservées aux tests. Les fixtures refusent un hôte distant ou un nom de base non autorisé. Ne jamais leur fournir une URL Railway.

```powershell
$env:FORECAST_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55432/forecast_test'
$env:FORECAST_JOBS_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55432/forecast_jobs_test'
$env:FORECAST_INTEGRATION_DATABASE_URL='postgresql://postgres@127.0.0.1:55432/forecast_integration_test'
uv run --locked --extra dev --extra forecast pytest forecast
```

La CI prépare ces bases sur PostgreSQL 16. Les tests de l'application incluent séparément TypeScript, ESLint, Jest et le build Next.js.

La suite combinée `pytest forecast dbx_workflow/tests -q` passe 163 tests en 169 secondes. Deux régressions ajoutées ensuite passent séparément : préservation des dépendances pendant dbt et import du package installé sans chemin courant. Cela couvre 165 tests Python distincts. Ruff, vérification du lock et vérification du diff passent. Le wheel Python se construit ; `forecast` est désormais inclus dans le package afin que l'entrée console du cron puisse importer son superviseur.

## Coût restant à établir

Tarifs consultés le 9 septembre 2026 : CPU 0,00000772 USD par vCPU-seconde, RAM 0,00000386 USD par Go-seconde, stockage objet 0,015 USD par Go-mois, sortie réseau des services 0,05 USD par Go. La sortie des buckets est gratuite. [Tarifs Railway](https://railway.com/pricing).

À titre de borne de calcul, 31 passages mensuels utilisant chacun deux vCPU et quatre Go pendant cinq minutes représentent environ 0,287 USD. Trois candidats trimestriels de 30 minutes aux mêmes ressources représentent environ 0,056 USD par mois en moyenne. Ce calcul ne mesure aucune consommation Railway et ne constitue pas un budget complet.

Ajouter le stockage PostgreSQL marginal, les artefacts conservés, les copies indépendantes, les sauvegardes, les transferts et le coût des revues. Mesurer le volume et le transfert réels des versions publiées. La suspension à cinq USD doit utiliser ce total mesuré ou projeté, pas seulement le temps CPU. Le plafond forecast reste dix USD par mois.

## Limites de livraison

- Le scénario complet [COST.md](COST.md) est une projection conditionnelle ; surveiller les allocations, la croissance des copies et la facturation retardée.
- Confirmation prospective suffisante et promotion manuelle d'un modèle admissible. Le dernier benchmark documenté dans [VALIDATION.md](VALIDATION.md) n'en fournit aucun.

La validation logicielle Development est distincte de la livraison : l'absence de modèle admissible bloque cette dernière. Les fixtures ne remplacent pas la confirmation prospective.
