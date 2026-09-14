# Exceptions, Error Boundaries, and `exc_info` in WSGI

Study notes from the Stage 3 "make the application raise and identify the
outer exception boundary" exercise. Written as a self-contained walkthrough:
Python mechanics first, then the HTTP contract, then PEP 3333's `exc_info`.

---

## 1. The Python mechanics: raise, propagate, catch, boundary

Three separate acts, easy to blur:

- **Raising** (`raise ValueError("boom")`, or an implicit failure like `1/0`)
  creates an exception object and *abandons* the current function immediately.
  Any code after the raise in that function never runs.
- **Propagating**: the exception travels *up* the call stack. The frame that
  raised it is popped, then the caller's frame, and so on — as if every
  function in between had also abandoned. Each frame's `finally` blocks (and
  `with` blocks) still run as it unwinds; that's how sockets and file handles
  get closed "magically" during errors.
- **Catching**: propagation stops at the *nearest enclosing* `try` whose
  `except` matches the exception's type (`except ValueError` catches
  `ValueError` and subclasses, not `TypeError`). An *unmatched* `except`
  doesn't stop anything — that frame is treated as having no handler and
  unwinding continues.

Vocabulary:

| verb | meaning |
|---|---|
| **raise** | start/restart propagation — the exception climbs the stack |
| **catch** | a matching `except` executed; propagation halted *there* |
| **handle** | the catch also produced the correct consequence (log + valid response or safe degradation) |
| **re-raise** | `raise` (bare, re-raising the current exception) or `raise X from Y` inside an `except` — propagation resumes upward |

Caught ≠ over forever. Code inside an `except` is still "during exception
handling"; if it re-raises, the *next* enclosing try gets the exception. The
handler's decision is always one of: **convert, recover, or re-raise
upward.** `from` chains the causes so the logged traceback shows both.

A **"boundary"** is a `try/except` at the outer edge of a *unit of work*,
whose job is not to fix the failure but to decide what happens to the world
outside that unit. For a server, the unit of work is "one request," and the
decision is: the client receives a valid HTTP response, and the server lives
to accept the next connection. That's the whole job of a request-level
boundary.

Two corollaries:

1. **An uncaught exception isn't "handled somewhere later."** It eventually
   hits the *interpreter*, which prints a traceback and terminates the
   running thread/program. In a server: a dead server. "We'll deal with it
   later" is only safe if a boundary genuinely exists above — the exercise is
   finding whether one does.
2. **Where you catch matters more than how you catch.** Catch too low (inside
   each handler) and every route repeats the same error logic, and you risk
   forgetting some. Catch at the request boundary and one place converts *all*
   failures into 500s. Library code almost never has a good reason to swallow
   exceptions; servers must swallow *and convert* them.

---

## 2. The call stack for one request (this repo)

```text
Connection.run                    wsgi/server/server.py:143   ← the only try in the chain
  self.app(...)                   server.py:158
    Middleware.__call__           application/middleware.py   ← no try/except
      self.application(...)       (inside __call__)
        WSGIApplication.__call__  application/application.py  ← no try/except
          route_handler(request)  e.g. index() in run.py      ← no try/except
```

So when `index` raises, there is exactly one place it can be caught —
`Connection.run`'s — and it turns out not to be a good one.

### Case A: handler raises `ValueError("boom")`

1. Unwinds up to `server.py:158`.
2. `except (ConnectionError, ValueError)` at server.py:164 matches — *by
   accident*. That clause was written for socket/parse errors, but
   `ValueError` is also what much of the stdlib raises for unrelated reasons;
   a handler's `ValueError` is indistinguishable from a malformed-request
   `ValueError` at this level.
3. It prints `"Connection error: boom"` — a *lie*; there was no connection
   problem. Classic smell of an over-broad catch: a wrong diagnosis in the log
   is worse than no log.
4. `finally` closes the socket. `curl -v` shows the connection closing with
   zero bytes received ("Empty reply to server"). No status line at all —
   not an HTTP response.
5. The server survives; the next request works.

### Case B: handler raises `RuntimeError("boom")`

1. Propagates out of `run()` — `finally` still closes the client socket —
   line 164 doesn't match, so nothing catches it there.
