"""A module for WSGI request and response classes."""

from io import BytesIO
from typing import Any


class WSGIRequest:
    """A class representing a WSGI request."""

    def __init__(self) -> None:
        self.http_method = ""
        self.path = ""
        self.headers: dict[str, str] = {}
        self.body = BytesIO()

    def to_environ(self) -> dict[str, Any]:
        """Convert the request to a WSGI environ."""
        path_parts = self.path.split("?")
        headers_dict = self.headers
        environ = {
            "REQUEST_METHOD": self.http_method,
            "PATH_INFO": path_parts[0],
            "QUERY_STRING": path_parts[1] if len(path_parts) > 1 else "",
            "SERVER_NAME": "127.0.0.1",
            "SERVER_PORT": "5000",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "CONTENT_TYPE": headers_dict.get("content-type", ""),
            "CONTENT_LENGTH": headers_dict.get("content-length", ""),
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": self.body,
            "wsgi.errors": BytesIO(),
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            **{
                f"HTTP_{name.upper().replace('-', '_')}": value
                for name, value in self.headers.items()
                if name not in ("content-type", "content-length")
            },
        }
        return environ


class WSGIResponse:
    """A class representing a WSGI response."""

    def __init__(self) -> None:
        self.status = ""
        self.body: bytes = b""
        self.headers: list[tuple[str, str]] = []
        self.is_sent = False

    def start_response(
        self, status: str, headers: list[tuple[str, str]], exc_info=None
    ):
        """Start the response with the status and headers."""
        print("Start response with", status, headers)
        self.status = status
        self.headers = headers

    def create_status_line(self, status: str = "200 OK") -> str:
        """Create the status line for the HTTP response.
        Args:
            status (str): The status.
        Returns:
            str: The formatted status line.
        """
        return f"HTTP/1.1 {status}\r\n"

    def format_headers(self, headers: list[tuple[str, str]]) -> str:
        """Format the headers for the HTTP response.
        Args:
            headers (list): The headers.
        Returns:
            str: The formatted headers.
        """
        return "".join([f"{key}: {value}\r\n" for key, value in headers])

    def make_response(
        self,
        status: str = "200 OK",
        headers: list[tuple[str, str]] | None = None,
        body: bytes = b"",
    ):
        """Create a HTTP response from the status, headers, and body.
        Args:
            status (str): The status.
            headers (list): The headers.
            body (bytes): The body.
        Returns:
            bytes: The HTTP response.
        """
        if headers is None:
            headers = []
        content = [
            self.create_status_line(status).encode("utf-8"),
            self.format_headers(headers).encode("utf-8"),
            b"\r\n" if body else b"",
            body,
        ]
        return b"".join(content)

    def to_http(self):
        """Convert the response to a HTTP response message."""
        self.is_sent = True
        return self.make_response(self.status, self.headers, self.body)
