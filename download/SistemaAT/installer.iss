; =============================================================
;  Sistema AT · IPD - DINADAF — Instalador (Inno Setup 6)
;  Compilar con: Inno Setup Compiler → installer.iss
;  Requiere antes: python build.py installer  (genera dist\SistemaAT)
;  Privilegios mínimos: instala en %LOCALAPPDATA%\Programs sin UAC.
;  Los datos del usuario viven en %LOCALAPPDATA%\SistemaAT y NO se
;  eliminan al desinstalar.
; =============================================================

#define MyAppName "Sistema AT"
#define MyAppVersion "1.0"
#define MyAppPublisher "IPD - DINADAF"
#define MyAppURL "https://www.gob.pe/ipd"
#define MyAppExeName "SistemaAT.exe"

[Setup]
AppId={{6F1B2C3D-4A5E-4F60-8A71-9B8C2D3E4F50}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputBaseFilename=Instalador_SistemaAT_v{#MyAppVersion}
OutputDir=dist_instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el &escritorio"; \
    GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\SistemaAT\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Intencionalmente vacío: los datos de %LOCALAPPDATA%\SistemaAT se conservan.
