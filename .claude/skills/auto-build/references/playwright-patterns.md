# Playwright Test Patterns

Common patterns for verifying Flask apps with Playwright.

## Start server + test pattern

```python
from playwright.sync_api import sync_playwright
import subprocess, time, sys

# Start Flask
server = subprocess.Popen([sys.executable, "app.py"])
time.sleep(3)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5000")
    # ... tests ...
    browser.close()

server.terminate()
```

## Form submission

```python
page.fill("textarea[name='content']", "Test post")
page.click("button[type='submit']")
page.wait_for_timeout(1000)
assert page.locator(".post").count() > 0
```

## Wait for dynamic content

```python
page.wait_for_selector(".post", timeout=5000)
```

## Check API response

```python
response = page.goto("http://localhost:5000/api/posts")
data = response.json()
assert "posts" in data
```

## Screenshot for debugging

```python
page.screenshot(path="debug.png", full_page=True)
```

## Mobile viewport testing

```python
page.set_viewport_size({"width": 375, "height": 812})
page.goto("http://localhost:5000")
# Check layout doesn't overflow
overflow = page.evaluate(
    "document.documentElement.scrollWidth > document.documentElement.clientWidth"
)
assert not overflow, "Page has horizontal overflow on mobile"
```

## Check for console errors

```python
errors = []
page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
page.goto("http://localhost:5000")
page.wait_for_timeout(3000)
assert len(errors) == 0, f"Console errors: {errors}"
```

## File upload testing

```python
page.set_input_files("input[type='file']", "test-image.png")
page.click("button[type='submit']")
```

## Network interception

```python
def handle_route(route):
    print(f"Request: {route.request.url}")
    route.continue_()

page.route("**/*", handle_route)
```