2. It reaches `server_forever`'s `except Exception` at server.py:48.
3. That handler prints, closes the *server* socket, and `break`s the
   `while True`. **One bad request terminates the entire server.**

Case B is the key observation of the exercise, and it mirrors a real 2002-era
lesson: WSGI was partly designed so application errors could not kill the
server. The line-48 boundary *catches* the exception but isn't a *request*
boundary — it's an accept-loop boundary conflating "one request failed" with
"the server is broken."

Today's summary: wrong-type errors → silent broken HTTP contract; right-type
errors → dead server. Neither is error *handling*; both are error *fallout*.

---

## 3. Why "close the socket" is not a substitute for "return a 500"

The HTTP contract: after a client sends a request, it is entitled to a status
line, headers, and ideally a body. Only two ways to end a request:

- **Commit a response**: `start_response` was called (status + headers
  captured), then a body sent. Once committed you can *never* send a different
  status — the client is already parsing it.
- **Abort**: close the connection before committing anything. Legitimate for
  *transport* failures (client vanished, request unparseable). Catastrophically
  ambiguous for *application* failures: the client can't distinguish "your
  server crashed" from "the network flaked," and proxies/retries treat a 500
  and an abrupt close very differently.

The rule the design should converge on:

> **An exception raised by the application before it commits a response must
> be *converted* into a committed 500 — abort is for transport-level failures
> only.**

That conversion is the boundary's job. (If the exception happens *after*
`start_response` committed a 200, conversion is impossible; abort is the only
legal move. See §6.)

Also: a 500's *body* should say something generic. Never put the exception
message or traceback into the *response* — information leakage. The traceback
belongs in the *server log*: `traceback.format_exc()` or
`logging.exception(...)` inside the `except` block. A boundary that doesn't
record the traceback turns every production incident into a mystery novel.

---

## 4. WSGI / PEP 3333 rules

- **The server must not fall over** when the application raises. It must
  consume/close `app_iter` inside error-safe machinery. This is precisely the
  guarantee Case B violates.
- **`start_response` is a commit signal**: the first call captures
  status/headers; later calls without `exc_info` should be ignored. This is
  *why* a 500 can't overwrite a committed 200.
- **The server must write no output of its own** (no stray `print`s in
  production; fine and correct in a learning server).

---

## 5. What `exc_info` is

Two related things share the name: the Python tuple, and the WSGI parameter
that borrows its shape.

### 5.1 The Python thing: `sys.exc_info()`

While code is *inside an `except` block*, Python keeps a record of the
exception being handled:

```python
sys.exc_info()  # -> (type, value, traceback)
```

| slot | example for `1/0` | what it carries |
|---|---|---|
| `type` | `ZeroDivisionError` | the exception class |
| `value` | `division by zero` | the exception instance (the message) |
| `traceback` | a traceback object | **the whole stack that unwound** — every frame, with file/line info |

The message alone doesn't tell you where it came from; the traceback slot is
what lets `traceback.format_exc()` / `logging.exception()` print the full
"Traceback (most recent call last): ..." — including frames of functions that
no longer exist on the stack. `except ValueError as error` gives you `value`;
`exc_info` is the packaged trio, including the `traceback` part `as error`
doesn't.

Key property: **`exc_info` only has meaningful content *during* exception
handling.** Outside an `except` block it is `(None, None, None)`. That fact is
the entire semantic of the WSGI parameter below.

### 5.2 The WSGI parameter: `start_response(status, headers, exc_info=None)`

`start_response` is the channel through which the app/middleware hands the
server the status line and headers. PEP 3333 allows an optional third
argument whose value is exactly that tuple. Read as:

> "Here is my status, here are my headers — and by the way, **I am calling
> you while handling this exception.**"

### 5.3 Why it exists: two designs for error middleware

Setup: an error-handling middleware wraps the app; the app raises; the
middleware catches and wants an error response sent. Two designs:

**Design A — middleware makes the 500 itself:**

```text
middleware:  except: log it; start_response("500 Internal Server Error", [html headers])
server:      ...sends it, none the wiser
```

Fine, but every middleware layer invents its own 500 page and logging, and
the server doesn't know an application error occurred.

**Design B — middleware delegates via `exc_info`:**

