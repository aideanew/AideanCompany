# Browser Testing Workflow for Project Scaffolding

## Problem
Vite dev servers use HMR WebSocket for hot-reload. When the Hermes browser tool connects to a Vite dev server, the WebSocket connection fails (remote browser can't reach localhost WS), causing React to render a blank page even though HTML/JS load correctly.

## Solution: Production Build + Static Server

### 1. Build All Apps
```bash
cd frontend/apps/admin && npm run build
cd frontend/apps/console && npm run build
cd frontend/apps/public && npm run build
```

### 2. Serve with Node.js Static Server

Create `static.js`:
```javascript
const http = require('http');
const fs = require('fs');
const path = require('path');

const port = process.argv[2] || 8001;
const mimeTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
};

const server = http.createServer((req, res) => {
    let filePath = req.url === '/' ? '/index.html' : req.url;
    filePath = path.join(process.cwd(), filePath);
    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || 'application/octet-stream';
    try {
        const content = fs.readFileSync(filePath);
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content);
    } catch (err) {
        res.writeHead(404);
        res.end('Not Found');
    }
});
server.listen(port, () => console.log(`Serving on port ${port}`));
```

### 3. Start Servers (Windows PowerShell)

```python
import subprocess

server_file = r'C:\Users\<user>\server\static.js'
dist_dir = r'E:\path\to\app\dist'

# Start-Process properly sets WorkingDirectory (unlike shell=True cwd)
ps_cmd = f'Start-Process -FilePath node -ArgumentList "{server_file}", "8001" -WorkingDirectory "{dist_dir}" -WindowStyle Hidden'
subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], shell=True)
```

**Key**: Use `Start-Process -WorkingDirectory` — NOT `subprocess.Popen(cwd=...)` with `shell=True`, which doesn't properly set the working directory on Windows.

### 4. Verify with Socket
```python
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 8001))
s.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
response = b''
while True:
    chunk = s.recv(8192)
    if not chunk: break
    response += chunk
body = response.split(b'\r\n\r\n', 1)[1].decode() if b'\r\n\r\n' in response else ''
print(f"OK: {len(body)} bytes, has_bundle={'assets/' in body}")
```

## Known Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `pnpm dev` exits with code 1 | `runDepsStatusCheck` fails | Use `npm run dev` from app dir |
| `python -m http.server` returns empty | Connection handling bug on Windows | Use Node.js static server |
| `subprocess.Popen(cwd=..., shell=True)` wrong dir | `shell=True` ignores `cwd` | Use PowerShell `Start-Process -WorkingDirectory` |
| Vite dev server blank in browser | HMR WebSocket can't connect | Build production and serve `dist/` |
| Old node processes on ports | Previous sessions left running | Kill with `Stop-Process -Id <pid> -Force` |
