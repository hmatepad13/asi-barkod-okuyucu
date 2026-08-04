#define AppName "Asi Barkod PC Alicisi"
#define AppVersion "0.5.0"
#define AppExeName "AsiBarkodReceiver.exe"

[Setup]
AppId={{9DA94099-5E5D-499B-9A52-CF587A501806}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Asi Barkod
DefaultDirName={autopf64}\Asi Barkod
UsePreviousAppDir=no
DefaultGroupName=Asi Barkod
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=Asi-Barkod-Windows-Kurulum-v{#AppVersion}
SetupIconFile=..\..\pc-receiver\assets\asi_barkod_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=6.2
ArchitecturesAllowed=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaustune kisayol ekle"; GroupDescription: "Kisayollar:"
Name: "startup"; Description: "Windows acilinca otomatik baslat"; GroupDescription: "Baslatma:"

[Files]
Source: "..\..\dist\AsiBarkodReceiver\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Asi Barkod PC Alicisi"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Asi Barkod PC Alicisi"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{commonstartup}\Asi Barkod PC Alicisi"; Filename: "{app}\{#AppExeName}"; Parameters: "--tray"; Tasks: startup

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod Receiver TCP 8765"""; Flags: runhidden waituntilterminated; StatusMsg: "Eski ag kurallari temizleniyor..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod Discovery UDP 8766"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod TCP 8765"""; Flags: runhidden waituntilterminated; StatusMsg: "Eski ag kurallari temizleniyor..."
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod UDP 8766"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone HTTPS 8767"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone Kurulum 8768"""; Flags: runhidden waituntilterminated
Filename: "{app}\{#AppExeName}"; Description: "Asi Barkod PC Alicisini baslat"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM {#AppExeName} /F"; Flags: runhidden waituntilterminated; RunOnceId: "StopReceiver"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod TCP 8765"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveTcpRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod UDP 8766"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveUdpRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone HTTPS 8767"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveIphoneHttpsRule"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Asi Barkod iPhone Kurulum 8768"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveIphoneSetupRule"

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

  { v0.4.0 ve öncesi paketin x86 Program Files yolunu bırakmadan temizle. }
  DelTree(ExpandConstant('{autopf32}\Asi Barkod'), True, True, True);

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
