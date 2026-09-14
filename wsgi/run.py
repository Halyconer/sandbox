"""A simple WSGI application example."""

import re
import reprlib
from collections.abc import Generator, Iterable, Iterator

from wsgi.application import WSGIApplication, middleware
from wsgi.application.request import Request
from wsgi.application.response import (
    PlainTextResponse,
)
from wsgi.server import WSGIServer

# Create a WSGI application
app = WSGIApplication()

# Instantiate the Middleware
middleware = middleware.Middleware(app)


# Register path operations
@app.get("/")
def index(request: Request) -> PlainTextResponse:
    """Index page."""
    routes = [route.path for route in app.router.routes]
    return PlainTextResponse(
        status="200 OK", body="\n".join(routes) if routes else "No routes found."
    )


@app.get("/crash")
def crash(request: Request) -> PlainTextResponse:
    """This is for testing crashes in the app and seeing where and how they get handled"""
    raise RuntimeError("Forced error for validation")


@app.get("/words")
def words(request: Request) -> Iterator[bytes]:
    """Path to create an iterable to pass to server"""
    RE_WORD = re.compile(r"\w+")
    text = "Roses are red, violets are blue, I am a potato, and so aren't you"
    return (match.group().encode("utf-8") for match in RE_WORD.finditer(text))


@app.get("/faulty_words")
def faulty_words(request: Request) -> Iterator[bytes]:
    """A faulty iterator will be raised, with the intention of testing what will happen once headers are set and an error is raised"""

    def generator():
        yield "Hello"
        yield 1 / 0

    return (str(x).encode("utf-8") for x in generator())


if __name__ == "__main__":
    # Create a server
    server = WSGIServer(middleware, "0.0.0.0", 8081)
    server.server_forever()
