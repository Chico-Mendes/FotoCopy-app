# Variables
APP_NAME = FotoCopy
MAIN_FILE = src/copy-files-app.py
DIST_DIR = dist
BUILD_DIR = build
INNO_SCRIPT = setup.iss
INNO_COMPILER = C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe

# Default target
all: linux windows setup

# Linux build
linux:
	@echo "=== Building Linux binary ==="
	pyinstaller --onefile $(MAIN_FILE)

# Windows build
windows:
	@echo "=== Building Windows binary with Wine ==="
	wine pyinstaller --onefile $(MAIN_FILE)

# Windows setup
setup: windows
	@echo "=== Building Windows setup with Inno Setup ==="
	wine "$(INNO_COMPILER)" $(INNO_SCRIPT)

# Clean up build artifacts
clean:
	@echo "=== Cleaning up build artifacts ==="
	rm -rf $(BUILD_DIR) $(DIST_DIR) __pycache__ *.spec output

.PHONY: all linux windows setup clean
