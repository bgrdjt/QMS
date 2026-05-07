@echo off
REM ================================================================
REM  QMS Document Management System — Windows Installer v1.3c
REM  Explicitly searches Python314 and Launcher locations
REM  Run as Administrator
REM ================================================================

title QMS DMS — Installer v1.3c
color 0B
setlocal EnableDelayedExpansion

echo.
echo  ==============================================================
echo   QMS Document Management System  v1.3c
echo   ISO 13485 / ISO 9001 / ISO 14971 / FDA QMSR
echo  ==============================================================
echo.

SET INSTALL_ROOT=%~dp0
IF "%INSTALL_ROOT:~-1%"=="\" SET INSTALL_ROOT=%INSTALL_ROOT:~0,-1%
echo  Installer location: %INSTALL_ROOT%
echo.

REM ================================================================
REM  STEP 1 - Find Python
REM  Explicitly checks Python314, Python313, all 3xx versions,
REM  the py launcher, and PATH — skips Store stub
REM ================================================================
echo [1/8] Locating Python...
echo.

SET PYTHON_EXE=
SET PYTHON_FOUND=0

REM ----------------------------------------------------------------
REM  Check all known Python version folders explicitly
REM  Covers: Python314, Python313, Python312, Python311, Python310,
REM          Python39, Python38 in both AppData and Program Files
REM ----------------------------------------------------------------
FOR %%V IN (Python314 Python313 Python312 Python311 Python310 Python39 Python38) DO (
    IF "!PYTHON_FOUND!"=="0" (
        REM Per-user install location (most common for non-admin installs)
        SET TRY1=%LOCALAPPDATA%\Programs\Python\%%V\python.exe
        IF EXIST "!TRY1!" (
            "!TRY1!" --version >nul 2>&1
            IF NOT ERRORLEVEL 1 (
                SET PYTHON_EXE=!TRY1!
                SET PYTHON_FOUND=1
                echo   Found: !TRY1!
            )
        )
    )
    IF "!PYTHON_FOUND!"=="0" (
        REM System-wide install (Program Files)
        SET TRY2=C:\Program Files\%%V\python.exe
        IF EXIST "!TRY2!" (
            "!TRY2!" --version >nul 2>&1
            IF NOT ERRORLEVEL 1 (
                SET PYTHON_EXE=!TRY2!
                SET PYTHON_FOUND=1
                echo   Found: !TRY2!
            )
        )
    )
    IF "!PYTHON_FOUND!"=="0" (
        REM Root of C: (older installs)
        SET TRY3=C:\%%V\python.exe
        IF EXIST "!TRY3!" (
            "!TRY3!" --version >nul 2>&1
            IF NOT ERRORLEVEL 1 (
                SET PYTHON_EXE=!TRY3!
                SET PYTHON_FOUND=1
                echo   Found: !TRY3!
            )
        )
    )
)

REM ----------------------------------------------------------------
REM  Check the Python Launcher (py.exe) as fallback
REM  The launcher is usually at C:\Windows\py.exe
REM ----------------------------------------------------------------
IF "!PYTHON_FOUND!"=="0" (
    IF EXIST "C:\Windows\py.exe" (
        C:\Windows\py.exe --version >nul 2>&1
        IF NOT ERRORLEVEL 1 (
            SET PYTHON_EXE=C:\Windows\py.exe
            SET PYTHON_FOUND=1
            echo   Found Python Launcher: C:\Windows\py.exe
        )
    )
)

REM ----------------------------------------------------------------
REM  Check PATH-based commands, reject Store stub
REM ----------------------------------------------------------------
IF "!PYTHON_FOUND!"=="0" (
    FOR %%C IN (python python3) DO (
        IF "!PYTHON_FOUND!"=="0" (
            %%C --version >nul 2>&1
            IF NOT ERRORLEVEL 1 (
                FOR /F "usebackq delims=" %%P IN (`where %%C 2^>nul`) DO (
                    IF "!PYTHON_FOUND!"=="0" (
                        echo %%P | findstr /I "WindowsApps" >nul 2>&1
                        IF ERRORLEVEL 1 (
                            SET PYTHON_EXE=%%P
                            SET PYTHON_FOUND=1
                            echo   Found on PATH: %%P
                        ) ELSE (
                            echo   Skipping Store stub: %%P
                        )
                    )
                )
            )
        )
    )
)

