@echo off
REM =====================================================================
REM  LucasChessR - LAN multiplayer extension pack - UNINSTALLER
REM
REM  Usage:
REM      uninstall.bat "C:\path\to\LucasChessR"
REM
REM  Removes only the files that install.bat added:
REM      bin\Code\LAN\                 (the whole folder)
REM      bin\Code\Menus\PlayMenu.py    (restores the backup when present)
REM =====================================================================
setlocal

set "PACK=%~dp0"
set "BASE="

if not "%~1"=="" (
    set "BASE=%~1"
) else (
    if exist "%PACK%..\bin\Code" set "BASE=%PACK%.."
    if not defined BASE if exist "%PACK%..\LucasChessR\bin\Code" set "BASE=%PACK%..\LucasChessR"
    if not defined BASE if exist "%PACK%..\..\bin\Code" set "BASE=%PACK%..\.."
)

if not defined BASE (
    echo [ERROR] LucasChessR folder not found.
    echo.
    echo Run:  uninstall.bat "C:\Games\LucasChessR"
    echo.
    pause
    exit /b 1
)

set "DST=%BASE%\bin\Code"

echo.
echo  LucasChessR LAN extension pack - uninstall
echo  ------------------------------------------
echo  Target : %DST%
echo.

if not exist "%DST%" (
    echo [ERROR] Folder not found: %DST%
    pause
    exit /b 1
)

echo  This will delete:
echo     %DST%\LAN
echo     %DST%\Menus\PlayMenu.py ^(restoring the backup if it exists^)
echo.
set "ANSWER="
set /P "ANSWER=Continue? [y/N] "
if /I not "%ANSWER%"=="y" (
    echo Cancelled.
    pause
    exit /b 0
)

if exist "%DST%\Menus\PlayMenu.py.lanbak" (
    move /Y "%DST%\Menus\PlayMenu.py.lanbak" "%DST%\Menus\PlayMenu.py" >nul
    echo [OK] Original PlayMenu.py restored.
) else (
    if exist "%DST%\Menus\PlayMenu.py" (
        del /Q "%DST%\Menus\PlayMenu.py"
        echo [OK] PlayMenu.py removed, the original PlayMenu.pyc is used again.
    )
)

if exist "%DST%\LAN" (
    rmdir /S /Q "%DST%\LAN"
    echo [OK] Folder LAN removed.
)

echo.
echo [OK] Uninstalled.
echo.
pause
endlocal
