; 光明（Light）v7.0.0 Windows 安装包配置文件
; 需要 Inno Setup 6+ 编译
; 下载地址: https://jrsoftware.org/isdl.php

#define MyAppName "光明"
#define MyAppNameEnglish "Light"
#define MyAppVersion "7.0.0"
#define MyAppPublisher "Light Contributors"
#define MyAppURL "https://github.com/skywalk163/light"
#define MyAppExeName "light.exe"

[Setup]
; AppId 刻意沿用 duan 时期的 GUID：它是 Windows 侧的升级身份标识，
; 不是用户可见名称。保持不变，装 v7 才会覆盖升级旧的段言安装，
; 换新 GUID 会让两个版本并存、且旧版卸载项永久残留。
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
OutputBaseFilename=light-{#MyAppVersion}-setup
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
; 光明核心文件（whl 名必须与 pyproject.toml 的 name 一致，当前为 light）
Source: "..\..\dist\light-{#MyAppVersion}-py3-none-any.whl"; DestDir: "{app}\dist"; Flags: ignoreversion
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
Name: "{group}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/k light"
Name: "{group}\{#MyAppName} REPL"; Filename: "{cmd}"; Parameters: "/k light repl"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/k light"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C pip install --user {app}\dist\light-{#MyAppVersion}-py3-none-any.whl"; Description: "安装光明到 Python 环境"; Flags: postinstall runascurrentuser

[UninstallRun]
; 顺带清掉 duan 时期用同一个 AppId 装下的旧 PyPI 包，避免 light 与 duan 两套入口点并存
Filename: "{cmd}"; Parameters: "/C pip uninstall light -y"; Flags: runhidden
Filename: "{cmd}"; Parameters: "/C pip uninstall duan -y"; Flags: runhidden

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
