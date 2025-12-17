@echo off
setlocal

REM Standalone launcher for .fnw files
REM Usage: fnw_open.cmd <path_to_file.fnw>

if "%~1"=="" (
    echo Usage: %~nx0 ^<file.fnw^>
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM Run from the FuncNodes project directory so `uv run` uses the local code.
if exist "%PROJECT_DIR%\\pyproject.toml" (
    pushd "%PROJECT_DIR%" >nul 2>nul
)

REM Keep the launcher simple and reliable: avoid subprocess-monitor indirection.
set "FNW_FILE=%~1"
set "ARGS=--debug standalone"
echo Running: funcnodes %ARGS% "%FNW_FILE%"
REM Prefer uv if available; otherwise fall back to installed entrypoints.
where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Running: uv run funcnodes %ARGS% "%FNW_FILE%"
    uv run funcnodes %ARGS% "%FNW_FILE%"
    goto :cleanup
)

where uvx >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Running: uvx funcnodes %ARGS% "%FNW_FILE%"
    uvx funcnodes %ARGS% "%FNW_FILE%"
    goto :cleanup
)

where funcnodes >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Running: funcnodes %ARGS% "%FNW_FILE%"
    funcnodes %ARGS% "%FNW_FILE%"
    goto :cleanup
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Running: py -3 -m funcnodes %ARGS% "%FNW_FILE%"
    py -3 -m funcnodes %ARGS% "%FNW_FILE%"
    goto :cleanup
)

echo Running: python -m funcnodes %ARGS% "%FNW_FILE%"
python -m funcnodes %ARGS% "%FNW_FILE%"

:cleanup
popd >nul 2>nul
cmd /k
endlocal
