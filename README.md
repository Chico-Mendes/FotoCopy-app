# copy-files-app

Python app to read a file list and copy those files

---

# Packaging a Python Application for Linux and Windows

This guide explains how to create distribution files for a Python application:

- **Linux**: Using `PyInstaller` to generate executables or distribution folders.
- **Windows**: Using `PyInstaller` for cross-compilation (via Wine) and packaging with **Inno Setup** (still on Linux).

---

## 1. Prerequisites

Before starting, ensure you have:

- Python 3.8+ installed
- `pip` and `venv` available
- Required tools installed:

  ```bash
  pip install pyinstaller
  sudo apt install wine mingw-w64
  ```

For **Inno Setup**, you’ll need to install the Windows Inno compiler in Wine:

```bash
wget https://jrsoftware.org/download.php/is.exe
wine is.exe
```

---

## 2. Packaging for Linux

1. **Navigate to your project directory**:

   ```bash
   cd /path/to/your/project
   ```

2. **Create a virtual environment (recommended)**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Generate executable with PyInstaller**:

   ```bash
   pyinstaller --onefile main.py
   ```

   - `--onefile`: bundles everything into a single executable
   - `--noconsole`: (optional) hides console window for GUI apps

4. **Find your build output**:
   The executable will be located in the `dist/` folder:

   ```bash
   dist/main
   ```

5. **Distribute**:

   - Provide the binary directly, or
   - Create a `.tar.gz` or `.deb` package if needed.

---

## 3. Packaging for Windows (on Linux)

### 3.1 Build Windows Executable with PyInstaller + Wine

1. **Install cross-compilation dependencies**:

   ```bash
   sudo apt install wine mingw-w64
   ```

2. **Run PyInstaller under Wine**:

   ```bash
   wine pyinstaller --onefile main.py
   ```

3. **Find your Windows `.exe` file**:

   ```bash
   dist/main.exe
   ```

---

### 3.2 Create Windows Installer with Inno Setup

1. **Write an Inno Setup script (`installer.iss`)**:

   ```iss
   [Setup]
   AppName=MyPythonApp
   AppVersion=1.0
   DefaultDirName={pf}\MyPythonApp
   DefaultGroupName=MyPythonApp
   OutputDir=output
   OutputBaseFilename=MyPythonAppSetup

   [Files]
   Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion

   [Icons]
   Name: "{group}\MyPythonApp"; Filename: "{app}\main.exe"
   Name: "{commondesktop}\MyPythonApp"; Filename: "{app}\main.exe"
   ```

2. **Compile the installer using Wine**:

   ```bash
   wine "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" installer.iss
   ```

3. **Resulting Installer**:
   The installer `.exe` will appear in the `output/` directory:

   ```bash
   output/MyPythonAppSetup.exe
   ```

---

## 4. Publishing

### 4.1. Build the apps

```bash
make
```

---

### 4.2. Add a Git Tag for the Release

1. Choose a version (e.g., `v1.0.0`).
2. Create a git tag:

   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   ```

3. Push the tag:

   ```bash
   git push origin v1.0.0
   ```

---

### 4.3. Publish a GitHub Release (with binaries)

You usually **don’t commit build artifacts** (`dist/`, `output/`) into the repository, but instead upload them as **release assets**.

1. Go to your repo → **Releases** → **Draft a new release**.
2. Choose the tag (e.g., `v1.0.0`).
3. Upload files:

   - `dist/MyPythonApp`
   - `dist/MyPythonApp.exe`
   - `output/MyPythonAppSetup.exe`

4. Publish the release.

---
