@echo off
setlocal

echo ==========================================
echo Running ALL Tests
echo ==========================================

echo.
echo [1/4] Checking the locked Python workspace...
echo ------------------------------------------
call uv lock --check
if errorlevel 1 goto :failure

call uv sync --locked --package raw-ingest --extra dev
if errorlevel 1 goto :failure

echo.
echo [2/4] Running raw-ingest backend tests...
echo ------------------------------------------
call uv run --locked --package raw-ingest --extra dev pytest dbx_workflow/tests
if errorlevel 1 goto :failure

echo.
echo [3/4] Running frontend tests and lint...
echo ------------------------------------------
pushd app
if errorlevel 1 goto :failure
call npm test -- --ci --watchAll=false --runInBand
if errorlevel 1 goto :failure_from_app
call npm run lint
if errorlevel 1 goto :failure_from_app
popd

echo.
echo [4/4] Running Data Transformations Tests (DBT dev)...
echo ------------------------------------------
call uv run --locked --package raw-ingest dbt test --target dev --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
if errorlevel 1 goto :failure

echo.
echo ==========================================
echo [SUCCESS] All tests passed!
echo ==========================================
endlocal & exit /b 0

:failure_from_app
set "EXIT_CODE=%ERRORLEVEL%"
popd
goto :failure

:failure
if not defined EXIT_CODE set "EXIT_CODE=%ERRORLEVEL%"
echo [FAIL] Validation failed with exit code %EXIT_CODE%.
endlocal & exit /b %EXIT_CODE%
