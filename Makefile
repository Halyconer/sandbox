.PHONY: fmt check run

PY   := .venv/bin/python
RUFF := .venv/bin/ruff
BLACK := .venv/bin/black

# Fix in place: lint autofixes first, formatter last so it has the final say.
fmt:
	-$(RUFF) check --fix .
	$(BLACK) .

# Non-destructive: what CI should run. Fails instead of rewriting.
check:
	$(RUFF) check .
	$(BLACK) --check .

run:
	$(PY) wsgi/run.py
