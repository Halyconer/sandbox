"""Middlewares for the application."""

import time

from wsgi.server.log import print_log

from .application import WSGIApplication


class Middleware:
    def __init__(self, application):
        self.application: WSGIApplication = application

    def __call__(self, environ, start_response):
        start = time.time()
        print_log("Hi! This is the Middleware speaking")

        def start_response_wrapper(status, headers, exc_info=None):
            return start_response(status, headers, exc_info)

        result = self.application(environ, start_response_wrapper)
        end = time.time()
        print(f"Application took {end - start} seconds.")
        return result
