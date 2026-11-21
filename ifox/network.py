"""Proxies for a profile, set so nothing reaches the network around the proxy.

Accepted formats (the forms proxy providers export):
    socks5h://user:pass@host:port      also socks5, socks4, socks4a, http, https
    user:pass@host:port                scheme from `scheme`, default http
    host:port:user:pass
    user:pass:host:port
    host:port

What Firefox can do with each:
    socks5, socks5h   login sent by the agent; DNS always through the proxy
    http, https       login sent as a header by the agent (patch 09 for http)
    socks4, socks4a   no login in the protocol

Prefer https when the provider offers it: the login is encrypted on the way
to the proxy. With http it crosses your own network in clear text.

Decodo: https://user:pass@us.decodo.com:10001 (US), or gate.decodo.com with
user-<name>-country-us. Ports 10001+ keep one exit IP for 10 min. SOCKS5 only
on gate.decodo.com:7000 (country hosts don't take SOCKS5).

The login never goes into the profile: it travels over the pipe to the agent.
"""
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit

SCHEMES = {"http", "https", "socks", "socks4", "socks4a", "socks5", "socks5h"}


@dataclass
class Proxy:
    scheme: str
    host: str
    port: int
    user: str = ""
    password: str = ""

    @property
    def kind(self):
        """Firefox's name for it: http, https, socks4 or socks (= SOCKS5)."""
        return {"socks4a": "socks4", "socks5": "socks", "socks5h": "socks"}.get(self.scheme, self.scheme)

    def url(self):
        """scheme://user:pass@host:port, the form parse() reads back."""
        who = f"{quote(self.user, safe='')}:{quote(self.password, safe='')}@" if self.user else ""
        return f"{self.scheme}://{who}{self.host}:{self.port}"

    def __repr__(self):  # never print the password
        who = f"{self.user}:***@" if self.user else ""
        return f"Proxy({self.scheme}://{who}{self.host}:{self.port})"


def _port(s):
    if not s.isdigit() or not 0 < int(s) < 65536:
        raise ValueError(f"bad proxy port {s!r}")
    return int(s)


def parse(text, scheme="http"):
    """Any common proxy string to a Proxy."""
    text = text.strip()
    if "://" in text:
        u = urlsplit(text)
        s = u.scheme.lower()
        if s not in SCHEMES or not u.hostname or not u.port:
            raise ValueError("proxy URL must be scheme://[user:pass@]host:port")
        s = "socks5" if s == "socks" else s
        return Proxy(s, u.hostname, u.port, unquote(u.username or ""), unquote(u.password or ""))
    if "@" in text:
        cred, _, addr = text.rpartition("@")
        user, _, password = cred.partition(":")
        host, _, port = addr.rpartition(":")
        return Proxy(scheme, host, _port(port), user, password)
    parts = text.split(":")
    if len(parts) == 2:
        return Proxy(scheme, parts[0], _port(parts[1]))
    if len(parts) >= 4:
        if parts[1].isdigit():                    # host:port:user:pass (pass may hold ':')
            return Proxy(scheme, parts[0], _port(parts[1]), parts[2], ":".join(parts[3:]))
        if parts[-1].isdigit():                   # user:pass:host:port
            return Proxy(scheme, parts[-2], _port(parts[-1]), parts[0], ":".join(parts[1:-2]))
    raise ValueError("unknown proxy format; use scheme://user:pass@host:port")


def proxy_prefs(proxy):
    """Stock prefs for the profile. With a login, the agent finishes the job."""
    p = parse(proxy) if isinstance(proxy, str) else proxy
    if p.user and p.kind == "socks4":
        raise ValueError("socks4 has no login; use socks5")
    out = {
        "network.proxy.type": 1,          # manual
        "network.proxy.no_proxies_on": "",
        "network.proxy.failover_direct": False,   # proxy down = no connection, never direct
        "network.proxy.allow_bypass": False,
        # WebRTC: no UDP of its own, so neither the page nor a STUN server sees the real IP.
        "media.peerconnection.ice.proxy_only": True,
        # Host names never go to the local resolver.
        "network.dns.disablePrefetch": True,
        "network.http.http3.enable": False,
        "network.proxy.socks5_remote_dns": True,
        "network.proxy.socks_remote_dns": True,
    }
    if p.kind == "http" and not p.user:
        out.update({
            "network.proxy.http": p.host, "network.proxy.http_port": p.port,
            "network.proxy.ssl": p.host, "network.proxy.ssl_port": p.port,
        })
    elif p.kind in ("http", "https"):
        # The agent sets these (prefs can't hold a login or name a TLS proxy).
        # Until then, a dead local port: nothing leaves directly, and Firefox
        # never meets the proxy without its login (that would ask a person).
        out.update({"network.proxy.socks": "127.0.0.1", "network.proxy.socks_port": 9,
                    "network.proxy.socks_version": 5})
    else:
        out.update({
            "network.proxy.socks": p.host, "network.proxy.socks_port": p.port,
            "network.proxy.socks_version": 4 if p.kind == "socks4" else 5,
        })
    return out


def agent_args(proxy):
    """Arguments for the agent's proxy command, or None when prefs are enough."""
    p = parse(proxy) if isinstance(proxy, str) else proxy
    if p.kind == "https" or (p.kind in ("http", "socks") and p.user):
        return {"type": p.kind, "host": p.host, "port": p.port, "user": p.user, "pass": p.password}
    return None
