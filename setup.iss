#define appName "FotoCopy"
#define appVersion "1.2.12"
#define sourceFile "dist/copy-files-app.exe"

[Setup]
AppId={{08203CFF-8664-4C29-AE3C-0BC1256C8F7D}}
AppName={#appName}
AppVersion={#appVersion}
WizardStyle=modern
DefaultDirName={autopf}\{#appName}
DefaultGroupName={#appName}
OutputDir=dist
OutputBaseFilename={#appName}_setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "{#sourceFile}"; DestDir: "{app}"; DestName: "{#appName}.exe"

[Icons]
Name: "{group}\{#appName}"; Filename: "{app}\{#appName}"
Name: "{group}\Uninstall {#appName}"; Filename: "{uninstallexe}"

[Languages]
Name: pt; MessagesFile: "compiler:Languages\Portuguese.isl"
