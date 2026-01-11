# Bitcoin-analysis
Bitcoin chart and analysis
# create requirement.txt 
```bash
uv pip compile pyproject.toml -o requirements.txt
```
# test rapide :
```bash
# 1. Simuler ce que le workflow va faire
cd dbx_raw_ingest

# 2. Supprimer vos anciens packages (nettoyer)
pip uninstall -r requirements.txt -y

# 3. Réinstaller depuis le nouveau requirements.txt
pip install -r requirements.txt

# 4. Tester les 3 commandes que le workflow utilise
databricks --version
echo "✅ Step 1: databricks CLI installed"

databricks  databricks workspace list / -p PROD
echo "✅ Step 2: Authentication works"

databricks bundle validate --target prod --profile PROD --var="pauseStatus=UNPAUSED"
echo "✅ Step 3: Bundle validation works"

# Si tout est ✅ → Prêt à pusher sur GitHub

```

