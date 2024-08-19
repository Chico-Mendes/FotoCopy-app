#define appName "FotoCopy"
#define appVersion "0.2.1"
#define sourceFile "copy-files-app.exe"

[Setup]
AppId={{08203CFF-8664-4C29-AE3C-0BC1256C8F7D}
AppName={#appName}
AppVersion={#appVersion}
DefaultDirName={autopf}\{#appName}
DefaultGroupName={#appName}
OutputDir=.
OutputBaseFilename={#appName}_setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "{#sourceFile}"; DestDir: "{app}"; DestName: "{#appName}.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\{#appName}"; Filename: "{app}\{#appName}"
Name: "{group}\Uninstall {#appName}"; Filename: "{uninstallexe}"

[Registry]
; Write the version information to the registry
Root: HKLM; Subkey: "Software\{#appName}"; ValueType: string; ValueName: "Version"; ValueData: "{#appVersion}"; Flags: uninsdeletekey
