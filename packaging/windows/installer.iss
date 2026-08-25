#ifndef AppVersion
  #define AppVersion "1.1.4"
#endif
#ifndef SourceDir
  #define SourceDir "build\\windows\\app"
#endif
#ifndef OutputDir
  #define OutputDir "build\\windows\\installer"
#endif

#define AppName "Career Radar"
#define AppPublisher "Mahdi Navaei"
#define AppExeName "CareerRadar.exe"

[Setup]
AppId={{8F5D0A6E-6173-4E0E-B597-7D91E48B3AE7}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs
AppSupportURL=https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs/blob/main/docs/WINDOWS.md
AppUpdatesURL=https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs/releases
VersionInfoDescription=Career Radar Windows desktop application
VersionInfoProductName=Career Radar
VersionInfoCompany={#AppPublisher}
VersionInfoCopyright=Copyright (c) 2026 Mahdi Navaei
VersionInfoOriginalFileName=CareerRadar-Setup-v{#AppVersion}.exe
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoTextVersion={#AppVersion}
VersionInfoProductTextVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\CareerRadar
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=CareerRadar-Setup-v{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Career Radar"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Career Radar"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch Career Radar"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
