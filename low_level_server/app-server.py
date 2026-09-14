import selectors
import socket
import traceback

import low_level_server.libserver as libserver

sel = selectors.DefaultSelector()


def accept_wrapper(sock, PROTOCOL):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)

    if not PROTOCOL:
        print("No protocol specified. Closing connection.")
        conn.close()
        return
    elif PROTOCOL.lower() == "http":
        message = libserver.HTTPConnection(sel, conn, addr)
    elif PROTOCOL.lower() == "messageClass":
        message = libserver.Message(sel, conn, addr)
    else:
        print(f"Unknown protocol: {PROTOCOL}. Closing connection.")
        conn.close()
        return

    sel.register(conn, selectors.EVENT_READ, data=message)


def main(HOST: str, PORT: int, PROTOCOL: str) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            s.setblocking(False)
            sel.register(s, selectors.EVENT_READ, data=None)
            while True:
                # select blocks until there are sockets ready for I/O, or until the timeout expires
                events = sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        accept_wrapper(key.fileobj, PROTOCOL)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            print(
                                f"Main: Error: Exception for {message.addr}:\n"
                                f"{traceback.format_exc()}"
                            )
                            message.close()

    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()


main(str("127.0.0.1"), int(8000), str("http"))
