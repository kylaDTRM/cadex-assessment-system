[![CI](https://github.com/kylaDTRM/cadex-assessment-system/actions/workflows/ci.yml/badge.svg)](https://github.com/kylaDTRM/cadex-assessment-system/actions/workflows/ci.yml)

# cadex-assessment-system
Online Assessment &amp; Examination Platform for Universities

---

## Development setup 🔧

If you're contributing locally in this dev container, ensure your editor uses the container's Python interpreter so the language server (Pylance) resolves Django and other packages correctly.

- Use the dev container's interpreter path: `/usr/local/python/3.12.1/bin/python`.
- Recommended VS Code workspace settings (file: `.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "/usr/local/python/3.12.1/bin/python",
  "python.analysis.extraPaths": [
    "/usr/local/python/3.12.1/lib/python3.12/site-packages"
  ]
}
```

After changing settings: reload the window and restart the language server (Command Palette → "Developer: Reload Window", then "Python: Restart Language Server").

If the editor still shows missing import diagnostics, verify packages are installed in the environment:

```bash
cd backend
pip install -r requirements.txt
pip show Django djangorestframework
```

If you prefer, you can set up a virtual environment and point `python.defaultInterpreterPath` to the venv python instead.

---
