#!/usr/bin/env python3
"""Start the Flask development server with pre-flight checks."""

import subprocess
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
APP_PATH = os.path.join(PROJECT_ROOT, "app.py")
REQUIREMENTS = os.path.join(PROJECT_ROOT, "requirements.txt")

def check_dependencies():
    try:
        import flask
    except ImportError:
        print("[!] Flask not found. Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS])

def check_port(port=5000):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            print(f"[!] Port {port} is already in use. Run /run-app stop first.")
            sys.exit(1)

def main():
    check_dependencies()
    check_port()
    print(f"[*] Starting Flask app from {APP_PATH}")
    print(f"[*] Access at http://localhost:5000")
    os.chdir(PROJECT_ROOT)
    subprocess.run([sys.executable, APP_PATH])

if __name__ == "__main__":
    main()
