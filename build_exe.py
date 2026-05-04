"""
Build script for GestVoice Smart Assistant EXE.
Run this to create a standalone .exe that users can double-click to launch.

Usage:  python build_exe.py
Output: dist/GestVoice.exe
"""

import PyInstaller.__main__
import os
import sys

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# MediaPipe needs its data files bundled
import mediapipe
mp_path = os.path.dirname(mediapipe.__file__)

PyInstaller.__main__.run([
    os.path.join(script_dir, 'new.py'),
    '--name=GestVoice',
    '--onefile',
    '--console',                # Keep console for debug output
    f'--add-data={os.path.join(script_dir, "cursor_control.py")};.',
    f'--add-data={mp_path};mediapipe',
    '--hidden-import=mediapipe',
    '--hidden-import=cv2',
    '--hidden-import=pyttsx3',
    '--hidden-import=speech_recognition',
    '--hidden-import=pyautogui',
    '--hidden-import=PIL',
    '--hidden-import=sklearn',
    '--hidden-import=sklearn.feature_extraction.text',
    '--hidden-import=sklearn.naive_bayes',
    '--hidden-import=sklearn.pipeline',
    '--hidden-import=sklearn.utils._cython_blas',
    '--hidden-import=sklearn.neighbors._typedefs',
    '--hidden-import=sklearn.neighbors._quad_tree',
    '--hidden-import=sklearn.tree._utils',
    '--hidden-import=fuzzywuzzy',
    '--hidden-import=google.generativeai',
    '--hidden-import=numpy',
    '--hidden-import=pygetwindow',
    '--hidden-import=pyttsx3.drivers',
    '--hidden-import=pyttsx3.drivers.sapi5',
    '--collect-all=mediapipe',
    '--collect-all=google.generativeai',
    '--noconfirm',
    '--clean',
    f'--distpath={os.path.join(script_dir, "dist")}',
    f'--workpath={os.path.join(script_dir, "build")}',
    f'--specpath={script_dir}',
])

print("\n" + "=" * 60)
print("  ✅ BUILD COMPLETE!")
print(f"  EXE Location: {os.path.join(script_dir, 'dist', 'GestVoice.exe')}")
print("  Double-click GestVoice.exe to launch the app!")
print("=" * 60)
