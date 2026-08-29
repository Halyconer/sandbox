"""Utility functions for the server."""

import argparse
from .log import print_log


def get_directory_path():
    """Get the directory path from the command line arguments.
    args:
        --directory: str: The directory path.
    returns:
        str: The directory path.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", help="the directory path")
    args = parser.parse_args()
    if not args.directory:
        return None
    return args.directory


def print_avaliabe_endpoints(app):
    """Print the available endpoints."""
    print_log("Available endpoints:")
    for route in app.router.routes:
        print_log(f"[{route.http_method}] {route.path}")
