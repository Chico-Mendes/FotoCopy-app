#define appName "FotoCopy"
#define appVersion "1.0.0"
#define sourceFile "copy-files-app.exe"

[Setup]
;AppId={{08203CFF-8664-4C29-AE3C-0BC1256C8F7D}
AppName={#appName}
AppVersion={#appVersion}
WizardStyle=modern
DefaultDirName={autopf}\{#appName}
DefaultGroupName={#appName}
OutputDir=.
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
