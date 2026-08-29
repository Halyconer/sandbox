"""A simple WSGI application example."""

from wsgi.server import WSGIServer
from wsgi.application import WSGIApplication
from wsgi.application.request import Request
from wsgi.application.response import (
    PlainTextResponse,
)
from wsgi.application.middleware import timing_middleware

# Create a WSGI application
app = WSGIApplication(
    middleware=[
        timing_middleware,
    ]
)


# Register path operations
@app.get("/")
def index(request: Request) -> PlainTextResponse:
    """Index page."""
    routes = [route.path for route in app.router.routes]
    return PlainTextResponse(
        status="200 OK", body="\n".join(routes) if routes else "No routes found."
    )


if __name__ == "__main__":
    # Create a server
    server = WSGIServer(app, "0.0.0.0", 8081)
    server.server_forever()
