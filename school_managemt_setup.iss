; InnoSetup Script for School Management System
; Requires InnoSetup 6 or later

#define MyAppName "Primary School Management System"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Greenwood Primary School"
#define MyAppURL "https://www.greenwood.edu"
#define MyAppExeName "SchoolManagementSystem.exe"
#define MyAppSetupName "SchoolManagementSystem_Setup"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{6B29FC40-CA47-1067-B31D-00DD010662DA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename={#MyAppSetupName}
SetupIconFile=assets\icons\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardImageFile=assets\setup_wizard.bmp
WizardSmallImageFile=assets\setup_wizard_small.bmp
SetupLogging=yes

; Languages
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

; Custom messages
[Messages]
WelcomeLabel2=This will install [name] on your computer.%n%nIt is recommended that you close all other applications before continuing.%n%nMySQL Server is required for this application to function properly.
ReadyLabel2=Setup is now ready to begin installing [name] on your computer.
FinishedLabel=Setup has finished installing [name] on your computer.%n%nPlease ensure MySQL Server is installed and running before starting the application.

[CustomMessages]
english.MySQLRequired=MySQL Server is required for this application to function properly. Please ensure MySQL is installed before continuing.
english.CreateDesktopIcon=Create a &desktop icon
english.CreateQuickLaunchIcon=Create a &Quick Launch icon
english.InstallMySQL=Install MySQL Server (if not already installed)
english.DownloadMySQL=Download MySQL Installer
english.MySQLInstalled=MySQL Server is already installed on this computer.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "mysqlcheck"; Description: "{cm:InstallMySQL}"; GroupDescription: "Prerequisites:"; Flags: checkedonce
Name: "createdatabase"; Description: "Create &database tables automatically"; GroupDescription: "Database Setup:"; Flags: checkedonce

[Files]
; Main executable
Source: "dist\SchoolManagementSystem.exe"; DestDir: "{app}"; Flags: ignoreversion
; Database files
Source: "database\*"; DestDir: "{app}\database"; Flags: ignoreversion recursesubdirs createallsubdirs
; Setup scripts
Source: "setup_database.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup_database.bat"; DestDir: "{app}"; Flags: ignoreversion
; Documentation
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTALLATION_GUIDE.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
; Assets
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
; Config file
Source: "config.py"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; AfterInstall: UpdateConfigFile
; MySQL Connector (optional - include if you want to bundle it)
; Source: "mysql-connector-python-8.0.33-py3-none-any.whl"; DestDir: "{tmp}"; Flags: deleteafterinstall

; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Run database setup if selected
Filename: "{app}\setup_database.bat"; Description: "Set up database tables"; Flags: runhidden nowait skipifdoesntexist; Tasks: createdatabase
; Run the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Add any uninstall cleanup here
Filename: "{cmd}"; Parameters: "/C ""taskkill /f /im SchoolManagementSystem.exe"""; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\*.log"

[Code]
// Pascal Script for custom setup behavior
var
  MySQLPage: TInputOptionWizardPage;
  MySQLInstalled: Boolean;
  MySQLPort: String;
  MySQLRootPassword: String;

function IsMySQLInstalled: Boolean;
var
  ResultCode: Integer;
begin
  // Check if MySQL service exists
  Result := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\MySQL');
  
  // Alternative check: Try to connect to MySQL
  if not Result then
  begin
    Result := FileExists(ExpandConstant('{commonpf32}\MySQL\MySQL Server 8.0\bin\mysqld.exe')) or
              FileExists(ExpandConstant('{commonpf64}\MySQL\MySQL Server 8.0\bin\mysqld.exe')) or
              FileExists(ExpandConstant('{commonpf32}\MySQL\MySQL Server 5.7\bin\mysqld.exe')) or
              FileExists(ExpandConstant('{commonpf64}\MySQL\MySQL Server 5.7\bin\mysqld.exe'));
  end;
  
  MySQLInstalled := Result;
end;

function InitializeSetup: Boolean;
begin
  // Check for .NET Framework or other prerequisites
  Result := True;
end;

procedure InitializeWizard;
var
  MySQLCheckPage: TOutputMsgWizardPage;
