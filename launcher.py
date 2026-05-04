"""
GestVoice Launcher - Simple wrapper that imports and runs the main module.
This avoids PyInstaller bytecode scanning issues with complex files.
"""
import sys
import os

# When running as EXE, add the bundled path
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    sys.path.insert(0, base_path)
    os.chdir(base_path)

# Import and run
from new import main
main()
