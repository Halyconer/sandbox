"""A module containing the WSGI server implementation."""

import itertools
import socket
import sys
import traceback
from collections.abc import Callable, Iterable
from io import BytesIO

from .constant import BUFFER_SIZE
from .log import print_log
from .wsgi import WSGIRequest, WSGIResponse


class WSGIServer:
    """A class representing a WSGI server."""

    def __init__(
        self,
        app: Callable,
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
        self,
        client_socket: socket.socket,
        client_address: tuple,
        app: Callable,
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

    def failure_path(self, exc_info):
        if self.response.headers_sent:
            print_log(
                f"We encountered an error on our end: {exc_info[1]} \r\n {traceback.format_exc()}",
                error=True,
            )
            self.client_socket.close()
            return
        print_log(
            f"We encountered an error on our end: {exc_info[1]} \r\n {traceback.format_exc()}",
            error=True,
        )
        self.response.body = b"Internal Server Error"
        self.response.headers = [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(self.response.body))),
            ("Connection", "close"),
        ]
        self.response.status = "500 Internal Server Error"
        response = self.response.to_http()
        self.response.headers_sent = True
        self.client_socket.sendall(response)
        self.client_socket.close()
        print_log("Client socket closed", error=True)

    def stream(self, itr: Iterable[bytes]):
        def _chunk(data: bytes) -> bytes:
            return f"{len(data):X}\r\n".encode("iso-8859-1") + data + b"\r\n"

        chunked = False
        has_length = any(
            name.lower() == "content-length" for name, _ in self.response.headers
        )
        if not has_length:
            chunked = True
            self.response.headers.append(("Transfer-Encoding", "Chunked"))
        headers_response = self.response.make_response(
            self.response.status, self.response.headers, body=b""
        )
        try:
            it = iter(itr)
            first = next(it, None)
            self.client_socket.sendall(headers_response)
            self.response.headers_sent = True
        except Exception as error:
            self.failure_path(sys.exc_info())
            return
        try:
            if first is not None:
                chunks = itertools.chain((first,), it)
            else:
                chunks = it

            for item in chunks:
                if chunked:
                    if not item:
                        continue
                    item = _chunk(item)
                self.client_socket.sendall(item)

            if chunked:
                self.client_socket.sendall(b"0\r\n\r\n")
        finally:
            close = getattr(itr, "close", None)
            if close is not None:
                close()

    def run(self):
        """Read and parse a single HTTP request"""
        try:
            while True:
                # Attempting to parse
                try:
                    parsed_request = self.read()
                    if parsed_request is None:
                        # This means that the request is incomplete
                        # so we need to try again
                        continue
                    print(f"Parsed request: {parsed_request}")
                    self.request.http_method = parsed_request["method"]
                    self.request.path = parsed_request["target"]
                    self.request.headers = parsed_request["headers"]
                    self.request.body = BytesIO(parsed_request["body"])

                except ValueError:
                    # Request was no bueno
                    print_log("The request was malformed", error=True)
                    self.response.body = b"Bad Request"
                    self.response.headers = [
                        ("Content-Type", "text/plain"),
                        ("Content-Length", str(len(self.response.body))),
                        ("Connection", "close"),
                    ]
                    self.response.status = "400 Bad Request"
                    response = self.response.to_http()
                    self.client_socket.sendall(response)
                    self.client_socket.close()
                    print_log("Client socket closed", error=True)
                    break
                # Send the request to the app to process
                try:
                    environ = self.request.to_environ()
                    chunks = self.app(environ, self.response.start_response)
                # Broad exception to handle whatever the app passes up
                except Exception as error:
                    self.failure_path(sys.exc_info())
                    break
                # Now sending back to the client
                try:
                    self.stream(chunks)
                    break
                except (ConnectionResetError, BrokenPipeError):
                    print_log("Lost connection to client, closing socket", error=True)
                    self.client_socket.close()
                    break
                except Exception as error:
                    self.failure_path(sys.exc_info())
                    break
        except (ConnectionResetError, BrokenPipeError):
            print_log("Lost connection to client, closing socket", error=True)
            self.client_socket.close()
        finally:
            self.client_socket.close()
            print_log(f"Socket closed with {self.client_address}")
