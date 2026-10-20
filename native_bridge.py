"""ctypes binding to the Linux C library; no unsafe numeric-PID fallback."""
import ctypes
import os
from pathlib import Path


def library():
    path = Path(__file__).resolve().parent / "native" / "libport_sentinel.so"
    try:
        lib = ctypes.CDLL(str(path), use_errno=True)
    except OSError as exc:
        raise RuntimeError("Build the Ubuntu native library first with make.") from exc
    lib.ps_open_process.argtypes = [ctypes.c_int]
    lib.ps_open_process.restype = ctypes.c_int
    lib.ps_signal_process.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.ps_signal_process.restype = ctypes.c_int
    return lib


def checked(result):
    if result < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return result
