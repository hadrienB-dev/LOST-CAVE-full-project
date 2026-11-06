@echo off
setlocal
pushd "%~dp0"

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "Lost Cave" ^
    --add-data "%~dp0assets;assets" ^
    --distpath build ^
    --workpath build\pyinstaller-work ^
    --specpath build ^
    main.py
if errorlevel 1 exit /b %errorlevel%

echo Build cree : build\Lost Cave.exe
popd
