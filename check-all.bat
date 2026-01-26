@echo off
setlocal

echo ==========================================
echo Running ALL Tests
echo ==========================================

echo.
echo [1/2] Running Backend Tests (pytest)...
echo ------------------------------------------
call uv run pytest
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Backend tests failed!
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Running Frontend Tests (npm test)...
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
echo ==========================================
echo [SUCCESS] All tests passed!
echo ==========================================
endlocal
