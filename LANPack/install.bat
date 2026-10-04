@echo off
REM =====================================================================
REM  LucasChessR - LAN multiplayer extension pack - INSTALLER
REM
REM  Usage:
REM      install.bat "C:\path\to\LucasChessR"
REM
REM  With no argument the script looks for the LucasChessR folder around
REM  its own location.
REM
REM  Nothing of the original program is modified: only new files are added.
REM =====================================================================
setlocal

set "PACK=%~dp0"
set "SRC=%PACK%Code"
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
    echo Put this folder inside LucasChessR or run:
    echo     install.bat "C:\Games\LucasChessR"
    echo.
    pause
    exit /b 1
)

set "DST=%BASE%\bin\Code"

echo.
echo  LucasChessR LAN extension pack - install
echo  ----------------------------------------
echo  Source : %SRC%
echo  Target : %DST%
echo.

if not exist "%SRC%\LAN\__init__.py" (
    echo [ERROR] The pack files are not next to this script.
    pause
    exit /b 1
)

if not exist "%DST%" (
    echo [ERROR] Folder not found: %DST%
    pause
    exit /b 1
)

REM --------------- source installation? patch PlayMenu.py ----------------
if exist "%DST%\Menus\PlayMenu.py" (
    if not exist "%DST%\Menus\PlayMenu.py.lanbak" (
        echo [INFO] Source installation detected: patching PlayMenu.py
        copy /Y "%DST%\Menus\PlayMenu.py" "%DST%\Menus\PlayMenu.py.lanbak" >nul
        echo.>>"%DST%\Menus\PlayMenu.py"
        echo # --- LucasChessR LAN extension pack (start) --->>"%DST%\Menus\PlayMenu.py"
        echo import sys as _lan_sys>>"%DST%\Menus\PlayMenu.py"
        echo from Code.LAN.hook import install as _lan_install>>"%DST%\Menus\PlayMenu.py"
        echo _lan_install(_lan_sys.modules[__name__])>>"%DST%\Menus\PlayMenu.py"
        echo # --- LucasChessR LAN extension pack (end) --->>"%DST%\Menus\PlayMenu.py"
    )
) else (
    if not exist "%DST%\Menus\PlayMenu.pyc" (
        echo [WARNING] Neither PlayMenu.py nor PlayMenu.pyc were found.
        echo           The menu entry may not appear.
    )
)

REM --------------- copy the new files -----------------------------------
xcopy /Y /E /I /Q "%SRC%\LAN" "%DST%\LAN" >nul
if not exist "%DST%\Menus\PlayMenu.py.lanbak" (
    copy /Y "%SRC%\Menus\PlayMenu.py" "%DST%\Menus\PlayMenu.py" >nul
)

echo [OK] Files copied.

if exist "%BASE%\bin\Code\LAN\manager.py" (
    echo.
    echo [OK] Installed. Start LucasChessR and open the "Play" menu:
    echo      a new entry "Play on the local network (LAN)" is available.
) else (
    echo [ERROR] The files could not be copied.
)

echo.
pause
endlocal
