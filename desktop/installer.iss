[Setup]
AppName=CodeMonkeys
AppVersion=1.0
AppPublisher=CodeMonkeys
DefaultDirName={autopf}\CodeMonkeys
DefaultGroupName=CodeMonkeys
UninstallDisplayIcon={app}\CodeMonkeys.exe
Compression=lzma2
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename=CodeMonkeysSetup
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\CodeMonkeys\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CodeMonkeys"; Filename: "{app}\CodeMonkeys.exe"
Name: "{group}\Uninstall CodeMonkeys"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CodeMonkeys"; Filename: "{app}\CodeMonkeys.exe"; Tasks: desktopicon

[Code]
var
  DownloadPage: TDownloadWizardPage;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ErrorCode: Integer;
begin
  Result := True;
  if CurPageID = wpReady then
  begin
    if not RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Python\PythonCore') and
       not RegKeyExists(HKEY_CURRENT_USER, 'SOFTWARE\Python\PythonCore') then
    begin
      if MsgBox('Python is required but not found. Setup will now download and install Python 3.12. Do you want to continue?', mbConfirmation, MB_YESNO) = IDYES then
      begin
        DownloadPage.Clear;
        DownloadPage.Add('https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe', 'python_installer.exe', '');
        DownloadPage.Show;
        try
          try
            DownloadPage.Download;
          except
            SuppressibleMsgBox(AddPeriod(GetExceptionMessage), mbCriticalError, MB_OK, IDOK);
            Result := False;
            Exit;
          end;
        finally
          DownloadPage.Hide;
        end;
        
        Exec(ExpandConstant('{tmp}\python_installer.exe'), '/quiet InstallAllUsers=0 PrependPath=1', '', SW_SHOW, ewWaitUntilTerminated, ErrorCode);
      end
      else
      begin
        Result := False;
      end;
    end;
  end;
end;