REM ----------------------------------------------------------------
REM  If found but not on PATH, add it now for this session AND
REM  permanently so future CMD windows work too
REM ----------------------------------------------------------------
IF "!PYTHON_FOUND!"=="1" (
    FOR %%I IN ("!PYTHON_EXE!") DO SET PYTHON_DIR=%%~dpI
    REM Remove trailing backslash
    IF "!PYTHON_DIR:~-1!"=="\" SET PYTHON_DIR=!PYTHON_DIR:~0,-1!

    REM Add to current session immediately
    SET PATH=!PYTHON_DIR!;!PYTHON_DIR!\Scripts;!PATH!

    REM Add permanently (takes effect in new CMD windows)
    SETX PATH "!PYTHON_DIR!;!PYTHON_DIR!\Scripts;%PATH%" >nul 2>&1

    echo   Python directory added to PATH: !PYTHON_DIR!
)

REM ----------------------------------------------------------------
REM  Final failure message
REM ----------------------------------------------------------------
IF "!PYTHON_FOUND!"=="0" (
    echo.
    echo  ============================================================
    echo   PYTHON NOT FOUND.
    echo  ============================================================
    echo.
    echo   Python 3.14 was checked at:
    echo   %LOCALAPPDATA%\Programs\Python\Python314\python.exe
    echo.
    echo   If Python is installed somewhere else, run this command
    echo   in CMD (adjust the path to match your install):
    echo.
    echo   SETX PATH "C:\path\to\python;C:\path\to\python\Scripts;%%PATH%%"
    echo.
    echo   Then close this window, open a new CMD, confirm:
    echo     python --version
    echo   Then re-run install.bat
    echo.
    echo   Or reinstall Python from https://python.org/downloads
    echo   and check "Add python.exe to PATH" on the first screen.
    echo.
    pause
    exit /b 1
)

FOR /F "usebackq tokens=*" %%V IN (`"!PYTHON_EXE!" --version 2^>^&1`) DO SET PY_VER=%%V
echo.
echo   Python: !PY_VER!
echo   Path:   !PYTHON_EXE!
echo   OK
echo.

SET PIP_CMD="!PYTHON_EXE!" -m pip

REM ================================================================
REM  STEP 2 - Find Node.js
REM ================================================================
echo [2/8] Locating Node.js...

SET NODE_FOUND=0
node --version >nul 2>&1
IF NOT ERRORLEVEL 1 (
    SET NODE_FOUND=1
    FOR /F "usebackq tokens=*" %%V IN (`node --version 2^>^&1`) DO echo   Node.js %%V
)

IF "!NODE_FOUND!"=="0" (
    FOR %%F IN (
        "C:\Program Files\nodejs\node.exe"
        "C:\Program Files (x86)\nodejs\node.exe"
    ) DO (
        IF "!NODE_FOUND!"=="0" IF EXIST %%F (
            %%F --version >nul 2>&1
            IF NOT ERRORLEVEL 1 (
                SET NODE_FOUND=1
                FOR %%I IN (%%F) DO SET ND=%%~dpI
                SET ND=!ND:~0,-1!
                SET PATH=!ND!;!PATH!
                echo   Found: %%F
            )
        )
    )
)

IF "!NODE_FOUND!"=="0" (
    echo.
    echo   ERROR: Node.js not found.
    echo   Install from https://nodejs.org then re-run.
    echo.
    pause
    exit /b 1
)
echo   OK
echo.

REM ================================================================
REM  STEP 3 - Verify npm
REM ================================================================
echo [3/8] Verifying npm...
npm --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo   WARNING: npm not found. Reinstall Node.js.
) ELSE (
    FOR /F "usebackq tokens=*" %%V IN (`npm --version 2^>^&1`) DO echo   npm %%V
)
echo   OK
echo.

REM ================================================================
REM  STEP 4 - Install Python packages
REM ================================================================
echo [4/8] Installing Python packages...
echo   flask  flask-cors  requests  PyQt5  reportlab  pypdf
echo   (May take 1-3 minutes)
echo.

!PIP_CMD! install flask flask-cors requests PyQt5 reportlab pypdf ^
    --quiet --no-warn-script-location
IF ERRORLEVEL 1 (
    echo.
    echo   Some packages failed. Run this manually:
    echo   "!PYTHON_EXE!" -m pip install flask flask-cors requests PyQt5 reportlab pypdf
    echo.
    pause
) ELSE (
    echo   All packages installed successfully.
)
echo   OK
echo.