```text
middleware:  except: start_response("500 ...", [...], exc_info=sys.exc_info())
server:      sees exc_info non-empty and asks: have I committed a response yet?
             ├─ NO  → discards the middleware's page and handles the error at
             │        its own level (canonical 500, canonical log with full
             │        traceback). Per spec: the server re-raises the exception.
             └─ YES → cannot swap in a 500 (commit rule), so ignores the
                      delegation and aborts the response.
```

`exc_info` is the mechanism for design B: the middleware says *"I stopped the
exception from propagating, but the right owner of the error's consequence is
you, the server, at the true outer boundary — here's the original exception
info; re-raise it at your level."* It is WSGI's **cross-component re-raise**:
middleware can't literally `raise` into the server's `try` after calling
`start_response`; the callback is the only channel between them.

So the two spec rules fall out naturally:

1. "If `exc_info` is non-empty and nothing committed, the server may
   re-raise" — one component (the server) owns what a 500 looks like.
2. "If already committed, ignore it and abort" — the commit-point rule is
   physical: a 200 already in the client's terminal cannot be edited
   retroactively.

### 5.4 Mapping onto this repo

- `wsgi/server/wsgi.py` — `def start_response(self, status, headers,
  exc_info=None)`: the server's accepting-channel. Currently stores-and-drops
  it (legal: a server may not support it).
- `wsgi/application/middleware.py` — `start_response_wrapper` forwards
  `exc_info` untouched, so the middleware is currently *transparent* to all
  of §5.3 — no behavior to observe yet.
- To make it concrete: after building the request-level 500 boundary (§6
  step 3), write error middleware in design A, then design B, and diff the
  logs/responses. Design B requires the server's `start_response` to *do*
  something when `exc_info` is non-empty and nothing was committed — the
  first line of WSGI-spec code written deliberately.

**TL;DR:** `exc_info` = the `(type, value, traceback)` tuple Python exposes
while an exception is being handled, passed through `start_response`'s
optional third argument as a note from app/middleware to server saying "I
caught something; you decide the error response."

---

## 6. A generator subtlety (connects to Fluent Python ch. 6)

The app returns `[response.body]` — a **list**, fully constructed *before*
`app(...)` returns — so any handler exception surfaces at server.py:158,
*before* `start_response` runs. That's why "convert to 500" is even possible.

If the app instead yielded chunks lazily (a generator), an exception could
surface at the `b"".join(chunks)` on server.py:159, *after* a 200 was
committed on line 158. Then the boundary must **not** try to send a 500 —
headers are gone; the only correct action is abort + log. The difference in
*when* an exception arrives relative to the commit point is the deep reason
`start_response` exists as a separate callback instead of the app just
returning a `Response` object. The bug only exists in the lazy design — worth
demonstrating deliberately once the error boundary is in place.

---

## 7. The experiment sequence

1. **Observe before fixing:**
   - `raise ValueError("boom")` in `index`; run server;
     `curl -v http://127.0.0.1:8081/`. Record what curl prints (no status
     line) and the misleading log line.
   - Change to `raise RuntimeError("boom")`; same curl; confirm the server
     process exits and a second `curl` fails with connection refused.
   - Raise from a route vs from template/response code vs from the middleware;
     see whether the catch site differs.
2. **Design the boundary in prose (no code yet):** should the try/except live
   in `Connection.run`, or in `server_forever` around `session.run()`? What
   does each choice *not* protect? The `server_forever` loop around
   `session.run()` is the per-connection boundary; the try inside `run()`
   (lines 145–162) is the per-request one. Separately: why does the
   accept-loop handler at line 48 currently `break` where it should probably
   `continue`?
3. **Implement:** a request-level try/except that
   (a) logs the full traceback with the request method/path,
   (b) commits a generic 500 *only if* nothing has been committed yet, else
   aborts, and
   (c) keeps parse/socket failures distinguishable from application failures
   in the log.
4. **Verify:** `curl -v` shows a real `HTTP/1.1 500`; the server stays up;
   logs show a traceback naming the actual raise site. Then optionally add
   the design-A vs design-B error middleware (§5.4) and compare against
   Flask's `@app.errorhandler`, coming in Stage 4.

---

## Mental model

