"""Tie the browser's life to this Python process.

The browser and every process it starts go into a Windows job object that only
this process holds. When Python ends for any reason (script done, error,
Ctrl+C, window closed, killed from Task Manager) Windows closes the handle and
ends the whole job, so no browser is ever left running.
"""
import ctypes
import subprocess
from ctypes import wintypes

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_nt = ctypes.WinDLL("ntdll")

_k32.CreateJobObjectW.restype = wintypes.HANDLE
_k32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
_k32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
_k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
_k32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
_k32.CloseHandle.argtypes = (wintypes.HANDLE,)
_nt.NtResumeProcess.argtypes = (wintypes.HANDLE,)

CREATE_SUSPENDED = 0x00000004
_KILL_ON_JOB_CLOSE = 0x00002000
_EXTENDED_LIMITS = 9


class _Basic(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD)]


class _Extended(ctypes.Structure):
    _fields_ = [("Basic", _Basic), ("Io", ctypes.c_uint64 * 6), ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


def _check(ok):
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return ok


class Job:
    def __init__(self):
        self.handle = _check(_k32.CreateJobObjectW(None, None))
        info = _Extended()
        info.Basic.LimitFlags = _KILL_ON_JOB_CLOSE
        _check(_k32.SetInformationJobObject(self.handle, _EXTENDED_LIMITS, ctypes.byref(info), ctypes.sizeof(info)))

    def start(self, cmd):
        """Popen(cmd) inside the job. Started paused and resumed only once it is in,
        so not even its first child can escape."""
        proc = subprocess.Popen(cmd, creationflags=CREATE_SUSPENDED)
        try:
            _check(_k32.AssignProcessToJobObject(self.handle, int(proc._handle)))
        except OSError:
            proc.kill()
            raise
        _nt.NtResumeProcess(int(proc._handle))
        return proc

    def kill(self):
        if self.handle:
            _k32.TerminateJobObject(self.handle, 1)

    def close(self):
        if self.handle:
            _k32.CloseHandle(self.handle)   # last handle: Windows ends anything still in it
            self.handle = None
