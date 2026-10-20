#!/usr/bin/env python3
"""Tiny local TCP server used only to test Port Sentinel safely."""

from __future__ import annotations

import argparse
import socket

parser = argparse.ArgumentParser()
parser.add_argument("port", nargs="?", type=int, default=8080)
args = parser.parse_args()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", args.port))
    server.listen(5)
    print(f"Demo server listening on 127.0.0.1:{args.port}", flush=True)
    while True:
        conn, addr = server.accept()
        with conn:
            conn.sendall(b"Port Sentinel demo server\n")
