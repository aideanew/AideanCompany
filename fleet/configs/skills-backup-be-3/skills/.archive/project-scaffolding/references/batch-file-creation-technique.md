# Batch File Creation Technique

## Problem
When `write_file` tool fails due to WSL bash missing on Windows (error: `CreateProcessCommon:800: execvpe(/bin/bash) failed`), use `execute_code` with Python to batch-create files.

## Solution
Use Python's `os` and `open()` to create files with proper encoding and line endings:

```python
import os

project_dir = r"E:\Code\Demo\AideanSynapse\AideanSynapse_hermes"

def write(rel_path, content):
    path = os.path.join(project_dir, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f"  OK {rel_path}")
```

## Key Details
- Use `encoding='utf-8'` for Chinese content and proper Unicode support
- Use `newline='\n'` for Unix line endings on Windows
- Use `os.makedirs(exist_ok=True)` to create parent directories automatically
- Batch 10-15 files per `execute_code` call to avoid timeout
- Print file names for verification

## Go Code in Python Strings
When embedding Go code in Python strings, be careful with:
- Triple-quoted strings: `'''...'''` work but can have issues with Go `//` comments
- Single-quoted strings: `'...'` are safer for Go code
- Escape sequences: use raw strings `r'...'` when needed

Example that failed:
```python
# This caused syntax error because // was interpreted as Python comment
write("file.go", '''package main
// This comment caused issues
func main() {}
''')
```

Example that worked:
```python
# Split into separate calls or use single quotes
write("file.go", 'package main\n\nfunc main() {}')
```

## Session Results
- Created 100+ files across backend, frontend, database, deploy
- Used ~20 execute_code calls with 5-15 files each
- Total time: ~2 minutes for all file creation
