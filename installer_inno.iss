#define MyAppName "Otek Savunma"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Otek"
#define MyAppExeName "OtekSavunma.exe"

[Setup]
AppId={{9E3F2B6B-4C0F-4B7B-9F0B-OTEK-SAVUNMA-MVP}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\OtekSavunma
DefaultGroupName=Otek Savunma
OutputDir=installer_output
OutputBaseFilename=OtekSavunma_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Otek Savunma"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\Otek Savunma"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Kısayollar:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Otek Savunma'yı çalıştır"; Flags: nowait postinstall skipifsilent
