"""Response classes for the application."""

import json
from abc import ABC, abstractmethod
from typing import Any


class BaseResponse(ABC):
    """Base response class for the application."""

    content_type = "text/plain"

    def __init__(
        self,
        status: str = "200 OK",
        headers: list[tuple[str, str]] | None = None,
        body: bytes | str | dict[Any, Any] | None = None,
    ):
        self.status = status
        self.headers = headers if headers is not None else []
        self.body = self.body_conversion(body) if body is not None else b""
        self.add_content_type_and_content_length()

    def add_content_type_and_content_length(self):
        """Add the Content-Type and Content-Length headers."""
        header_names = {name.lower() for name, value in self.headers}
        if not "Content-Type" in header_names:
            self.headers.append(("Content-Type", self.content_type))
        if self.body and not "Content-Length" in header_names:
            self.headers.append(("Content-Length", str(len(self.body))))

    @classmethod
    @abstractmethod
    def body_conversion(cls, body) -> bytes:
        """Convert the body to bytes."""


class PlainTextResponse(BaseResponse):
    """A plain text response class for the application."""

    content_type = "text/plain"

    @classmethod
    def body_conversion(cls, body) -> bytes:
        """Convert the body to bytes."""
        if isinstance(body, bytes):
            return body
        elif isinstance(body, str):
            return body.encode("utf-8")
        raise TypeError(
            f"{cls.__name__} body must be str or bytes, got {type(body).__name__}"
        )


class JSONResponse(BaseResponse):
    """A JSON response class for the application."""

    content_type = "application/json"

    @classmethod
    def body_conversion(cls, body) -> bytes:
        return json.dumps(body).encode("utf-8")


class NotFoundResponse(PlainTextResponse):
    """A not found response class for the application."""

    def __init__(self):
        super().__init__(status="404 NOT FOUND", body="Not Found")


class HTTPErrorResponse(PlainTextResponse):
    """A not found response class for the application."""

    def __init__(self, status: str, body: str):
        super().__init__(status=status, body=body)
