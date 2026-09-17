# Application Engineering Sandbox

Hands-on companion to the backend/application-engineering track in Adrian
Glass's [`reading.md`](../adrian-glass/reading.md).

## Goal

Build a series of deliberately small components until this path is no longer
opaque:

```text
TCP socket → HTTP → WSGI → Flask → application layer → database
```

The target is not memorizing framework APIs. It is being able to trace an
unfamiliar production request, explain its failure modes, and choose sensible
boundaries between domain logic, infrastructure, and delivery.

## Working rules

- Implement each exercise by hand before asking AI for an implementation.
- AI may explain, hint, quiz, review code, and diagnose failures; it must not
  write the implementation.
- Keep every exercise small enough that the whole runtime path fits in your
  head.
- Record observations and failures in notes rather than hiding them behind a
  library.
- Use `curl -v`, logging, and a debugger to observe behavior.
- Run servers, clients, and experiments yourself; supply the output when you
  want help interpreting it.

## How to read (docs are reference, not curriculum)

- Reference docs (Flask, PEPs, library docs) assume vocabulary. Reading them
  cold is boring for everyone — read them driven by a question, not cover to
  cover.
- Build the model from narrative sources: prefer O'Reilly books. For Flask,
  *Flask Web Development* (Grinberg) is the narrative path.
- Keep a running list of words you don't know yet; review it weekly instead of
  chasing every doc link.
- Read source alongside docs. This repo exists so framework internals look
  familiar instead of magic.

## Progress

- **0–1. TCP and raw HTTP — done.** `low_level_server/`: selector-based
  multi-client echo and HTTP servers (request parsing, `/`, `/health`, 404,
  malformed-request handling).
- **2. Concurrency experiments — open, not recorded here.** Single-threaded
  vs thread-per-connection vs process workers; blocking I/O vs CPU work. Do it
  or record why it is deferred before treating the boundary as covered.
- **3. WSGI — done.** `wsgi/server/` (hand-built server: framing, chunked
  streaming, commit and error semantics) and `wsgi/application/` (router,
  request/response, error boundary, both handler middleware and real WSGI
  middleware). Outstanding: one end-to-end verification pass (200, 404, 500,
  400, poisoned header, server survives).
- **4. Flask as a WSGI application — current.**

### 4. Flask as a WSGI application

Narrow the reading to what the question needs. Read the
[application lifecycle](https://flask.palletsprojects.com/en/stable/lifecycle/)
and [request context](https://flask.palletsprojects.com/en/stable/reqcontext/)
pages as reference after finding the code they describe.

- [ ] In the installed Flask source, find `__call__` and `wsgi_app`. Trace
  setup-time route registration versus request-time route execution.
- [ ] Trace request-context creation and teardown.
- [ ] Compare a Python `try/except` boundary with Flask error-handler lookup.
- [ ] Trace `../fitness-app` from Waitress through Flask to a route. Explain
  why the same database exception becomes an HTTP response in the webhook but
  a failed process in the CLI job.

Done when you can explain, from memory: who owns the socket, who creates
`environ`, who calls the application, and what `start_response` commits to.

### 5. Application architecture

- [ ] Domain model independent of Flask and PostgreSQL.
- [ ] Repository abstraction; service layer; unit-of-work/transaction boundary.
- [ ] Translate infrastructure exceptions into application outcomes.
- [ ] Flask adapter and CLI adapter over the same application code.

Read *Architecture Patterns with Python* (cosmicpython.com) alongside this.

### 6. Production concerns

PostgreSQL transactions and isolation · idempotency and safe retries ·
background work and graceful shutdown · configuration and secrets · structured
logging and health checks · tests at unit, integration, and HTTP boundaries ·
ASGI and `asyncio` after the synchronous model is solid · containers, reverse
proxy, TLS, deployment.

## Completion test

Given a request to the fitness app's Hevy webhook, explain the path from the
network socket to the database and back. For a foreign-key failure, identify:

1. where PostgreSQL detects it;
2. how psycopg represents it in Python;
3. how it propagates through the call stack;
4. what the database context manager does;
5. which outer boundary handles it for a webhook;
6. why the nightly CLI job gets a different result; and
7. which layer translates it into an application outcome or HTTP status.

## Pacing and play

One main track at a time. Play is allowed — budget it explicitly (a bounded
side quest such as a graphics weekend), keep the same from-scratch rule, and
watch for it quietly replacing track time. If that happens, it is data, not
failure: name it and rebalance.
