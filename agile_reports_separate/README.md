# Agile Reports Separate Folder

This folder centralizes the bulky Agile-report artifacts that used to sit at the repo root.

- `data/`: SQLite/Excel exports that feed the reporting dashboards (`agile_database.db`, `Agile_Master_Data.xlsx`). The files stay here while the repository root is preserved via a hard link so existing scripts still resolve `agile_database.db`.
- `docs/`: long-form artifacts such as `AGILE_AI_AGENT_DOCS.md`.
- `scripts/`: auxiliary helpers (e.g., `reconcile_agile_metrics.py`, `Dockerfile.agile`) that belong with the exports rather than the core codebase.
- `archives/`: the packaged report exports we already generated (`.zip`, `.tar.gz`).

Moving these items reduces noise in the workspace root while keeping everything accessible from one dedicated directory.
