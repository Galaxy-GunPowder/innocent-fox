"""Local test lab: what a website's servers see from a browser, with no outside site.

One HTTPS server on localhost offers HTTP/2, a second offers HTTP/1.1 only, and a
plain HTTP server serves the bot test. Each records, per browser run:

  TLS        the ClientHello (ciphers, extensions in order, groups, ALPN ...), JA3, JA4
  HTTP/2     SETTINGS in order, WINDOW_UPDATE, PRIORITY frames, pseudo-header order,
             header order: the Akamai HTTP/2 fingerprint
  HTTP/1.1   header order and values

The browser trusts the servers through a local test CA, added to the run's own
temporary profile with NSS certutil (never to Windows or another profile).
"""
import hashlib
import json
import shutil
import socket
import ssl
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import h2.config
import h2.connection
import h2.events
import hpack

HERE = Path(__file__).resolve().parent
WORK = Path(r"D:\ifox")
CA_DIR = WORK / "identity" / "lab-ca"
CERTUTIL = WORK / "obj" / "dist" / "bin" / "certutil.exe"   # NSS tool from our build, with its DLLs
GREASE = {f"{b:02x}{b:02x}" for b in range(0x0a, 0x100, 0x10)}


# ---------------------------------------------------------------- certificates

def certs():
    """Local test CA and a localhost certificate, made once."""
    ca_pem, key_pem, cert_pem = CA_DIR / "ca.pem", CA_DIR / "localhost-key.pem", CA_DIR / "localhost.pem"
    if cert_pem.exists():
        return ca_pem, cert_pem, key_pem
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    CA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ifox identity lab CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=3650))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
          .sign(ca_key, hashes.SHA256()))
    key = ec.generate_private_key(ec.SECP256R1())
    leaf = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
            .issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(ca_key, hashes.SHA256()))
    ca_pem.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_pem.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_pem.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    return ca_pem, cert_pem, key_pem


def trust(profile):
    """Make a fresh profile folder trust the lab CA (before the browser starts)."""
    ca_pem, _, _ = certs()
    db = f"sql:{profile}"
    run = lambda *a: subprocess.run([str(CERTUTIL), *a], cwd=CERTUTIL.parent, check=True,  # noqa: E731
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run("-N", "-d", db, "--empty-password")
    run("-A", "-n", "ifox-lab", "-t", "C,,", "-i", str(ca_pem), "-d", db)


# ---------------------------------------------------------------- TLS ClientHello

def parse_client_hello(data):
    """Everything in a ClientHello except random values, extension order kept."""
    if len(data) < 6 or data[0] != 0x16 or data[5] != 0x01:
        return {"error": "not a ClientHello", "first_bytes": data[:8].hex()}
    p = 9
    out = {"record_version": data[1:3].hex(), "legacy_version": data[p:p + 2].hex()}
    p += 2 + 32
    out["session_id_length"] = data[p]
    p += 1 + data[p]
    n = int.from_bytes(data[p:p + 2], "big"); p += 2
    out["ciphers"] = [data[i:i + 2].hex() for i in range(p, p + n, 2)]; p += n
    out["compression"] = list(data[p + 1:p + 1 + data[p]])
    p += 1 + data[p]
    end = p + 2 + int.from_bytes(data[p:p + 2], "big"); p += 2
    ext_order, lengths, details = [], {}, {}
    u16s = lambda b: [b[i:i + 2].hex() for i in range(0, len(b) - 1, 2)]  # noqa: E731
    while p + 4 <= end:
        t = int.from_bytes(data[p:p + 2], "big"); ln = int.from_bytes(data[p + 2:p + 4], "big")
        body = data[p + 4:p + 4 + ln]; p += 4 + ln
        name = f"{t:04x}"
        ext_order.append(name)
        if t not in (0x0015, 0x0029, 0x0033, 0xfe0d):      # padding, PSK, key shares, ECH vary in size
            lengths[name] = ln
        if t == 0x0000:
            details["server_name"] = body[5:].decode(errors="replace")
        elif t == 0x000a:
            details["supported_groups"] = u16s(body[2:])
        elif t == 0x000d:
            details["signature_algorithms"] = u16s(body[2:])
        elif t == 0x0032:
            details["signature_algorithms_cert"] = u16s(body[2:])
        elif t == 0x0010:
            q, alpn = 2, []
            while q < len(body):
                alpn.append(body[q + 1:q + 1 + body[q]].decode()); q += 1 + body[q]
            details["alpn"] = alpn
        elif t == 0x002b:
            details["supported_versions"] = u16s(body[1:])
        elif t == 0x0033:
            q, groups = 2, []
            while q + 4 <= len(body):
                kl = int.from_bytes(body[q + 2:q + 4], "big")
                groups.append(f"{body[q:q + 2].hex()}/{kl}"); q += 4 + kl
            details["key_shares"] = groups
        elif t == 0x000b:
            details["ec_point_formats"] = list(body[1:])
        elif t == 0x002d:
            details["psk_modes"] = list(body[1:])
        elif t == 0x001c:
            details["record_size_limit"] = int.from_bytes(body, "big")
        elif t == 0x001b:
            details["compress_certificate"] = u16s(body[1:])
        elif t == 0x0022:
            details["delegated_credentials"] = u16s(body[2:])
        elif t == 0x0005:
            details["status_request"] = body.hex()
        elif t == 0xff01:
            details["renegotiation_info"] = body.hex()
        elif t == 0xfe0d:
            # Firefox sends a decoy (GREASE) ECH with a cipher picked at random per connection: keep the type only.
            details["ech"] = {"type": body[0] if body else None}
        elif t == 0x0015:
            details["padding"] = True
    out["extension_order"] = ext_order
    out["extension_lengths"] = lengths
    out.update(details)
    out["ja3"], out["ja3_hash"] = ja3(out)
    out["ja4"] = ja4(out)
    return out


def ja3(h):
    dec = lambda xs: "-".join(str(int(x, 16)) for x in xs if x not in GREASE)  # noqa: E731
    s = ",".join([str(int(h["legacy_version"], 16)), dec(h["ciphers"]), dec(h["extension_order"]),
                  dec(h.get("supported_groups", [])), "-".join(str(x) for x in h.get("ec_point_formats", []))])
    return s, hashlib.md5(s.encode()).hexdigest()


def ja4(h):
    """JA4 TLS client fingerprint (FoxIO spec), for TCP."""
    ciphers = [c for c in h["ciphers"] if c not in GREASE]
    exts = [e for e in h["extension_order"] if e not in GREASE]
    versions = [v for v in h.get("supported_versions", []) if v not in GREASE]
    top = max(versions) if versions else h["legacy_version"]
    ver = {"0304": "13", "0303": "12", "0302": "11", "0301": "10"}.get(top, "00")
    alpn = (h.get("alpn") or [""])[0]
    a = f"t{ver}{'d' if '0000' in exts else 'i'}{min(len(ciphers), 99):02d}{min(len(exts), 99):02d}" \
        f"{(alpn[0] + alpn[-1]) if alpn else '00'}"
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12] if s else "000000000000"  # noqa: E731
    b = sha(",".join(sorted(ciphers)))
    c_in = ",".join(sorted(e for e in exts if e not in ("0000", "0010")))
    sig = ",".join(h.get("signature_algorithms", []))
    c = sha(c_in + (f"_{sig}" if sig else ""))
    return f"{a}_{b}_{c}"


