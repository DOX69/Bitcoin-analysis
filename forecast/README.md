# Benchmark local du forecast Bitcoin

Le runner compare trois candidats sur le même snapshot hebdomadaire :

- `price_unchanged`, prix observé maintenu sur les 52 horizons ;
- `gaussian_random_walk`, référence probabiliste fondée sur les rendements log historiques ;
- `lightgbm_quantile`, 52 horizons directs et cinq quantiles.

Le runner agrège les lignes quotidiennes en semaines ISO et refuse les semaines incomplètes, manquantes ou dupliquées. Il réserve 60 % des semaines à l'apprentissage, 20 % à la calibration, puis teste les origines dont les 52 cibles futures sont disponibles. Les fenêtres de variables peuvent se chevaucher entre origines, car elles ne contiennent que des valeurs connues à l'origine. Les modèles n'utilisent aucune cible située après la fin d'apprentissage.

Les mesures incluent MAE, RMSE, perte pinball, couverture des bandes 50 % et 80 %, largeur des intervalles, durée, pic RSS, threads configurés, taille modèle plus calibrateur et coût Railway équivalent. Ce dernier est une estimation locale au tarif CPU/RAM du ticket budget, pas une dépense réelle.

## Rejouer la mesure

```powershell
uv run --locked --extra benchmark python -m forecast.benchmark snapshot `
  --base-url https://bitcoin-web-development.up.railway.app `
  --start-date 2015-07-20 `
  --end-date 2026-09-06 `
  --output C:\Users\<user>\AppData\Local\Temp\bitcoin-forecast\weekly-snapshot.csv

uv run --locked --extra benchmark python -m forecast.benchmark benchmark `
  --snapshot C:\Users\<user>\AppData\Local\Temp\bitcoin-forecast\weekly-snapshot.csv `
  --output C:\Users\<user>\AppData\Local\Temp\bitcoin-forecast\benchmark.json
```

Le snapshot et le rapport restent locaux. Le dernier jour peut apparaître dans le fetch quotidien sans produire de semaine hebdomadaire tant que son dimanche n'est pas disponible.
