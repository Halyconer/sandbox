"""A module for the WSGI application class."""

import sys
from collections.abc import Iterable

from .request import Request
from .response import (
    BaseResponse,
    JSONResponse,
    NotFoundResponse,
    PlainTextResponse,
)
from .router import Router
from .template import Template


class WSGIApplication:
    """A class representing a WSGI application."""

    def __init__(self, template_engine: object = None):
        """Initialize the WSGI application.
        Args:
            middleware (list[callable], optional): The middleware. Defaults to None.
            template_engine (object, optional): The template engine. Defaults to None.
        """
        self.router = Router()
        self.app_dir = self._get_app_dir()
        self.template_engine = (
            template_engine if template_engine is not None else Template
        )

    def _get_app_dir(self):
        return sys.path[0]

    def get(self, path: str):
        """Register a GET handler.
        Args:
            path (str): The path.
        Returns:
            callable: The decorator.
        """
        return self.router.get(path)

    def post(self, path: str):
        """Register a POST handler.
        Args:
            path (str): The path.
        Returns:
            callable: The decorator
        """
        return self.router.post(path)

    def put(self, path: str):
        """Register a PUT handler.
        Args:
            path (str): The path.
        Returns:
            callable: The decorator
        """
        return self.router.put(path)

    def delete(self, path: str):
        """Register a DELETE handler.
        Args:
            path (str): The path.
        Returns:
            callable: The decorator
        """
        return self.router.delete(path)

    def __call__(self, environ, start_response):
        """This is the entry point for the WSGI server.
        Args:
            environ (dict): The WSGI environment.
            start_response (callable): The start response function.
        Returns:
            list: The response body.
        """

        route_handler = self.router.get_route_handler(
            environ["PATH_INFO"], environ["REQUEST_METHOD"]
        )
        if route_handler is None:
            response = NotFoundResponse()
        else:
            request = Request.from_environ(environ)
            result = route_handler(request=request)
            if isinstance(result, dict):
                response = JSONResponse(body=result)
            elif isinstance(result, Iterable):
                start_response("200 OK", [])
                return result
            elif not isinstance(result, BaseResponse):
                response = PlainTextResponse(body=result)
            else:
                # Response is already a BaseResponse
                response = result
        start_response(response.status, response.headers)
        # This is where we would potentially need to re-raise because headers have been set
        return [response.body]
