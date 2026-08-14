; 段言（DuanLang）v6.1.0 Windows 安装包配置文件
; 需要 Inno Setup 6+ 编译
; 下载地址: https://jrsoftware.org/isdl.php

#define MyAppName "段言"
#define MyAppNameEnglish "DuanLang"
#define MyAppVersion "6.1.0"
#define MyAppPublisher "Duan Contributors"
#define MyAppURL "https://github.com/skywalk163/duan"
#define MyAppExeName "duan.exe"

[Setup]
AppId={{D8A7B3C4-5E6F-4A1B-9C2D-3E4F5A6B7C8D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppNameEnglish}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\output\windows
OutputBaseFilename=duan-{#MyAppVersion}-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"

[Files]
; 段言核心文件
Source: "..\..\dist\duan-{#MyAppVersion}-py3-none-any.whl"; DestDir: "{app}\dist"; Flags: ignoreversion
Source: "..\..\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\cli\*"; DestDir: "{app}\cli"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\stdlib\*"; DestDir: "{app}\stdlib"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\stdlib_v3\*"; DestDir: "{app}\stdlib_v3"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\antlrparser\*"; DestDir: "{app}\antlrparser"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Python 嵌入式发行版（需手动下载放置）
; Source: "python-3.10.xx-embed-amd64.zip"; DestDir: "{app}\python"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/k duan"
Name: "{group}\{#MyAppName} REPL"; Filename: "{cmd}"; Parameters: "/k duan repl"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/k duan"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C pip install --user {app}\dist\duan-{#MyAppVersion}-py3-none-any.whl"; Description: "安装段言到 Python 环境"; Flags: postinstall runascurrentuser

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C pip uninstall duan -y"; Flags: runhidden

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;