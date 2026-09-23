#define AppName "Asi Barkod PC Alicisi"
#define AppVersion "0.5.3"
#define AppExeName "AsiBarkodReceiver.exe"
#define StartupTaskName "Asi Barkod PC Alicisi"

#ifdef X86_BUILD
  #define BuildArch "x86"
  #define OutputName "Asi-Barkod-Windows-Kurulum-v" + AppVersion + "-x86"
  #define InstallDir "{autopf}\\Asi Barkod"
  #define AllowedArchitectures "x86compatible"
#else
  #define BuildArch "x64"
  #define OutputName "Asi-Barkod-Windows-Kurulum-v" + AppVersion + "-x64"
  #define InstallDir "{autopf64}\\Asi Barkod"
  #define AllowedArchitectures "x64compatible"
#endif

[Setup]
AppId={{9DA94099-5E5D-499B-9A52-CF587A501806}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Asi Barkod
DefaultDirName={#InstallDir}
UsePreviousAppDir=no
UsePreviousTasks=no
DefaultGroupName=Asi Barkod
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename={#OutputName}
SetupIconFile=..\..\pc-receiver\assets\asi_barkod_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=6.2
ArchitecturesAllowed={#AllowedArchitectures}
#ifndef X86_BUILD
ArchitecturesInstallIn64BitMode=x64compatible
#endif
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaustune kisayol ekle"; GroupDescription: "Kisayollar:"
Name: "startup"; Description: "Windows acilinca otomatik baslat"; GroupDescription: "Baslatma:"

[InstallDelete]
; Onceki uygulamanin paketlenmis kutuphanelerini, yeni dosyalar kopyalanmadan temizle.
; Inno kaldirici kayitlari ve %APPDATA% altindaki kullanici verileri korunur.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\..\dist\{#BuildArch}\AsiBarkodReceiver\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Asi Barkod PC Alicisi"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Asi Barkod PC Alicisi"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod Receiver TCP 8765"""; Flags: runhidden waituntilterminated; StatusMsg: "Eski ag kurallari temizleniyor..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod Discovery UDP 8766"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod TCP 8765"""; Flags: runhidden waituntilterminated; StatusMsg: "Eski ag kurallari temizleniyor..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod UDP 8766"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone HTTPS 8767"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone Kurulum 8768"""; Flags: runhidden waituntilterminated
Filename: "{app}\{#AppExeName}"; Description: "Asi Barkod PC Alicisini baslat"; Flags: nowait postinstall skipifsilent shellexec

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""{#StartupTaskName}"" /F"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveStartupTask"
Filename: "{sys}\taskkill.exe"; Parameters: "/IM {#AppExeName} /F"; Flags: runhidden waituntilterminated; RunOnceId: "StopReceiver"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod TCP 8765"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveTcpRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod UDP 8766"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveUdpRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone HTTPS 8767"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveIphoneHttpsRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone Kurulum 8768"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveIphoneSetupRule"

[UninstallDelete]
Type: files; Name: "{commonstartup}\Asi Barkod PC Alicisi.lnk"

[Code]
function RemovePreviousInstall(RootKey: Integer; Architecture: String): String;
var
  OldCommand: String;
  OldUninstaller: String;
  ResultCode: Integer;
  ClosingQuote: Integer;
begin
  Result := '';
  if not RegQueryStringValue(RootKey,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{9DA94099-5E5D-499B-9A52-CF587A501806}_is1',
    'UninstallString', OldCommand) then
    exit;

  { Inno'nun UninstallString degeri tirnak icindeki unins???.exe yoludur. }
  if (Length(OldCommand) > 1) and (OldCommand[1] = '"') then
  begin
    ClosingQuote := Pos('"', Copy(OldCommand, 2, Length(OldCommand) - 1));
    if ClosingQuote = 0 then
    begin
      Result := Architecture + ' eski kaldirici yolu gecersiz: ' + OldCommand;
      exit;
    end;
    OldUninstaller := Copy(OldCommand, 2, ClosingQuote - 1);
  end
  else
    OldUninstaller := OldCommand;

  if not FileExists(OldUninstaller) then
  begin
    Result := Architecture + ' eski kaldirici bulunamadi: ' + OldUninstaller;
    exit;
  end;

  if not Exec(OldUninstaller, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '',
    SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := Architecture + ' eski surum kaldirilamadi. Hata kodu: ' + IntToStr(ResultCode)
  else if ResultCode <> 0 then
    Result := Architecture + ' eski surum kaldirilamadi. Cikis kodu: ' + IntToStr(ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  LegacyDir: String;
begin
  { Onceki tasinabilir/BAT kurulumunu durdur; log klasorunu koru. }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM asi_barkod_receiver.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM AsiBarkodReceiver.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM AsiBarkodIphoneBridge.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  { Onceki x86/x64 surumlerini kendi Inno kaldiricilariyla kaldir. }
  Result := RemovePreviousInstall(HKLM32, 'x86');
  if Result <> '' then
    exit;
  if IsWin64 then
  begin
    Result := RemovePreviousInstall(HKLM64, 'x64');
    if Result <> '' then
      exit;
  end;

  { Yonetici manifestli EXE, Baslangic klasorundaki normal kisayoldan acilamaz. }
  DeleteFile(ExpandConstant('{commonstartup}\Asi Barkod PC Alicisi.lnk'));
  DeleteFile(ExpandConstant('{userstartup}\Asi Barkod Receiver.cmd'));
  LegacyDir := ExpandConstant('{localappdata}\Programs\AsiBarkod');
  DeleteFile(LegacyDir + '\Asi Barkod Receiver.cmd');
  DeleteFile(LegacyDir + '\asi_barkod_receiver.exe');
  DeleteFile(LegacyDir + '\AsiBarkod-Kurulum-Windows-Android.zip');
  DeleteFile(LegacyDir + '\AsiBarkod.apk');
  DeleteFile(LegacyDir + '\install_latest_github.bat');
  DeleteFile(LegacyDir + '\install_windows_admin.bat');
  DeleteFile(LegacyDir + '\uninstall_windows_admin.bat');
  DeleteFile(LegacyDir + '\OKU_BENI_KURULUM.txt');
  DelTree(LegacyDir + '\assets', True, True, True);

end;

procedure ConfigureStartupTask;
var
  ResultCode: Integer;
  TaskCommand: String;
  TaskParameters: String;
begin
  { Onceki ayari kaldir; guncellemede kullanicinin secimi aynen uygulanir. }
  Exec(ExpandConstant('{sys}\schtasks.exe'), '/Delete /TN "{#StartupTaskName}" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if not WizardIsTaskSelected('startup') then
    exit;

  { /IT: yalniz oturum acik kullanicinin masaustunde calisir.
    /RL HIGHEST: PyInstaller --uac-admin manifestiyle uyumlu en yuksek yetki. }
  { /TR tek arguman olmali; icteki EXE yolu icin tirnaklar kactirilmali. }
  TaskCommand := '\"' + ExpandConstant('{app}\{#AppExeName}') + '\" --tray';
  TaskParameters := '/Create /TN "{#StartupTaskName}" /TR "' + TaskCommand +
    '" /SC ONLOGON /RU "' + GetUserNameString + '" /IT /RL HIGHEST /F';
  if not Exec(ExpandConstant('{sys}\schtasks.exe'), TaskParameters, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    MsgBox('Windows otomatik baslatma gorevi olusturulamadi. Hata kodu: ' + IntToStr(ResultCode), mbError, MB_OK)
  else if ResultCode <> 0 then
    MsgBox('Windows otomatik baslatma gorevi olusturulamadi. Hata kodu: ' + IntToStr(ResultCode), mbError, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    ConfigureStartupTask;
end;