begin
  // Create custom page for MySQL check
  MySQLCheckPage := CreateOutputMsgPage(wpWelcome,
    'MySQL Server Check',
    'Checking for MySQL Server installation',
    'The School Management System requires MySQL Server to store data.' + #13#10 +
    'Setup will now check if MySQL is installed on your computer.');
    
  // Check MySQL installation
  if not IsMySQLInstalled then
  begin
    MySQLCheckPage.Msg2.Caption :=
      'MySQL Server was not detected on your system.' + #13#10 +
      'You must install MySQL Server before using this application.' + #13#10#13#10 +
      'Click Next to continue with installation, then install MySQL manually.';
  end
  else
  begin
    MySQLCheckPage.Msg2.Caption :=
      'MySQL Server is installed on your system.' + #13#10 +
      'Setup will configure the application to use the existing MySQL installation.';
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if CurPageID = wpSelectTasks then
  begin
    // Warn about MySQL if not installed
    if not MySQLInstalled then
    begin
      if MsgBox('MySQL Server is not installed. The application will not function without it.' + #13#10 +
                'Do you want to continue with installation?', mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end;
end;

procedure UpdateConfigFile;
var
  ConfigFile: String;
  ConfigContent: TStringList;
begin
  ConfigFile := ExpandConstant('{app}\config.py');
  
  if FileExists(ConfigFile) then
  begin
    ConfigContent := TStringList.Create;
    try
      ConfigContent.LoadFromFile(ConfigFile);
      
      // Update database configuration based on user's system
      // This is a simple example - you might want to make this more sophisticated
      for i := 0 to ConfigContent.Count - 1 do
      begin
        if Pos('''host''', ConfigContent[i]) > 0 then
          ConfigContent[i] := '    ''host'': ''localhost'','
        else if Pos('''password''', ConfigContent[i]) > 0 then
          ConfigContent[i] := '    ''password'': '''',' // Empty password by default
        else if Pos('CURRENT_ACADEMIC_YEAR', ConfigContent[i]) > 0 then
        begin
          // Set current year
          ConfigContent[i] := '    CURRENT_ACADEMIC_YEAR = "' + GetDateTimeString('yyyy', '', '') + '",';
        end;
      end;
      
      ConfigContent.SaveToFile(ConfigFile);
    finally
      ConfigContent.Free;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create necessary directories
    ForceDirectories(ExpandConstant('{app}\data\backups'));
    ForceDirectories(ExpandConstant('{app}\data\exports'));
    ForceDirectories(ExpandConstant('{app}\data\temp'));
    ForceDirectories(ExpandConstant('{app}\logs'));
    
    // Set permissions on data directories
    // (This would require more advanced code for proper permissions setting)
  end;
end;

procedure DeinitializeSetup;
begin
  // Cleanup if needed
end;

[Registry]
; Add application to Windows Registry for file associations or other settings
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}\Settings"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}\Settings"; ValueType: dword; ValueName: "Version"; ValueData: "{$GetFileVersion(expand('{app}\{#MyAppExeName}'))}"; Flags: uninsdeletevalue

[InstallDelete]
; Clean up old versions or temporary files
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"

; Custom installer pages
[CustomMessages]
english.WelcomePageTitle=Welcome to the School Management System Setup
english.WelcomePageDescription=This wizard will guide you through the installation of the School Management System.
english.SelectDirPageTitle=Choose Install Location
english.SelectDirPageDescription=Choose the folder where the School Management System will be installed.
english.SelectTasksPageTitle=Select Additional Tasks
english.SelectTasksPageDescription=Select additional tasks you would like Setup to perform.
english.ReadyPageTitle=Ready to Install
english.ReadyPageDescription=Setup is now ready to begin installation.
english.InstallingPageTitle=Installing
english.InstallingPageDescription=Please wait while Setup installs the School Management System.
english.FinishedPageTitle=Completing the School Management System Setup
english.FinishedPageDescription=Setup has finished installing the School Management System.

[Setup]
; Compression
CompressionThreads=2
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
LZMANumFastBytes=273

; Version info for the installer
VersionInfoVersion=1.0.0.0
VersionInfoCompany=Greenwood Primary School
VersionInfoDescription=School Management System Installer
VersionInfoTextVersion=1.0.0
VersionInfoCopyright=Copyright © 2024 Greenwood Primary School

; Sign the installer (optional - requires code signing certificate)
; SignTool=signtool

[Languages]
Name: en; MessagesFile: "compiler:Default.isl"
Name: es; MessagesFile: "compiler:Languages\Spanish.isl"