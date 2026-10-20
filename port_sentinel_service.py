#!/usr/bin/env python3
"""Per-user Unix socket daemon. No web server and no graphical interface."""
import argparse
import json
import logging
import os
from pathlib import Path
import signal
import socket
import socketserver
import stat
import struct
from port_sentinel_agent import run_agent, socket_path


class Handler(socketserver.StreamRequestHandler):
    timeout = 10

    def handle(self):
        try:
            _, uid, _ = struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid != os.getuid():
                raise PermissionError('Peer must have the same UID as this service.')
            line = self.rfile.readline(16385)
            if len(line) > 16384 or not line.endswith(b'\n'):
                raise ValueError('Request exceeds limit or has no newline.')
            request = json.loads(line)
            if set(request) != {'prompt'}:
                raise ValueError('Request must contain only prompt.')
            answer = run_agent(request['prompt'])
            response = {'ok':True,'answer':answer}
            logging.info('Request completed')
        except Exception as exc:
            logging.warning('Request failed: %s',type(exc).__name__)
            response = {'ok':False,'error':str(exc)}
        try:
            self.wfile.write(json.dumps(response).encode() + b'\n')
        except (BrokenPipeError, TimeoutError):
            logging.info('Client disconnected')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket',default=socket_path())
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    os.umask(0o077)
    path = Path(args.socket)
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    info = path.parent.lstat()
    if info.st_uid != os.getuid() or not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
        raise PermissionError('Socket directory must be owned by this user with mode 0700.')
    if path.exists() or path.is_symlink():
        raise RuntimeError('Socket path already exists. Check for a running service before removing a stale socket.')
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(SystemExit(0)))
    try:
        with socketserver.UnixStreamServer(str(path),Handler) as server:
            path.chmod(0o600)
            logging.info('Port Sentinel listening at %s',path)
            server.serve_forever()
    finally:
        path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
