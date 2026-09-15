"""Middlewares for the application."""

import sys
import time
import traceback

from wsgi.application.response import HTTPErrorResponse

from .application import WSGIApplication


class Middleware:
    def __init__(self, application):
        self.application: WSGIApplication = application

    def __call__(self, environ, start_response):
        start = time.time()

        def start_response_wrapper(status, headers, exc_info=None):
            return start_response(status, headers, exc_info)

        try:
            result = self.application(environ, start_response_wrapper)
        except Exception:
            traceback.print_exc()
            status = "500 Internal Server Error"
            response = HTTPErrorResponse(
                status, body="Internal Server Error, please try again"
            )
            start_response(response.status, response.headers, sys.exc_info())
            return [response.body]
        end = time.time()
        print(f"Application took {end - start} seconds.")
        return result

    def _join(self, data):
        """Stub for a future self-made join, which will will be a Callable passed to the server, allowing the Middleware to raise in case of a Generator mishap in the future"""
