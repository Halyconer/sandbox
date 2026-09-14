"""Validation of WSGI status and response headers per PEP 3333."""

import re

# Control characters: names forbid all (incl. CR/LF); values forbid all
# except horizontal tab (\x09), which RFC 9110 allows in field values.
_NAME_DISALLOWED = re.compile(r"[\x00-\x1F\x7F]")
_VALUE_DISALLOWED = re.compile(r"[\x00-\x08\x0A-\x1F\x7F]")

# HTTP/1.1 hop-by-hop headers: the application may never supply these.
HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


def validate_status(status):
    """Raise unless status is a str of the form '999 Reason'."""
    if not isinstance(status, str):
        raise TypeError(f"Status must be str, got {type(status).__name__}")
    if _NAME_DISALLOWED.search(status):
        raise ValueError("Control characters are not allowed in status")
    if len(status) < 4:
        raise ValueError("Status must be at least 4 characters")
    if not status[:3].isdigit():
        raise ValueError("Status must begin with a 3-digit code")
    if status[3] != " ":
        raise ValueError("Status must have a single space after the code")
    return status


def validate_headers(headers):
    """Raise unless headers is a list of legal (name, value) str tuples."""
    if not isinstance(headers, list):
        raise TypeError(f"Headers must be a list, got {type(headers).__name__}")
    for index, pair in enumerate(headers):
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise TypeError(
                f"Header {index} must be a (name, value) tuple, got {pair!r}"
            )
        name, value = pair
        if not isinstance(name, str):
            raise TypeError(
                f"Header name {index} must be str, got {type(name).__name__}"
            )
        if not isinstance(value, str):
            raise TypeError(
                f"Header value {index} must be str, got {type(value).__name__}"
            )
        if _NAME_DISALLOWED.search(name):
            raise ValueError(f"Control character in header name {name!r}")
        if _VALUE_DISALLOWED.search(value):
            raise ValueError(f"Control character in header value {value!r}")
        if name.lower() in HOP_BY_HOP:
            raise ValueError(f"Hop-by-hop header forbidden from WSGI apps: {name!r}")
    return headers
