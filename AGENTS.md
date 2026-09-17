# Repository Guidelines

## What this is

A deliberately incremental Python application-engineering sandbox: small
components implemented by hand until the path socket → HTTP → WSGI → Flask →
database is legible. `README.md` is the learning plan and the source of truth
for stage order and status. It supports the `../fitness-app` work.

## Layout

- `low_level_server/` — finished socket exercises: selector-based
  multi-client echo and raw HTTP servers, adapted from Real Python's socket
  guide.
- `wsgi/server/` — hand-built WSGI server: request parsing, framing, chunked
  streaming, commit and error semantics.
- `wsgi/application/` — hand-built WSGI application: router, middleware,
  request/response classes, templates, error boundary.
- `wsgi/run.py` — demo app wiring both halves together.
- `notes/` — local study notes. Git tracks only `README.md` and `AGENTS.md`;
  other markdown is ignored.

## Commands

- `make run` — run the demo server (`.venv/bin/python wsgi/run.py`).
- `make check` — non-destructive lint and format check (`ruff`, `black`).
- `make fmt` — autofix, then format.
- Tooling is pinned in `requirements-dev.txt`; install with
  `.venv/bin/pip install -r requirements-dev.txt`.

No test framework yet. When a layer stabilizes, add focused tests under
`tests/` (for example `test_http_parser.py`, `test_health_endpoint()`).

## Style

Python 3, four-space indentation. `snake_case` for functions, variables, and
modules; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants. Prefer
the standard library in foundational exercises. Keep control flow explicit so
request boundaries, exceptions, blocking I/O, and transactions stay visible.
Comments and docstrings explain behavior; they do not restate it.

## Agent rules

**Never implement code for the user.** Do not create or modify application
code, tests, configuration, migrations, scripts, or generated artifacts. The
agent may inspect the repository, explain behavior, hint, quiz, review code,
and diagnose problems, and may show a snippet when the user is genuinely
stuck — but the user writes and applies every implementation. Exceptions:
editing this file when the user explicitly asks for a repository-instruction
change, and trivial formatting or configuration fixes that do not affect the
learning path.

Do not run the user's servers, checks, or experiments. The user runs them and
supplies the output when they want help interpreting it.

Follow the stage order in `README.md`; never introduce a framework or
abstraction ahead of the exercise that motivates it.

## Commits and pull requests

Concise, imperative subjects, optionally scoped (for example `Add raw HTTP
health endpoint`). Pull requests state the exercise or behavior changed, the
test and manual-verification commands (such as `curl -v` output), and any
known limitations or required services.
