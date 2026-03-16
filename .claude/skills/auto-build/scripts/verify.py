#!/usr/bin/env python3
"""
Start Flask server, run Playwright checks, then shut down.
Usage: python verify.py [--url URL] [--checks basic|full]
"""

import subprocess
import sys
import time
import socket
import os
import json

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
APP_PATH = os.path.join(PROJECT_ROOT, "app.py")
DEFAULT_URL = "http://localhost:5000"


def wait_for_port(port, host="127.0.0.1", timeout=15):
    """Wait until the server is accepting connections."""
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    return False


def start_server():
    """Start Flask in a subprocess."""
    env = os.environ.copy()
    env["FLASK_ENV"] = "development"
    proc = subprocess.Popen(
        [sys.executable, APP_PATH],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if not wait_for_port(5000):
        proc.kill()
        print("[FAIL] Server did not start within 15 seconds.")
        sys.exit(1)
    print("[OK] Server started on port 5000.")
    return proc


def run_playwright_checks(url):
    """Run basic Playwright checks and return results."""
    check_script = f"""
import sys
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[FAIL] Playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)

results = []
url = "{url}"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Check 1: Page loads
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=10000)
        if resp and resp.ok:
            results.append(("Page loads", "PASS", f"Status {{resp.status}}"))
        else:
            status = resp.status if resp else "No response"
            results.append(("Page loads", "FAIL", f"Status {{status}}"))
    except Exception as e:
        results.append(("Page loads", "FAIL", str(e)))

    # Check 2: Title exists
    try:
        title = page.title()
        if title:
            results.append(("Has title", "PASS", title))
        else:
            results.append(("Has title", "WARN", "Empty title"))
    except Exception as e:
        results.append(("Has title", "FAIL", str(e)))

    # Check 3: No console errors
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.reload(wait_until="networkidle", timeout=10000)
    import time; time.sleep(2)
    if errors:
        results.append(("No JS errors", "FAIL", "; ".join(errors[:3])))
    else:
        results.append(("No JS errors", "PASS", ""))

    # Check 4: Interactive elements exist
    try:
        buttons = page.locator("button").count()
        inputs = page.locator("input, textarea").count()
        forms = page.locator("form").count()
        results.append(("Has interactive elements", "PASS" if (buttons + inputs) > 0 else "WARN",
                        f"buttons={{buttons}} inputs={{inputs}} forms={{forms}}"))
    except Exception as e:
        results.append(("Has interactive elements", "FAIL", str(e)))

    # Check 5: Responsive viewport
    try:
        page.set_viewport_size({{"width": 375, "height": 812}})
        page.wait_for_timeout(1000)
        overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        results.append(("Mobile responsive", "PASS" if not overflow else "WARN", "No horizontal overflow" if not overflow else "Horizontal overflow detected"))
        page.set_viewport_size({{"width": 1280, "height": 720}})
    except Exception as e:
        results.append(("Mobile responsive", "FAIL", str(e)))

    # Check 6: API endpoint
    try:
        api_resp = page.goto(url + "/api/posts", wait_until="networkidle", timeout=5000)
        if api_resp and api_resp.ok:
            results.append(("API /api/posts", "PASS", f"Status {{api_resp.status}}"))
        else:
            results.append(("API /api/posts", "WARN", "Endpoint may not exist"))
    except Exception as e:
        results.append(("API /api/posts", "WARN", str(e)))

    # Check 7: Screenshot
    page.goto(url, wait_until="networkidle", timeout=10000)
    screenshot_path = "{os.path.join(PROJECT_ROOT, 'screenshot.png').replace(chr(92), '/')}"
    page.screenshot(path=screenshot_path, full_page=True)
    results.append(("Screenshot saved", "PASS", screenshot_path))

    browser.close()

# Print results
print()
print("=" * 60)
print("  VERIFICATION RESULTS")
print("=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
warned = sum(1 for _, s, _ in results if s == "WARN")
for name, status, detail in results:
    icon = {{"PASS": "[OK]  ", "FAIL": "[FAIL]", "WARN": "[WARN]"}}[status]
    print(f"  {{icon}} {{name}}: {{detail}}")
print("=" * 60)
print(f"  PASS={{passed}}  FAIL={{failed}}  WARN={{warned}}")
print("=" * 60)

sys.exit(1 if failed > 0 else 0)
"""
    result = subprocess.run(
        [sys.executable, "-c", check_script],
        cwd=PROJECT_ROOT,
        capture_output=False,
    )
    return result.returncode


def main():
    url = DEFAULT_URL
    for i, arg in enumerate(sys.argv):
        if arg == "--url" and i + 1 < len(sys.argv):
            url = sys.argv[i + 1]

    # Check if server is already running
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        already_running = s.connect_ex(("127.0.0.1", 5000)) == 0

    server_proc = None
    if not already_running:
        print("[*] Starting server...")
        server_proc = start_server()
    else:
        print("[*] Server already running on port 5000.")

    try:
        exit_code = run_playwright_checks(url)
    finally:
        if server_proc:
            server_proc.terminate()
            server_proc.wait(timeout=5)
            print("[*] Server stopped.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
