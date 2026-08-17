# Repository Guidelines

## Project Structure & Module Organization

This is a deliberately incremental Python application-engineering sandbox. The
root `README.md` is the learning plan and architectural reference. `app.py` is
the current implementation entry point; keep early experiments small and
focused there, then split stable code into modules as the exercises introduce
WSGI, Flask, domain, infrastructure, and CLI layers. Place tests in `tests/`
and exercise notes near the code they document (for example, `notes/` or a
short `README.md`). No asset or generated-output directory is currently used.

## Build, Test, and Development Commands

There is no build system or dependency manifest yet. Run the current script
with:

```bash
python3 app.py
```

When a server is running, inspect it with commands such as
`curl -v http://127.0.0.1:8000/`. After tests are added, use
`python3 -m pytest`; keep any required local services or environment variables
documented in `README.md`.

## Coding Style & Naming Conventions

Use Python 3, four-space indentation, readable type and variable names, and
`snake_case` for functions, variables, and modules. Use `PascalCase` for
classes and `UPPER_SNAKE_CASE` for constants. Prefer the standard library in
foundational exercises, explicit control flow, and small functions that make
request boundaries, exceptions, blocking I/O, and transactions visible. Add a
formatter or linter only when the project adopts a dependency configuration.

## Testing Guidelines

No test framework or coverage threshold is configured yet. Add focused tests
under `tests/`, using names such as `test_http_parser.py` and
`test_health_endpoint()`. Test each layer as it appears: pure domain behavior
first, then socket/HTTP, application, and database boundaries. Record manual
observations from malformed or concurrent requests in notes.

## Commit & Pull Request Guidelines

There is no commit history to establish an existing convention. Use concise,
imperative subjects, optionally scoped by area (for example,
`Add raw HTTP health endpoint`). Pull requests should explain the exercise or
behavior changed, include test commands and manual verification (such as
`curl -v` output), and call out required services, configuration, or known
limitations. Include screenshots only when a user-facing interface is added.

## Agent-Specific Instructions

Follow the sequence in `README.md`. Implement and understand each exercise by
hand before introducing a framework or abstraction, and preserve observations
about failures and boundaries rather than hiding them behind libraries.

### No implementation by the agent

This is a learning project supporting `../fitness-app`. The agent must never
implement code for the user. Do not create or modify application code, tests,
configuration, migrations, scripts, or generated artifacts. The agent may
inspect the repository, explain behavior, review the user's code, diagnose
problems, and describe suggested changes in prose or pseudocode; the user
writes and applies the actual implementation. The only exception is editing
this `AGENTS.md` when the user explicitly requests a repository-instruction
change.
