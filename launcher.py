"""
GestVoice Launcher - Unified entry point for starting AETHER_CORE.
Runs Django development server in a managed background process,
automatically launches the web browser to the dashboard,
and runs the AI gesture + voice assistant on the main thread.
"""
import sys
import os
import subprocess
import time
import webbrowser
import threading

# When running as EXE, add the bundled path
is_frozen = getattr(sys, 'frozen', False)
if is_frozen:
    base_path = sys._MEIPASS
    sys.path.insert(0, base_path)
    os.chdir(base_path)

def run_django():
    """Starts the Django development server in a separate background process."""
    print("[SYSTEM] Connecting to MongoDB and starting Django server...")
    django_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intent_os")
    
    return subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8000"],
        cwd=django_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def open_dashboard():
    """Waits for Django to initialize, then opens the dashboard in the browser."""
    print("[SYSTEM] Initializing AI components and camera feed...")
    time.sleep(3.0)
    print("[SYSTEM] Opening AETHER_CORE dashboard at http://127.0.0.1:8000/ ...")
    webbrowser.open("http://127.0.0.1:8000/")

# Only start Django and the browser if running as raw Python (not compiled standalone EXE)
django_proc = None
if not is_frozen:
    django_proc = run_django()
    threading.Thread(target=open_dashboard, daemon=True).start()

# Import and run the AI Assistant (runs on main thread for OpenCV GUI responsiveness)
try:
    from new import main
    main()
finally:
    if django_proc:
        print("[SYSTEM] Stopping Django backend...")
        django_proc.terminate()
        try:
            django_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            django_proc.kill()
        print("[SYSTEM] Clean shutdown completed.")

