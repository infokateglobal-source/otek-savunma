# Otek Savunma (MVP) - Kuruluma Hazır Paket

Bu paket, küçük işletmeler için "indirilen dosyaları izleme + şüpheli dosyayı karantinaya alma" MVP ajanını içerir.

> Bu ortamda Windows için doğrudan .exe installer üretemiyorum (Windows'ta derleme gerekir).
> Ama sana **tek tıkla** Windows'ta .exe + installer üretmen için hazır proje + script veriyorum.

## 1) Windows'ta hızlı kurulum
1. Python 3.11+ kur.
2. Bu klasörde:
   - `pip install -r requirements.txt`
3. Çalıştır:
   - `python otek_agent.py`

### Eşik ayarı (opsiyonel)
Varsayılan eşik: 60
- Daha hassas yapmak için:
  - PowerShell: `setx OTEK_THRESHOLD 50`
  - Sonra terminali kapat/aç.

## 2) Windows için .exe üretme (PyInstaller)
1. `build_windows.bat` çalıştır.
2. Çıktı:
   - `dist\OtekSavunma.exe`

## 3) Installer (Inno Setup)
- `installer_inno.iss` dosyası hazır.
- Inno Setup ile açıp **Compile** de.
- Kurulum dosyası `installer_output\` içine çıkar.

## 4) Kayıtlar / Karantina
- Windows: `%APPDATA%\OtekSavunma\`
  - `Quarantine\`
  - `logs\events.ndjson`

## Icon
- `otek.ico` pakete eklendi. `build_windows.bat` icon ile derler.

## Tray + Panel
- Uygulama açılınca sistem tepsisinde (tray) simge oluşur.
- Pencereyi kapatırsan tepsiye gizlenir.
- Çıkış için tepsi menüsünden **Çıkış**.

## Notlar (Sorun giderme)
- Eğer program açılıp kapanıyorsa: `%%APPDATA%%\OtekSavunma\logs\crash.log` dosyasına bak.
- Çıktı artık: `dist\OtekSavunma\OtekSavunma.exe`