REM ================================================================
REM  STEP 5 - Install Node docx package
REM ================================================================
echo [5/8] Installing Node.js docx package...
npm install -g docx --silent >nul 2>&1
IF ERRORLEVEL 1 (
    echo   WARNING: Run manually:  npm install -g docx
) ELSE (
    echo   docx installed.
)
echo   OK
echo.

REM ================================================================
REM  STEP 6 - Verify QMS files and set environment variables
REM ================================================================
echo [6/8] Verifying QMS files...

SET APP_PATH=%INSTALL_ROOT%\app\qms_app.py
SET SERVER_PATH=%INSTALL_ROOT%\server\dms_server.py
SET FILES_OK=1

IF NOT EXIST "%APP_PATH%" (
    echo   NOT FOUND: %APP_PATH%
    SET FILES_OK=0
)
IF NOT EXIST "%SERVER_PATH%" (
    echo   NOT FOUND: %SERVER_PATH%
    SET FILES_OK=0
)

IF "!FILES_OK!"=="1" (
    SETX QMS_APP_PATH    "%APP_PATH%"    >nul 2>&1
    SETX QMS_SERVER_PATH "%SERVER_PATH%" >nul 2>&1
    echo   QMS_APP_PATH    = %APP_PATH%
    echo   QMS_SERVER_PATH = %SERVER_PATH%
    echo   OK
) ELSE (
    echo.
    echo   WARNING: QMS script files not found.
    echo   Make sure install.bat is in the QMS_Package root folder,
    echo   which should contain the app\ and server\ subfolders.
    echo.
)
echo.

REM ================================================================
REM  STEP 7 - Create Desktop shortcut
REM ================================================================
echo [7/8] Creating Desktop shortcut...

IF "!FILES_OK!"=="1" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ws = New-Object -ComObject WScript.Shell; ^
         $s  = $ws.CreateShortcut('%USERPROFILE%\Desktop\QMS App.lnk'); ^
         $s.TargetPath       = '!PYTHON_EXE!'; ^
         $s.Arguments        = '\"%APP_PATH%\"'; ^
         $s.WorkingDirectory = '%INSTALL_ROOT%'; ^
         $s.Description      = 'QMS Document Management System'; ^
         $s.Save()" >nul 2>&1

    IF EXIST "%USERPROFILE%\Desktop\QMS App.lnk" (
        echo   Shortcut "QMS App" created on Desktop
    ) ELSE (
        echo   Could not create shortcut automatically.
        echo   Launch manually: "!PYTHON_EXE!" "%APP_PATH%"
    )
) ELSE (
    echo   SKIPPED - fix file locations first.
)
echo   OK
echo.

REM ================================================================
REM  STEP 8 - Check LibreOffice
REM ================================================================
echo [8/8] Checking LibreOffice (for PDF generation)...
SET LO_FOUND=0
soffice --version >nul 2>&1
IF NOT ERRORLEVEL 1 SET LO_FOUND=1
FOR %%F IN (
    "C:\Program Files\LibreOffice\program\soffice.exe"
    "C:\Program Files (x86)\LibreOffice\program\soffice.exe"
) DO IF "!LO_FOUND!"=="0" IF EXIST %%F SET LO_FOUND=1

IF "!LO_FOUND!"=="1" (
    echo   LibreOffice found. PDF generation enabled.
) ELSE (
    echo   NOT FOUND. PDF generation will be skipped.
    echo   Optional: download from https://libreoffice.org
)
echo   OK
echo.

REM ================================================================
REM  DONE
REM ================================================================
echo  ==============================================================
echo   Installation complete!
echo  ==============================================================
echo.
IF "!FILES_OK!"=="1" (
    echo  LAUNCH:
    echo    Double-click "QMS App" on your Desktop
    echo    -- OR --
    echo    "!PYTHON_EXE!" "%APP_PATH%"
    echo.
)
echo  FIRST-TIME SETUP:
echo    Settings panel: QMS Root Folder, Name, Email, Company Name
echo    Team Roster: add team members
echo.
echo  WORD/EXCEL RIBBON:
echo    See QMS_DMS_User_Guide_v1_3.docx - Parts 2.5 and 2.6
echo    Requires: https://github.com/fernandreu/office-ribbonx-editor
echo.
pause