# ---------------------------------------------------------------- HTTP/2 frames

H2_SETTINGS = {1: "HEADER_TABLE_SIZE", 2: "ENABLE_PUSH", 3: "MAX_CONCURRENT_STREAMS", 4: "INITIAL_WINDOW_SIZE",
               5: "MAX_FRAME_SIZE", 6: "MAX_HEADER_LIST_SIZE", 8: "ENABLE_CONNECT_PROTOCOL", 9: "NO_RFC7540_PRIORITIES"}


class H2Sniffer:
    """Reads the client's raw HTTP/2 bytes and records the frames that identify a browser."""

    def __init__(self):
        self.buf, self.preface_done = b"", False
        self.decoder = hpack.Decoder()
        self.settings = None
        self.window_update = None
        self.priority_frames = []
        self.frame_order = []
        self.headers = []            # (stream, flags, priority, [(name, value)])

    def feed(self, data):
        self.buf += data
        if not self.preface_done:
            if len(self.buf) < 24:
                return
            self.buf, self.preface_done = self.buf[24:], True
        while len(self.buf) >= 9:
            ln = int.from_bytes(self.buf[:3], "big")
            if len(self.buf) < 9 + ln:
                return
            ftype, flags, stream = self.buf[3], self.buf[4], int.from_bytes(self.buf[5:9], "big") & 0x7fffffff
            payload, self.buf = self.buf[9:9 + ln], self.buf[9 + ln:]
            if len(self.frame_order) < 12:
                self.frame_order.append(f"{ftype}:{stream}")
            if ftype == 4 and not flags & 1 and self.settings is None:
                self.settings = [(int.from_bytes(payload[i:i + 2], "big"), int.from_bytes(payload[i + 2:i + 6], "big"))
                                 for i in range(0, len(payload), 6)]
            elif ftype == 8 and stream == 0 and self.window_update is None:
                self.window_update = int.from_bytes(payload[:4], "big") & 0x7fffffff
            elif ftype == 2:
                dep = int.from_bytes(payload[:4], "big")
                self.priority_frames.append((stream, dep >> 31, dep & 0x7fffffff, payload[4] + 1))
            elif ftype == 1:
                p, prio = 0, None
                if flags & 0x08:
                    p = 1                                   # pad length byte
                if flags & 0x20:
                    dep = int.from_bytes(payload[p:p + 4], "big")
                    prio = (dep >> 31, dep & 0x7fffffff, payload[p + 4] + 1); p += 5
                block = payload[p:len(payload) - (payload[0] if flags & 0x08 else 0)]
                try:
                    hdrs = [(k.decode() if isinstance(k, bytes) else k, v.decode() if isinstance(v, bytes) else v)
                            for k, v in self.decoder.decode(block)]
                except Exception as e:                      # CONTINUATION frames are not expected from Firefox
                    hdrs = [("<hpack error>", str(e))]
                self.headers.append((stream, flags, prio, hdrs))

    def summary(self):
        first = self.headers[0] if self.headers else None
        pseudo = [k[1] for k, _ in first[3] if k.startswith(":")] if first else []
        akamai = "|".join([
            ";".join(f"{k}:{v}" for k, v in self.settings or []),
            str(self.window_update or 0),
            ",".join(f"{s}:{e}:{d}:{w}" for s, e, d, w in self.priority_frames) or "0",
            ",".join(pseudo),
        ])
        return {
            "settings": [f"{H2_SETTINGS.get(k, k)}={v}" for k, v in self.settings or []],
            "window_update": self.window_update,
            "priority_frames": self.priority_frames,
            "first_frames": self.frame_order,
            "first_headers_priority": first[2] if first else None,
            "first_headers_flags": first[1] if first else None,
            "akamai": akamai,
        }


