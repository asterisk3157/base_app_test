#!/usr/bin/env python3
"""Stop the Flask development server by killing the process on port 5000."""

import subprocess
import sys
import re

def stop_windows():
    result = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True
    )
    pids = set()
    for line in result.stdout.splitlines():
        if ":5000" in line and "LISTENING" in line:
            parts = line.split()
            if parts:
                pids.add(parts[-1])
    if not pids:
        print("[*] No process found on port 5000.")
        return
    for pid in pids:
        print(f"[*] Killing PID {pid}...")
        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
    print("[*] Stopped.")

def stop_unix():
    result = subprocess.run(
        ["lsof", "-ti", ":5000"], capture_output=True, text=True
    )
    pids = result.stdout.strip().split("\n")
    pids = [p for p in pids if p]
    if not pids:
        print("[*] No process found on port 5000.")
        return
    for pid in pids:
        print(f"[*] Killing PID {pid}...")
        subprocess.run(["kill", "-9", pid])
    print("[*] Stopped.")

if __name__ == "__main__":
    if sys.platform == "win32":
        stop_windows()
    else:
        stop_unix()
