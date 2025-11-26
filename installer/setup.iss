; Inno Setup Script for WeWork Booker
; Download Inno Setup from: https://jrsoftware.org/isinfo.php

#define MyAppName "WeWork Booker"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "WeWork Booker"
#define MyAppURL "https://github.com/samspacey/wework-booker"
#define MyAppExeName "WeWork Booker.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; OutputDir is relative to the .iss file location
OutputDir=..\dist\installer
OutputBaseFilename=WeWorkBooker_Setup_{#MyAppVersion}
SetupIconFile=..\resources\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Install for current user only (no admin required)
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Source path is relative to the .iss file location
Source: "..\dist\WeWork Booker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
