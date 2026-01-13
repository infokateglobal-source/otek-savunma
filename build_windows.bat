@echo off
setlocal
echo [Otek Savunma] Windows build basliyor...

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Daha stabil: onedir build (onerilen)
pyinstaller --noconfirm --clean --name "OtekSavunma" --noconsole --icon=otek.ico --add-data "otek_icon_256.png;." otek_app.py

echo.
echo Build tamamlandi: dist\OtekSavunma\OtekSavunma.exe
echo Not: Uygulama tray icon olarak calisir. Kapatinca tepsiye gizlenir.
echo Hata olursa crash log: %%APPDATA%%\OtekSavunma\logs\crash.log

echo.
echo (Debug icin) Konsollu build istersen:
echo pyinstaller --noconfirm --clean --name "OtekSavunmaDebug" --console --icon=otek.ico --add-data "otek_icon_256.png;." otek_app.py

endlocal
