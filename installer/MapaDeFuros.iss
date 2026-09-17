; Inno Setup 6 - instalador do Mapa de Furos
#define AppName "Mapa de Furos"
#define AppVersion "1.0.0"
#define AppPublisher "Barreto Engenharia"
#define AppExe "MapaDeFuros.exe"

[Setup]
AppId={{7C1E3B52-8F4A-4E0B-9C1D-5A2F6B8D3E41}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\MapaDeFuros
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\assets\mapadefuros.ico
OutputDir=..\dist_instalador
OutputBaseFilename=MapaDeFuros_Setup_{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"
Name: "assockml"; Description: "Adicionar ""Abrir com Mapa de Furos"" para arquivos KML/KMZ"; GroupDescription: "Integração:"; Flags: unchecked

[Files]
Source: "..\dist\MapaDeFuros\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\exemplos\*"; DestDir: "{app}\exemplos"; Flags: ignoreversion
Source: "..\LEIAME.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Exemplos"; Filename: "{app}\exemplos"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.kml\OpenWithProgids"; ValueType: string; ValueName: "MapaDeFuros.kml"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assockml
Root: HKA; Subkey: "Software\Classes\.kmz\OpenWithProgids"; ValueType: string; ValueName: "MapaDeFuros.kml"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assockml
Root: HKA; Subkey: "Software\Classes\MapaDeFuros.kml"; ValueType: string; ValueName: ""; ValueData: "Polígono para Mapa de Furos"; Flags: uninsdeletekey; Tasks: assockml
Root: HKA; Subkey: "Software\Classes\MapaDeFuros.kml\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: assockml
Root: HKA; Subkey: "Software\Classes\MapaDeFuros.kml\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: assockml

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent
