# Contributing

Target Ubuntu 24.04 with Python 3.12. Create a branch for a change and keep the README and API contract consistent with the final behaviour.

```bash
sudo apt install -y build-essential iproute2 python3 python3-venv
make test
python3 -m compileall -q .
```

Use disposable child processes and ephemeral ports in tests. Never target an unrelated listener in a demonstration. Model integration checks require a separately installed local Ollama runtime and model; the unit/integration suite does not download a model.

For changes to the native interface, update the C header, ctypes argument declarations and Linux tests together. For changes to intent interpretation or stopping, test read-only requests, mismatched ports, negation, ambiguity and force handling. Document residual limitations instead of treating a successful signal send as confirmed port release.

Do not commit virtual environments, shared libraries, cache files, credentials or local sockets. Supplied PDFs are historical artifacts; update current Markdown documentation rather than silently rewriting those reports.
