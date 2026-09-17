import selectors
import socket
import sys
import traceback

from low_level_server import libclient

sel = selectors.DefaultSelector()
messages = [b"Message 1 from client.", b"Message 2 from client."]


def start_connection(host, port, request):
    """
    Start a socket connection and register it with the selector.
    Initially, the key data is set to the selected client object, and the
    socket is registered for both read and write events.
    """
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    if isinstance(request, str) and request.startswith("/"):
        message = libclient.HTTPClient(sel, sock, addr, target=request)
    else:
        message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)


def create_request(request):
    if isinstance(request, str):
        temp = request.split()
        action = temp[0].lower()
        value = temp[1].lower()
    else:
        return None

    if action == "search":
        return {
            "type": "text/json",
            "encoding": "utf-8",
            "content": {"action": action, "value": value},
        }
    else:
        return {
            "type": "binary/custom-client-binary-type",
            "encoding": "binary",
            "content": bytes(action + value, encoding="utf-8"),
        }


def main(HOST: str, PORT: int, request: str) -> None:
    try:
        # If the request is a string that starts with "/", treat it as an HTTP request and start a connection to the server.
        if request.startswith("/"):
            outgoing_request = request
        else:
            outgoing_request = create_request(request)
        if outgoing_request is None:
            print(f"Invalid request: {request}")
            sys.exit(1)
        start_connection(HOST, PORT, outgoing_request)
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)
                # A single client error must not tear down the accept loop.
                except Exception:  # noqa: BLE001
                    print(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
            # get_map returns a mapping of file objects to selector keys, checking if there
            # are any sockets being monitored. When the server has closed the connection, this
            # will be empty.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()


main("127.0.0.1", 8000, "/health")
