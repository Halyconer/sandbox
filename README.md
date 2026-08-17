# Application Engineering Sandbox

This repository is the hands-on companion to the backend/application-engineering
track documented in Adrian Glass's [`reading.md`](../adrian-glass/reading.md).

## Goal

Build a series of deliberately small components until this path is no longer
opaque:

```text
TCP socket → HTTP → WSGI → Flask → application layer → database
```

The architectural goal is to understand where requests, exceptions,
transactions, blocking I/O, and process boundaries enter a real application.
The target is not to memorize framework APIs. It is to be able to trace an
unfamiliar production request, explain its failure modes, and choose sensible
boundaries between domain logic, infrastructure, and delivery mechanisms.

## Working rules

- Implement the exercises by hand before asking AI for an implementation.
- AI can explain a concept, provide a small hint, quiz understanding, review
  code, or help diagnose an observed failure.
- Keep each exercise small enough that the complete runtime path can be held in
  mind.
- Record observations and failures in the exercise's notes rather than hiding
  them behind a library.
- Use `curl -v`, logging, and a debugger to observe behavior.
- Run checks, servers, clients, and manual experiments yourself. The agent may
  inspect and review the files, but should not execute checks or experiments;
  provide the output when you want help interpreting it.

## Task sequence

The order below is the consolidated learning path. Implement each stage by
hand, record what you observe, and do not move on until you can explain the
boundary it introduces.

### 0. Multi-connection TCP bridge

Read the multi-connection client/server section of [Real Python's socket
guide](https://realpython.com/python-sockets/#multi-connection-client-and-server)
and finish a small TCP echo server in this sandbox using `selectors`.

- [ ] Create and register the listening socket before entering the event loop.
- [ ] Accept multiple clients without blocking on one client.
- [ ] Keep per-client input/output state.
- [ ] Handle partial `recv()` and `send()` operations.
- [ ] Unregister and close clients cleanly.
- [ ] Test several clients, a slow client, disconnects, and Ctrl-C shutdown.

The optional application-protocol section of the article is useful background
for message framing, but the next concrete protocol here is HTTP.

### 1. Raw HTTP over TCP

- [ ] Create a TCP socket bound to `127.0.0.1:8000`.
- [ ] Accept connections and print the raw request bytes.
- [ ] Return a valid `200 OK` response with `Content-Length`.
- [ ] Add `/`, `/health`, and a 404 response.
- [ ] Parse the request method and path without using a web framework.
- [ ] Send malformed requests and document what happens.
- [ ] Add a slow handler and observe that the single-threaded server blocks.

Questions to answer:

- What is the difference between `bind`, `listen`, and `accept`?
- Which socket represents the listening endpoint and which represents one
  client connection?
- Why does `recv()` return bytes rather than a complete HTTP request?
- Why does the response need `\r\n` and `Content-Length`?
- What happens to the process when the handler raises an exception?

### 2. Concurrency experiments

- [ ] Compare the single-threaded server with a thread-per-connection version.
- [ ] Add process workers and compare the behavior.
- [ ] Use concurrent requests to distinguish blocking I/O from CPU work.
- [ ] Write down what state is shared between requests, threads, and processes.

### 3. WSGI

- [ ] Implement a callable `app(environ, start_response)`.
- [ ] Run it with Python's development WSGI server.
- [ ] Inspect the important keys in `environ`.
- [ ] Add middleware that logs the method and path.
- [ ] Make the application raise and identify the outer exception boundary.

Read [PEP 3333](https://peps.python.org/pep-3333/) while implementing this
section. Do not proceed until the server/application calling convention is
clear.

Finish this stage before studying Flask. The goal is to understand who owns
the socket, who creates `environ`, who calls the application, and what
`start_response` represents.

### 4. Flask as a WSGI application

- [ ] Read Flask's [application lifecycle](https://flask.palletsprojects.com/en/stable/lifecycle/)
  and [request context](https://flask.palletsprojects.com/en/stable/reqcontext/)
  documentation.
- [ ] Locate Flask's `__call__` and `wsgi_app` methods in the installed source.
- [ ] Trace setup-time route registration versus request-time route execution.
- [ ] Trace request-context creation and teardown.
- [ ] Compare a Python `try/except` boundary with Flask error-handler lookup.
- [ ] Trace `../fitness-app` from its server boundary through Flask and a route.
- [ ] Explain why the same database exception can become an HTTP response in a
  webhook but a failed process in a CLI job.

In `fitness-app`, `dev_server.py` uses Flask's development server, while the
Dockerfile uses Waitress. In both cases, the server owns the sockets and calls
the Flask WSGI application.

### 5. Application architecture

- [ ] Build a small domain model independent of Flask and PostgreSQL.
- [ ] Add a repository abstraction.
- [ ] Add a service layer for use-case orchestration.
- [ ] Add a unit-of-work or transaction boundary.
- [ ] Translate infrastructure exceptions into application-level outcomes.
- [ ] Connect the Flask adapter and a CLI adapter to the same application code.

Read the relevant chapters of [Architecture Patterns with Python](https://www.cosmicpython.com/)
while building these components.

### 6. Production concerns

- [ ] PostgreSQL transactions and isolation.
- [ ] Idempotency and safe retries.
- [ ] Background work and graceful shutdown.
- [ ] Configuration and secrets.
- [ ] Structured logging and health checks.
- [ ] Tests at unit, integration, and HTTP boundaries.
- [ ] ASGI and `asyncio` after the synchronous model is understood.
- [ ] Containerization, reverse proxying, TLS, and deployment.

## Completion test

Given a request to the fitness app's Hevy webhook, explain the path from the
network socket to the database and back. For a foreign-key failure, identify:

1. where PostgreSQL detects the problem;
2. how psycopg represents it in Python;
3. how Python propagates it through the call stack;
4. what the database context manager does;
5. which outer boundary handles it for a webhook;
6. why the nightly CLI job has a different result; and
7. which layer should translate it into an application outcome or HTTP status.
