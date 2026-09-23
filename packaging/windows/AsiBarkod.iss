#define AppName "Asi Barkod PC Alicisi"
#define AppVersion "0.5.2"
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
Name: "startup"; Description: "Windows acilinca otomatik baslat"; GroupDescription: "Baslatma:"; Flags: checkedonce

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
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  LegacyDir: String;
begin
  { Onceki tasinabilir/BAT kurulumunu durdur; log klasorunu koru. }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM asi_barkod_receiver.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM AsiBarkodReceiver.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM AsiBarkodIphoneBridge.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  { Mimari değiştirildiyse eski kurulum klasörünü bırakmadan temizle. }
#ifdef X86_BUILD
  if IsWin64 then
    DelTree(ExpandConstant('{autopf64}\Asi Barkod'), True, True, True);
#else
  DelTree(ExpandConstant('{autopf32}\Asi Barkod'), True, True, True);
  { Eski x86 kurulum kaydini ve kendi kaldiricisini temizle. }
  RegDeleteKeyIncludingSubkeys(HKLM32, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{9DA94099-5E5D-499B-9A52-CF587A501806}_is1');
  DeleteFile(ExpandConstant('{autopf64}\Asi Barkod\unins000.exe'));
  DeleteFile(ExpandConstant('{autopf64}\Asi Barkod\unins000.dat'));
  DeleteFile(ExpandConstant('{autopf64}\Asi Barkod\unins000.msg'));
#endif

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

  Result := '';
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
  TaskCommand := '"' + ExpandConstant('{app}\{#AppExeName}') + '" --tray';
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
