@echo off
rem Sestaví dist\NetReins.exe (jeden soubor, sám si řekne o práva správce).
rem Použití: build_exe.bat [cílová složka]
setlocal
cd /d "%~dp0"
set DIST=%~1
if "%DIST%"=="" set DIST=dist

python -m pip install -r requirements.txt pyinstaller || exit /b 1
python make_version_file.py || exit /b 1
for /f "delims=" %%i in ('python -c "import os, pydivert.windivert_dll as w; print(os.path.dirname(w.__file__))"') do set WD=%%i

python -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin ^
  --name NetReins --distpath "%DIST%" ^
  --icon icon.ico --add-data "icon.ico;." --add-data "icon.png;." ^
  --hidden-import pystray._win32 --version-file build\version_info.txt ^
  --add-binary "%WD%\WinDivert64.dll;pydivert\windivert_dll" ^
  --add-binary "%WD%\WinDivert64.sys;pydivert\windivert_dll" ^
  main.py || exit /b 1

echo.
echo Hotovo: %DIST%\NetReins.exe
