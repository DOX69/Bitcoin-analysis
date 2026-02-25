@echo off
setlocal

echo ==========================================
echo Running ALL Tests
echo ==========================================

echo.
echo [1/3] Running Backend Tests (pytest)...
echo ------------------------------------------
call uv run pytest
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Backend tests failed!
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Running Frontend Tests (npm test)...
echo ------------------------------------------
cd app
call npm test -- --watchAll=false
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Frontend tests failed!
    cd ..
    exit /b %ERRORLEVEL%
)
cd ..

echo.
echo [3/3] Running Data Transformations Tests (DBT)...
echo ------------------------------------------
cd dbt_silver_gold
echo Running dev tests...
call uv run dbt test -t dev
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] DBT DEV tests failed!
    cd ..
    exit /b %ERRORLEVEL%
)

echo Running prod tests...
call uv run dbt test -t prod
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] DBT PROD tests failed!
    cd ..
    exit /b %ERRORLEVEL%
)
cd ..

echo.
echo ==========================================
echo [SUCCESS] All tests passed!
echo ==========================================
endlocal
