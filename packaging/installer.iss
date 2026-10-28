; Instalador do LocalTube (Inno Setup 6). Compilado por packaging\build.ps1, que passa
; AppVersion, SourceDir (dist\LocalTube), OutputDir e IconFile.
;
; Instala só para o usuário atual (sem pedir administrador), em %LOCALAPPDATA%\Programs.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F1E0C55-3B7A-4C2B-9E43-0A8D5B1F7C21}
AppName=LocalTube
AppVersion={#AppVersion}
AppVerName=LocalTube {#AppVersion}
AppPublisher=LocalTube
AppPublisherURL=https://github.com/marcelosmbr2/localtube
DefaultDirName={autopf}\LocalTube
DefaultGroupName=LocalTube
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=LocalTube-{#AppVersion}-Setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\LocalTube.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\LocalTube"; Filename: "{app}\LocalTube.exe"
Name: "{autodesktop}\LocalTube"; Filename: "{app}\LocalTube.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LocalTube.exe"; Description: "{cm:LaunchProgram,LocalTube}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; yt-dlp baixado por "Atualizar". As configurações (%APPDATA%\LocalTube) e os vídeos ficam.
Type: filesandordirs; Name: "{localappdata}\LocalTube\yt-dlp"
