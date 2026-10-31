; installer.iss — Script de Inno Setup 6 para el Sistema AT
; Genera installer_output/SistemaAT_Setup_1.0.0.exe a partir de dist\SistemaAT\*
; Compilar: ISCC.exe installer.iss   (o directamente con build.py)

#define AppName "Sistema AT"
#define AppVersion "1.0.0"
#define AppPublisher "DINADAF · Instituto Peruano del Deporte"
#define AppExe "SistemaAT.exe"

[Setup]
AppId={{7E1F6C9A-52B4-4C7D-9A3E-8D2F51B0A644}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://www.gob.pe/ipd
DefaultDirName={autopf}\SistemaAT
PrivilegesRequired=lowest
DefaultGroupName={#AppName}
OutputDir=installer_output
OutputBaseFilename=SistemaAT_Setup_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
; Los datos del usuario viven en %LOCALAPPDATA%\SistemaAT\ y NO se eliminan
; al desinstalar, por lo que sobreviven a reinstalaciones y actualizaciones.

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "startmenu"; Description: "Crear accesos directos en el menú Inicio"; \
    GroupDescription: "Accesos directos:"
Name: "desktopicon"; Description: "Crear un acceso directo en el &escritorio"; \
    GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\SistemaAT\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startmenu
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Ejecutar {#AppName} ahora"; \
    Flags: nowait postinstall skipifsilent
