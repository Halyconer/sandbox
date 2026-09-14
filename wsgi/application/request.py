"""Request class for handling incoming requests."""

from dataclasses import dataclass


@dataclass
class Request:
    """A class representing a request."""

    query: dict[str, str]
    body: bytes
    headers: dict[str, str]

    @classmethod
    def from_environ(cls, environ: dict):
        """Create a request from a WSGI environ.
        Args:
            environ (dict): The WSGI environ.
        Returns:
            Request: The request object.
        """
        query = {}
        if environ["QUERY_STRING"]:
            qs = environ["QUERY_STRING"]
            query = (
                dict(entry.split("=") for entry in qs.split("&"))
                if qs.count("=") > 0
                else {qs: None}
            )
        body = environ["wsgi.input"].read()
        headers = {
            k.replace("HTTP_", ""): v
            for k, v in environ.items()
            if k.startswith("HTTP_")
        }
        return cls(query, body, headers)
