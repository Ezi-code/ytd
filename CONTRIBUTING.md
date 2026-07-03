# Contributing to ytdown

Thank you for your interest! This document covers everything you need to contribute effectively.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Running Tests](#running-tests)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)

## Code of Conduct

This project is committed to providing a welcoming, inclusive experience for everyone. Be respectful, constructive, and assume good faith.

Harassment, trolling, personal attacks, and other disrespectful behavior will not be tolerated.

## Development Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [FFmpeg](https://ffmpeg.org/) (required for MP3 downloads)

### Clone and install

```bash
git clone https://github.com/your-username/ytdown
cd ytdown
uv sync
```

This creates a virtual environment and installs all dependencies including dev tools (pre-commit, ruff, codespell).

### Install the CLI in editable mode

```bash
uv tool install -e .
```

Now `ytd` is available globally and picks up changes immediately.

## Coding Standards

### Python

- Target Python 3.14+
- Use type hints for all function signatures
- Follow [PEP 8](https://peps.python.org/pep-0008/) — enforced by Ruff

### Linting & Formatting

Formatting and linting are handled entirely by Ruff. There is no separate flake8, black, or isort config.

```bash
uv run ruff check .
uv run ruff format .
```

### Style rules

- 4-space indentation, no tabs
- 100 character line limit
- Use `Path` from `pathlib` for filesystem paths, not `os.path`
- Private helpers prefixed with `_` (e.g. `_download_mp3`)
- Docstrings on public functions only; private functions use comments when needed

## Pre-commit Hooks

The project uses [pre-commit](https://pre-commit.com/) to enforce code quality on every commit.

### Install hooks

```bash
pre-commit install
```

### Run on all files

```bash
pre-commit run -a
```

### What the hooks check

| Hook          | Purpose                                |
|---------------|----------------------------------------|
| ruff          | Linting with auto-fix                  |
| ruff-format   | Code formatting                        |
| codespell     | Spelling errors                        |
| various       | Trailing whitespace, YAML/TOML/JSON validation, merge conflicts, large files |

If a hook fails, fix the issue and stage the changes before committing again.

## Running Tests

Currently there is no test suite. Manual testing:

```bash
# basic download
ytd https://youtube.com/watch?v=dQw4w9WgXcQ mp4

# audio with custom codec
ytd https://youtube.com/watch?v=dQw4w9WgXcQ mp3 flac

# playlist controls
ytd https://youtube.com/playlist?list=... --playlist-start 1 --playlist-end 3

# custom output
ytd https://youtube.com/watch?v=dQw4w9WgXcQ mp3 -o ~/Desktop
```

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

<optional body>
<optional footer>
```

### Types

| Type       | When to use                              |
|------------|------------------------------------------|
| `feat`     | New feature or option                    |
| `fix`      | Bug fix                                  |
| `refactor` | Code change with no behavior change      |
| `docs`     | README, CONTRIBUTING, or docstring edits |
| `chore`    | Tooling, CI, dependencies, config        |
| `style`    | Formatting-only changes                  |

### Examples

```
feat: add --playlist-end option for playlist range control
fix: handle missing aria2 without crashing
docs: add aria2 install instructions for macOS
chore: bump ruff to v0.11.5
```

## Pull Request Process

1. **Open an issue first** for bugs or feature requests — avoids wasted effort
2. **Fork the repo** and create a branch from `main`
   ```bash
   git checkout -b feat/my-feature
   ```
3. **Make your changes** following the coding standards above
4. **Run pre-commit** on all files
   ```bash
   pre-commit run -a
   ```
5. **Write a clear commit message** following Conventional Commits
6. **Push and open a PR** — link the related issue in the description
7. **Keep PRs small** — one feature or fix per PR

### Before submitting

- [ ] Code lints and formats cleanly (`pre-commit run -a`)
- [ ] No new spelling errors (`codespell`)
- [ ] Backward compatible unless discussed otherwise
- [ ] CLI help output updated if you added/removed arguments
- [ ] README updated if user-facing behavior changed

## Project Structure

```
ytdown/
├── ytd.py                  # CLI entry point and all download logic
├── pyproject.toml          # Project metadata, dependencies, scripts
├── .pre-commit-config.yaml # Pre-commit hook definitions
├── README.md               # User-facing documentation
├── CONTRIBUTING.md         # This file
├── .gitignore
└── uv.lock                 # Locked dependency versions
```

All code lives in a single module. Keep it that way — splitting into a package is only warranted if the logic grows substantially.
