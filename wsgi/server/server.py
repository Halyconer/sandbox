"""A module containing the WSGI server implementation."""

import socket
import sys

from ..application import WSGIApplication
from .constant import BUFFER_SIZE
from .log import print_log
from .wsgi import WSGIRequest, WSGIResponse
from io import BytesIO


class WSGIServer:
    """A class representing a WSGI server."""

    def __init__(
        self,
        app: WSGIApplication,
        host: str = "localhost",
        port: int = 8080,
    ) -> None:
        self.host = host
        self.port = port
        self.app = app

    def server_forever(self):
        """Run the server."""
        # Create a TCP server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4, TCP
        server_socket.bind((self.host, self.port))  # Bind the socket to the address
        server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )  # Reuse the address
        server_socket.listen(1)  # Listen for incoming connections
        while True:
            try:
                # Wait for a connection from a TCP client
                client_socket, client_address = server_socket.accept()
                # Once a client has connected
                print_log(f"Socket established with {client_address}.")
                # Create a session for the client
                session = Connection(client_socket, client_address, self.app)
                # Run the session. For now, I want it to be blocking
                session.run()
            except KeyboardInterrupt:
                print_log("Server is shutting down.", error=True)
                server_socket.close()
                break
            except Exception as e:
                print_log(f"An error occurred: {e}", error=True)
                server_socket.close()
                break
        # Close the server socket
        server_socket.close()
        # Print the server shutdown message
        print_log("Server has been shutdown.", error=True)
        sys.exit(0)  # Exit the program


class Connection:
    """A class representing a connection.
    For now this connection will be blocking
    """

    def __init__(
        self, client_socket: socket.socket, client_address: tuple, app: WSGIApplication
    ) -> None:
        self.client_socket = client_socket
        self.client_address = client_address
        self.app = app
        self.response = WSGIResponse()
        self.request = WSGIRequest()
        self._recv_buffer = b""
        self._send_buffer = b""

    def _parse_request(self):
        header_end = self._recv_buffer.find(b"\r\n\r\n")
        if header_end == -1:
            if len(self._recv_buffer) > BUFFER_SIZE:
                raise ValueError("request headers are too large")
            return None

        header_bytes = self._recv_buffer[:header_end]
        remainder = self._recv_buffer[header_end + 4 :]

        try:
            header_text = header_bytes.decode("iso-8859-1")
        except UnicodeDecodeError as error:
            raise ValueError("request headers are not valid bytes") from error

        lines = header_text.split("\r\n")
        if not lines or not lines[0]:
            raise ValueError("missing request line")

        request_line = lines[0].split(" ")
        if len(request_line) != 3:
            raise ValueError("malformed request line")

        method, target, version = request_line
        if not version.startswith("HTTP/"):
            raise ValueError("unsupported HTTP version")

        headers = {}
        for line in lines[1:]:
            if ":" not in line:
                raise ValueError("malformed header")
            name, value = line.split(":", 1)
            name = name.strip().lower()
            if not name:
                raise ValueError("header name cannot be empty")
            headers[name] = value.strip()

        content_length = headers.get("content-length", "0")
        try:
            body_length = int(content_length)
        except ValueError as error:
            raise ValueError("content-length must be an integer") from error
        if body_length < 0:
            raise ValueError("content-length cannot be negative")
        if len(remainder) < body_length:
            return None

        body = remainder[:body_length]
        self._recv_buffer = remainder[body_length:]
        return {
            "method": method,
            "target": target,
            "version": version,
            "headers": headers,
            "body": body,
        }

    def read(self):
        # Receive data from the client socket up to BUFFER_SIZE bytes
        data = self.client_socket.recv(BUFFER_SIZE)
        self._recv_buffer += data
        if not data:
            raise ConnectionError("Client disconnected before completing the request")
        return self._parse_request()

    def run(self):
        """Read and parse a single HTTP request"""
        try:
            while True:
                parsed_request = self.read()
                if parsed_request is None:
                    # The request is incomplete
                    continue
                print(parsed_request)
                # Converting the request into digestible data for the app
                self.request.http_method = parsed_request["method"]
                self.request.path = parsed_request["target"]
                self.request.headers = parsed_request["headers"]
                self.request.body = BytesIO(parsed_request["body"])
                environ = self.request.to_environ()
                chunks = self.app(environ, self.response.start_response)
                self.response.body = b"".join(chunks)
                # the application returns a plaint text response object.
                http_bytes = self.response.to_http()
                self.client_socket.sendall(http_bytes)
                break
        except (ConnectionError, ValueError) as error:
            print(f"Connection error: {error}")
        finally:
            self.client_socket.close()
            print_log(f"Socket closed with {self.client_address}")
