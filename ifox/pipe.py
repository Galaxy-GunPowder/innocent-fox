"""The two named pipes between Python and the browser agent (Windows).

One instance each, local clients only, random name. The browser connects as
the client with -ifox-pipe <name>: <name>-in carries commands to it,
<name>-out carries replies back. Nothing listens on the network.
"""
import ctypes
import ctypes.wintypes as wt
import secrets

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateNamedPipeW.restype = wt.HANDLE
k32.CreateNamedPipeW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, wt.DWORD,
                                 wt.DWORD, wt.DWORD, wt.DWORD, wt.LPVOID]
k32.ConnectNamedPipe.restype = wt.BOOL
k32.ConnectNamedPipe.argtypes = [wt.HANDLE, wt.LPVOID]
k32.ReadFile.restype = wt.BOOL
k32.ReadFile.argtypes = [wt.HANDLE, wt.LPVOID, wt.DWORD, ctypes.POINTER(wt.DWORD), wt.LPVOID]
k32.WriteFile.restype = wt.BOOL
k32.WriteFile.argtypes = [wt.HANDLE, wt.LPCVOID, wt.DWORD, ctypes.POINTER(wt.DWORD), wt.LPVOID]
k32.CloseHandle.argtypes = [wt.HANDLE]

PIPE_ACCESS_INBOUND = 0x1
PIPE_ACCESS_OUTBOUND = 0x2
FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
PIPE_REJECT_REMOTE_CLIENTS = 0x8
ERROR_PIPE_CONNECTED = 535
INVALID_HANDLE = wt.HANDLE(-1).value
BUFFER = 1 << 20


def _create(path, access):
    h = k32.CreateNamedPipeW(path, access | FILE_FLAG_FIRST_PIPE_INSTANCE,
                             PIPE_REJECT_REMOTE_CLIENTS, 1, BUFFER, BUFFER, 0, None)
    if h in (None, INVALID_HANDLE):
        raise ctypes.WinError(ctypes.get_last_error())
    return h


class PipePair:
    def __init__(self):
        self.name = secrets.token_hex(16)
        self._out = _create(rf"\\.\pipe\{self.name}-in", PIPE_ACCESS_OUTBOUND)
        self._in = _create(rf"\\.\pipe\{self.name}-out", PIPE_ACCESS_INBOUND)

    def connect(self):
        """Blocks until the browser has opened both pipes."""
        for h in (self._out, self._in):
            if not k32.ConnectNamedPipe(h, None):
                err = ctypes.get_last_error()
                if err != ERROR_PIPE_CONNECTED:
                    raise ctypes.WinError(err)

    def write(self, data: bytes):
        view = memoryview(data)
        while view:
            done = wt.DWORD()
            if not k32.WriteFile(self._out, bytes(view[:BUFFER]), min(len(view), BUFFER),
                                 ctypes.byref(done), None):
                raise ctypes.WinError(ctypes.get_last_error())
            view = view[done.value:]

    def read(self) -> bytes:
        """Next chunk from the browser; b"" once it has closed its end."""
        buf = ctypes.create_string_buffer(65536)
        got = wt.DWORD()
        if not k32.ReadFile(self._in, buf, len(buf), ctypes.byref(got), None):
            return b""
        return buf.raw[:got.value]

    def close(self):
        for attr in ("_out", "_in"):
            h = getattr(self, attr)
            if h:
                k32.CloseHandle(h)
                setattr(self, attr, None)