# ---------------------------------------------------------------- servers

class Lab:
    """Servers for one browser run. lab.url() is the page to open; lab.done waits for the result."""

    def __init__(self, page="probe.html"):
        self.page = page
        self.stage = "page not loaded"
        self.done = threading.Event()
        self.result = None
        self.hellos, self.h2, self.requests = [], [], {}
        _, cert, key = certs()
        self._socks = []
        self.h2_port = self._tls_server(cert, key, ["h2", "http/1.1"])
        self.h1_port = self._tls_server(cert, key, ["http/1.1"])
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), self._plain_handler())
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def url(self, secure=True, **query):
        q = {"h1": self.h1_port, "h2": self.h2_port, **query}
        qs = "&".join(f"{k}={v}" for k, v in q.items())
        if secure:
            return f"https://localhost:{self.h2_port}/{self.page}?{qs}"
        return f"http://127.0.0.1:{self.http.server_address[1]}/{self.page}?{qs}"

    def close(self):
        self.http.shutdown()
        for s in self._socks:
            s.close()

    # routing, shared by every server
    def respond(self, method, path, headers, body, proto):
        if path.startswith("/stage?"):
            self.stage = path[7:]
            return 204, "text/plain", b""
        path = path.split("?")[0]
        names = [k for k, _ in headers]
        values = {k: v for k, v in headers if k.lower() not in ("host", ":authority", "referer", "cookie")}
        if method == "GET" and path == f"/{self.page}":
            self.requests.setdefault(f"document_{proto}", (names, values))
            self.stage = "page loaded; sections 1-9"
            return 200, "text/html; charset=utf-8", (HERE / self.page).read_bytes()
        if path in ("/fetch-headers", "/h1-headers", "/img-headers"):
            self.requests.setdefault(f"{path[1:]}_{proto}", (names, values))
            if path == "/img-headers":
                return 200, "image/gif", bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")
            return 204, "text/plain", b""
        if method == "POST" and path == "/result":
            self.result = json.loads(body)
            self.done.set()
            return 204, "text/plain", b""
        return 404, "text/plain", b""

    def _tls_server(self, cert, key, alpn):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(16)
        self._socks.append(sock)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        ctx.set_alpn_protocols(alpn)
        port = sock.getsockname()[1]
        threading.Thread(target=self._accept, args=(sock, ctx, port), daemon=True).start()
        return port

    def _accept(self, sock, ctx, port):
        while True:
            try:
                conn, _ = sock.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn, ctx, port), daemon=True).start()

    def _serve(self, conn, ctx, port):
        try:
            conn.settimeout(15)
            # Read the ClientHello without consuming it, so the TLS layer still gets it.
            data, deadline = b"", time.time() + 5
            while time.time() < deadline:
                data = conn.recv(65536, socket.MSG_PEEK)
                if len(data) >= 5 and len(data) >= 5 + int.from_bytes(data[3:5], "big"):
                    break
                time.sleep(0.01)
            hello = parse_client_hello(data)
            hello["port"] = "h2" if port == self.h2_port else "h1"
            self.hellos.append(hello)
            tls = ctx.wrap_socket(conn, server_side=True)
            hello["paths"] = []
            if tls.selected_alpn_protocol() == "h2":
                self._serve_h2(tls, hello["paths"])
            else:
                self._serve_h1(tls, hello["paths"])
        except (OSError, ssl.SSLError):
            pass
        finally:
            conn.close()

    def _serve_h1(self, s, paths):
        buf = b""
        while True:
            while b"\r\n\r\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    return
                buf += chunk
            head, buf = buf.split(b"\r\n\r\n", 1)
            lines = head.decode("latin-1").split("\r\n")
            method, path, _ = lines[0].split(" ", 2)
            headers = [tuple(x.strip() for x in line.split(":", 1)) for line in lines[1:] if ":" in line]
            n = int(dict((k.lower(), v) for k, v in headers).get("content-length", 0))
            while len(buf) < n:
                buf += s.recv(65536)
            body, buf = buf[:n], buf[n:]
            paths.append(path.split("?")[0])
            status, ctype, out = self.respond(method, path, headers, body, "h1")
            s.sendall(f"HTTP/1.1 {status} X\r\nContent-Type: {ctype}\r\nContent-Length: {len(out)}\r\n"
                      f"Access-Control-Allow-Origin: *\r\n\r\n".encode() + out)

    def _serve_h2(self, s, paths):
        sniff = H2Sniffer()
        self.h2.append(sniff)
        conn = h2.connection.H2Connection(h2.config.H2Configuration(client_side=False, header_encoding="utf-8"))
        conn.initiate_connection()
        s.sendall(conn.data_to_send())
        streams = {}
        while True:
            data = s.recv(65536)
            if not data:
                return
            sniff.feed(data)
            for ev in conn.receive_data(data):
                if isinstance(ev, h2.events.RequestReceived):
                    streams[ev.stream_id] = [list(ev.headers), b""]
                elif isinstance(ev, h2.events.DataReceived):
                    streams[ev.stream_id][1] += ev.data
                    conn.acknowledge_received_data(ev.flow_controlled_length, ev.stream_id)
                elif isinstance(ev, h2.events.StreamEnded):
                    hdrs, body = streams.pop(ev.stream_id)
                    d = dict(hdrs)
                    paths.append(d.get(":path", "/").split("?")[0])
                    status, ctype, out = self.respond(d.get(":method"), d.get(":path", "/"), hdrs, body, "h2")
                    conn.send_headers(ev.stream_id, [(":status", str(status)), ("content-type", ctype),
                                                     ("content-length", str(len(out))),
                                                     ("access-control-allow-origin", "*")],
                                      end_stream=not out)
                    step = conn.max_outbound_frame_size
                    for i in range(0, len(out), step):     # the probe fits the stream window, not one frame
                        conn.send_data(ev.stream_id, out[i:i + step], end_stream=i + step >= len(out))
            s.sendall(conn.data_to_send())

    def _plain_handler(self):
        lab = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _go(self):
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n) if n else b""
                status, ctype, out = lab.respond(self.command, self.path, list(self.headers.items()), body, "http")
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(out)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(out)
            do_GET = do_POST = _go
        return Handler

    def network(self):
        """What the servers saw: TLS per port, HTTP/2 frames, header order per request."""
        first = {}
        for h in self.hellos:
            first.setdefault(h.get("port"), h)
        sniff = self.h2[0].summary() if self.h2 else None
        if sniff and self.h2[0].headers:
            sniff["document_header_order"] = [k for k, _ in self.h2[0].headers[0][3]]
        return {
            "tls_h2_port": first.get("h2"),
            "tls_h1_port": first.get("h1"),
            "tls_hello_count": len(self.hellos),
            # Each connection: port, new or resumed (pre_shared_key), and its JA4.
            "tls_hellos": [f"{h.get('port')} {'resumed' if '0029' in (h.get('extension_order') or []) else 'new'} {h.get('ja4', '')}"
                           f" {','.join(h.get('paths') or [])}" for h in self.hellos],
            "http2": sniff,
            "requests": {k: {"order": v[0], "values": v[1]} for k, v in sorted(self.requests.items())},
        }


def fresh_profile(prefs_text, secure=True):
    import tempfile
    profile = Path(tempfile.mkdtemp(prefix="ifox-lab-"))
    (profile / "user.js").write_text(prefs_text, encoding="utf-8")
    if secure:
        trust(profile)
    return profile


def remove_profile(profile):
    time.sleep(1)
    shutil.rmtree(profile, ignore_errors=True)