**Exceptions are control flow that only the owner of a *consequence* should
intercept, and a server's only legitimate consequence for an unknown
application failure is: log the truth, send a valid response, stay alive.**

The Stage 3 checklist item is just verifying, by experiment, who currently
decides those consequences in this code — the answer being "nobody, in two
different ways."

---

## 8. Status (2026-09-04, mid-stage)

- **App layer:** handler exceptions propagate transparently (no internal
  catch in `WSGIApplication.__call__`).
- **Server layer:** `Connection.run()` is a three-phase boundary
  (parse → app → send). Malformed requests get a real 400; the server backstop
  keeps the accept loop alive; `server_forever` continues on non-fatal errors.
- **Response state machine:** `WSGIResponse` has `headers_set` and
  `headers_sent`; `start_response` implements all four branches
  (first store / `AssertionError` / replace / re-raise). `to_http` no longer
  sets a wire flag — `Connection` flips `headers_sent` after `sendall`.
- **Error middleware (design B) implemented:** `Middleware.__call__` catches,
  logs the traceback, builds `HTTPErrorResponse`, and calls
  `start_response(..., sys.exc_info())`. On `/crash` (crash before commit)
  the exc_info call takes the replace branch; the middleware's 500 body
  ("Internal Server Error, please try again") is the observable.
- **Response classes:** `BaseResponse` is an `ABC` with abstract
  `body_conversion` (`@classmethod` over `@abstractmethod`); subclasses own
  their conversion (plain str/bytes, JSON via `json.dumps`); `content_type`
  is a class attribute only.

## 9. Header validation (2026-09-04, later)

Per PEP 3333: *validate malformed input inside `start_response` (while the
app is still running and the error is catchable), fill in missing required
headers at send time.* Implemented:

- `wsgi/server/validators.py` — pure functions: `validate_status`
  (str, `"999 Reason"` shape, no control chars), `validate_headers`
  (list of 2-tuples of str, no control chars — CR/LF injection defense —
  no hop-by-hop headers from the app).
- Wired into `WSGIResponse.start_response` **after** the store, so a failed
  validation leaves `headers_set = True` and the app's only legal retry is
  with `exc_info` — the PEP's reference-implementation ordering.
- Flow to observe: validator raises `ValueError` inside the app's
  `start_response` call → propagates through the app → middleware catches →
  retry with `exc_info` → replace branch → the middleware's 500 ships.

Known leftovers:

- `response.py` checks header presence case-sensitively
  (`"Content-Type" in header_names`); the spec says names are
  case-insensitive — a lowercase `content-type` app header yields a
  duplicate. Fix: compare `.lower()`.
- Typed exceptions (`AppError`-style: intentional client-facing status +
  message vs unexpected bug → generic body, full truth in the log) — the
  two-tier dispatch that previews Flask's `HTTPException` + errorhandler.
- `response.py:3` still imports the deprecated `abstractclassmethod`
  (unused); delete the line.
- `HTTPErrorResponse` docstring says "A not found response class" (copy-paste).

## 10. Next stage

1. **Verify end-to-end** (run server + curl): `/` → 200 with middleware
   timing log; `/crash` → 500 with the *middleware's* body; `/nonexistent`
   → 404; malformed request → 400; server stays alive throughout. Then a
   poisoned-header test: a header value containing `\r\n` must be rejected
   by the validator → 500, not injected onto the wire.
2. **Iterable app + streaming.** Requires generators first: the app must
   yield chunks and fail mid-iteration, and the server must send incrementally
   (today `b"".join(chunks)` buffers the whole iterable *before*
   `headers_sent` flips) so `headers_sent` can become `True` before the
   iterable is exhausted. This is the only way the fourth (re-raise/abort)
   branch becomes reachable in live traffic.
   - *Before this piece:* read the iterables/iterators/generators chapter in
     Fluent Python.
   - *Decision to record:* implement `write()` (the spec says
     `start_response` must return it) or consciously skip it; keep the
     block-boundary rule (yield at least once per underlying yield).

Deferred:

- Flask (Stage 4) is moved after the middleware experiments, so Flask's error
  handlers are read as *recognition* rather than magic. After that, return to
  `fitness-app` to trace its Flask + Waitress request path.
