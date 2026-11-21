"""A small local SOCKS5 proxy for tests: no login, CONNECT only, counts what it sees.

Its exit is this machine, so it proves where traffic goes, not that the IP changes.
"""
import socket
import struct
import threading


class Socks5:
    def __init__(self, host="127.0.0.1", port=1080):
        self.addr = (host, port)
        self.connects = []        # "host:port" per CONNECT
        self.udp_requests = 0     # UDP ASSOCIATE attempts (refused)
        self.srv = socket.create_server(self.addr)
        threading.Thread(target=self._accept, daemon=True).start()

    @property
    def url(self):
        return f"socks5://{self.addr[0]}:{self.addr[1]}"

    def close(self):
        self.srv.close()

    def _accept(self):
        while True:
            try:
                conn, _ = self.srv.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    @staticmethod
    def _read(conn, n):
        data = b""
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                raise ConnectionError
            data += chunk
        return data

    def _serve(self, conn):
        try:
            ver, nmethods = self._read(conn, 2)
            self._read(conn, nmethods)
            conn.sendall(b"\x05\x00")  # no login
            ver, cmd, _, atyp = self._read(conn, 4)
            if atyp == 1:
                host = socket.inet_ntoa(self._read(conn, 4))
            elif atyp == 3:
                host = self._read(conn, self._read(conn, 1)[0]).decode()
            elif atyp == 4:
                host = socket.inet_ntop(socket.AF_INET6, self._read(conn, 16))
            else:
                raise ConnectionError
            port = struct.unpack(">H", self._read(conn, 2))[0]
            if cmd != 1:
                if cmd == 3:
                    self.udp_requests += 1
                conn.sendall(b"\x05\x07\x00\x01" + b"\0" * 6)  # command not supported
                return
            self.connects.append(f"{host}:{port}")
            up = socket.create_connection((host, port), timeout=15)
            conn.sendall(b"\x05\x00\x00\x01" + b"\0" * 6)
            threading.Thread(target=self._pipe, args=(up, conn), daemon=True).start()
            self._pipe(conn, up)
        except (OSError, ConnectionError):
            pass
        finally:
            conn.close()

    @staticmethod
    def _pipe(a, b):
        try:
            while True:
                data = a.recv(65536)
                if not data:
                    break
                b.sendall(data)
        except OSError:
            pass
        finally:
            for s in (a, b):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
