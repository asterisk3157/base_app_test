"""
conftest.py — pytest configuration for E2E tests.
Starts the Flask server in a background thread if it is not already running.
"""
import os
import sys
import time
import socket
import subprocess
import threading
import pytest

APP_HOST = '127.0.0.1'
APP_PORT = 5000
BASE_URL = f'http://{APP_HOST}:{APP_PORT}'

# Path to app.py
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_FILE = os.path.join(APP_DIR, 'app.py')


def _is_server_running():
    """Return True if something is listening on APP_PORT."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((APP_HOST, APP_PORT))
            return True
        except (ConnectionRefusedError, socket.timeout):
            return False


def _start_server():
    """Start the Flask dev server as a subprocess."""
    env = os.environ.copy()
    env['PYTHONPATH'] = APP_DIR
    proc = subprocess.Popen(
        [sys.executable, APP_FILE],
        cwd=APP_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait up to 10 seconds for the server to become available
    for _ in range(20):
        if _is_server_running():
            return proc
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError('Flask server did not start within 10 seconds')


_server_proc = None


def pytest_configure(config):
    """Start the server once for the entire test session."""
    global _server_proc
    if not _is_server_running():
        _server_proc = _start_server()


def pytest_unconfigure(config):
    """Stop the server process if we started it."""
    global _server_proc
    if _server_proc is not None:
        _server_proc.terminate()
        _server_proc = None


@pytest.fixture(scope='session')
def base_url():
    return BASE_URL
