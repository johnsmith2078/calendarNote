# Repository Guidelines

## Project Structure & Module Organization
- Core PyQt6 app lives in `main.py` (`DiaryApp` plus custom widgets like `PlainTextEdit` and `SearchDialog`).
- Diary files are UTF-8 text under `diary_entries/YYYY/MM/YYYY-MM-DD.txt` (git-ignored); directories are created on demand.
- Build helpers: `compile_resources.py` (turns `resources.qrc` into `resources_rc.py`) and `build_with_nuitka.py` (standalone executable with icon).
- Assets sit at the repo root (`icon.ico`, `cover.png`, `resources.qrc`); project metadata in `pyproject.toml` with a `uv.lock` for dependency pinning.

## Build, Test, and Development Commands
- Install deps (Python 3.12+): `uv sync` (preferred) or `pip install -e .`.
- Run locally: `python main.py`.
- Rebuild Qt resources after changing icons/resources: `python compile_resources.py`.
- Package for Windows: `python build_with_nuitka.py` (requires Nuitka; outputs to `dist/` and embeds `icon.ico`).
- Keep generated `resources_rc.py` and personal diary files out of commits unless deliberately needed.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indents; order imports stdlib → third-party → local.
- Use snake_case for functions/variables, PascalCase for Qt classes/widgets/actions; keep signal/slot names descriptive.
- Inline comments should stay concise; user-facing strings and comments are primarily Simplified Chinese to match the existing UI tone.
- Centralize UI constants and behaviors inside `DiaryApp` methods to avoid scattered state.

## Testing Guidelines
- No automated suite yet; rely on targeted manual checks:
  - Launch with `python main.py`, create/edit today’s entry, confirm the file path matches `diary_entries/YYYY/MM/YYYY-MM-DD.txt`.
  - Switch dates to verify auto-save and the modified indicator clear correctly.
  - Exercise global search and in-page search to ensure results highlight and UI remains responsive.
- When submitting changes, include the manual steps you ran and note any areas not covered.

## Commit & Pull Request Guidelines
- Match existing history: short, action-led Chinese summaries (e.g., “添加…”, “优化…”, “修复…”); avoid mixing unrelated changes in one commit.
- PRs should state purpose, list key changes, summarize local run/test results, and attach screenshots or GIFs for UI-visible updates.
- If altering storage or build outputs, call out migration steps and keep sample diary content or generated binaries out of the PR unless explicitly required.
