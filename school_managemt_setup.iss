; Inno Setup 6 script for Hope Academy School Management System.
; Build the executable first (build_exe.bat), or run: build_exe.ps1 -Installer
;
; Runtime data (settings, logs, reports, backups) lives in
; %APPDATA%\Hope Academy School Management System, not in the install folder,
; so the application can run from Program Files without write access.

#define MyAppName "Hope Academy School Management System"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Hope Academy"
#define MyAppExeName "Hope_Academy_School_Management_System.exe"

[Setup]
; Unique per application; never change it, or upgrades will install side by side.
AppId={{5E70B4D2-8146-4E45-AD4A-519328793E98}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=Hope_Academy_School_Management_System_Setup
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
FinishedLabel=Setup has finished installing [name].%n%nNothing else needs to be installed. When the program opens for the first time it will ask where to keep the school's information - choose "On this computer".

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\user_manual.pdf"; DestDir: "{app}\docs"; Flags: ignoreversion
; Only needed by administrators who choose the optional MySQL storage.
Source: "database\schema.sql"; DestDir: "{app}\database"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\User Manual"; Filename: "{app}\docs\user_manual.pdf"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; School data lives in %APPDATA%\Hope Academy School Management System and is
; deliberately left in place on uninstall, so reinstalling keeps every record.
