#!/usr/bin/env python3
"""Linux OS tools for the Port Sentinel Agent.

The functions in this module are the agent's tool-calling surface. They do not
ask the LLM to generate shell commands; they perform the OS operations directly
with Python's subprocess/os interfaces and /proc inspection.
"""

from __future__ import annotations

import os
import re
import signal
import time
import socket
import sys
import subprocess
from pathlib import Path
from typing import Any


def _run_ss(protocol: str) -> list[dict[str, Any]]:
    """Read listening TCP/UDP sockets from ss(8)."""
    if protocol == "tcp":
        cmd = ["ss", "-H", "-lntp"]
    elif protocol == "udp":
        cmd = ["ss", "-H", "-anup"]
    else:
        cmd = ["ss", "-H", "-antup"]

    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("ss is unavailable or timed out; using /proc.") from exc

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ss failed")

    rows: list[dict[str, Any]] = []
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Typical output:
        # LISTEN 0 4096 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=1234,fd=3))
        parts = line.split()
        if len(parts) < 5:
            continue

        # Combined TCP/UDP output includes a leading Netid column.
        offset = 1 if parts[0] in {"tcp", "udp"} else 0
        if len(parts) < 5 + offset:
            continue
        local = parts[3 + offset]
        process_text = " ".join(parts[5 + offset:])
        pids = sorted({int(x) for x in re.findall(r"pid=(\d+)", process_text)})
        names = re.findall(r'\(\("([^"]+)"', process_text)
        port_match = re.search(r":(\d+)$", local)
        if not port_match:
            continue

        state = parts[offset]
        family = "ipv6" if local.startswith("[") or ":" in local.rsplit(":", 1)[0] else "ipv4"
        proto = parts[0] if offset else ("tcp" if state == "LISTEN" else "udp")
        if proto == "tcp" and state != "LISTEN":
            continue
        rows.append(
            {
                "protocol": proto,
                "state": state,
                "local_address": local,
                "port": int(port_match.group(1)),
                "family": family,
                "pids": pids,
                "process_names": sorted(set(names)),
                "source": "ss",
            }
        )

    return rows


def _decode_address(local_hex: str, family: str) -> str:
    address, port = local_hex.rsplit(":", 1)
    raw = bytes.fromhex(address)
    # /proc encodes each 32-bit word in native byte order.
    raw = b"".join(int.from_bytes(raw[i:i+4], sys.byteorder).to_bytes(4, "big")
                   for i in range(0, len(raw), 4))
    ip = socket.inet_ntop(socket.AF_INET6 if family == "ipv6" else socket.AF_INET, raw)
    return f"[{ip}]:{int(port, 16)}" if family == "ipv6" else f"{ip}:{int(port, 16)}"


def _read_proc_socket_inodes(protocol: str) -> list[dict[str, Any]]:
    """Return bound/listening socket records using /proc/net as a fallback."""
    files = {
        "tcp": ["/proc/net/tcp", "/proc/net/tcp6"],
        "udp": ["/proc/net/udp", "/proc/net/udp6"],
        "all": ["/proc/net/tcp", "/proc/net/tcp6", "/proc/net/udp", "/proc/net/udp6"],
    }[protocol]

    records: list[dict[str, Any]] = []
    for filename in files:
        path = Path(filename)
        if not path.exists():
            continue
        proto = "tcp" if "/tcp" in filename else "udp"
        family = "ipv6" if filename.endswith("6") else "ipv4"
        try:
            lines = path.read_text().splitlines()[1:]
        except PermissionError:
            continue

        for line in lines:
            fields = line.split()
            if len(fields) < 10:
                continue
            local_hex, state, inode = fields[1], fields[3], fields[9]
            try:
                port = int(local_hex.rsplit(":", 1)[1], 16)
            except (ValueError, IndexError):
                continue

            # TCP 0A == LISTEN. For UDP, a bound socket is useful for our purpose;
            # /proc does not expose a TCP-like LISTEN state for UDP.
            if proto == "tcp" and state != "0A":
                continue

            records.append(
                {
                    "protocol": proto,
                    "state": "LISTEN" if proto == "tcp" else "UNCONN",
                    "local_address": _decode_address(local_hex, family),
                    "port": port,
                    "family": family,
                    "inode": inode,
                    "pids": [],
                    "process_names": [],
                    "source": "proc",
                }
            )
    return records


def _proc_socket_owner_map() -> dict[str, set[int]]:
    """Map socket inode -> PIDs by scanning /proc/<pid>/fd symlinks."""
    mapping: dict[str, set[int]] = {}
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        fd_dir = entry / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(fd)
            except (PermissionError, FileNotFoundError, OSError):
                continue
            match = re.fullmatch(r"socket:\[(\d+)\]", target)
            if match:
                mapping.setdefault(match.group(1), set()).add(pid)
    return mapping


def _process_name(pid: int) -> str:
    try:
        comm = (Path(f"/proc/{pid}/comm").read_text()).strip()
        if comm:
            return comm
    except OSError:
        pass
    return "unknown"


def _process_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        cmd = raw.replace(b"\x00", b" ").decode(errors="replace").strip()
        return cmd or _process_name(pid)
    except OSError:
        return "unknown"


def _enrich(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add owner information to proc-derived records."""
    if not records:
        return records
    inode_map = _proc_socket_owner_map()
    for row in records:
        if row.get("source") != "proc":
            continue
        pids = sorted(inode_map.get(row.get("inode", ""), set()))
        row["pids"] = pids
        row["process_names"] = sorted({_process_name(pid) for pid in pids})
        row.pop("inode", None)
    return records


def list_listening_ports(protocol: str = "all") -> list[dict[str, Any]]:
    """List listening/bound network ports and their owning PIDs.

    Args:
        protocol: "tcp", "udp", or "all".
    """
    if sys.platform != "linux":
        raise RuntimeError("Port Sentinel requires Ubuntu/Linux.")
    protocol = protocol.lower()
    if protocol not in {"tcp", "udp", "all"}:
        raise ValueError("protocol must be tcp, udp, or all")

    try:
        rows = _run_ss(protocol)
        # ss is the preferred source. It may omit PIDs when permissions are
        # insufficient, so supplement missing owners from /proc.
        if all(row["pids"] for row in rows):
            return rows
        proc_rows = _enrich(_read_proc_socket_inodes(protocol))
        for row in rows:
            if row["pids"]:
                continue
            supplements = [r for r in proc_rows if r["protocol"] == row["protocol"]
                           and r["family"] == row["family"]
                           and r["local_address"] == row["local_address"]]
            row["pids"] = sorted({pid for r in supplements for pid in r["pids"]})
            row["process_names"] = sorted({_process_name(pid) for pid in row["pids"]})
        return rows
    except RuntimeError:
        rows = []

    proc_rows = _enrich(_read_proc_socket_inodes(protocol))
    return proc_rows


def find_port_process(port: int, protocol: str = "tcp") -> dict[str, Any]:
    """Find the process(es) owning a specific listening/bound port.

    Args:
        port: TCP/UDP port number, 1-65535.
        protocol: "tcp", "udp", or "all".
    """
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")

    rows = list_listening_ports(protocol)
    matches = [row for row in rows if row["port"] == port]

    # A non-root `ss -p` may show the socket but hide its PID. For a specific
    # port, retry through /proc so the tool can still resolve the owner when
    # the kernel permissions allow the /proc fd scan.
    if matches and not any(row.get("pids") for row in matches):
        proc_rows = _enrich(_read_proc_socket_inodes(protocol))
        proc_matches = [row for row in proc_rows if row["port"] == port]
        if proc_matches:
            matches = proc_matches

    owners: dict[int, dict[str, Any]] = {}
    for row in matches:
        for pid in row.get("pids", []):
            owners[pid] = {
                "pid": pid,
                "process_name": _process_name(pid),
                "cmdline": _process_cmdline(pid),
            }

    return {
        "port": port,
        "protocol": protocol,
        "found": bool(matches),
        "socket_count": len(matches),
        "sockets": matches,
        "processes": sorted(owners.values(), key=lambda x: x["pid"]),
        "message": (
            f"Found {len(owners)} owning process(es) for port {port}."
            if owners
            else (f"Port {port} has sockets, but their owners are not visible." if matches
                  else f"No listening/bound socket found for port {port}.")
        ),
    }


def get_process_info(pid: int) -> dict[str, Any]:
    """Return basic information about a Linux process."""
    pid = int(pid)
    if pid <= 0:
        raise ValueError("pid must be positive")
    if not Path(f"/proc/{pid}").exists():
        return {"pid": pid, "exists": False, "message": "Process does not exist."}

    try:
        status = Path(f"/proc/{pid}/status").read_text(errors="replace")
        state_match = re.search(r"^State:\s*(.+)$", status, re.MULTILINE)
        uid_match = re.search(r"^Uid:\s*(\d+)", status, re.MULTILINE)
        uid = int(uid_match.group(1)) if uid_match else None
    except OSError:
        state_match = None
        uid = None

    return {
        "pid": pid,
        "exists": True,
        "process_name": _process_name(pid),
        "cmdline": _process_cmdline(pid),
        "state": state_match.group(1).strip() if state_match else "unknown",
        "uid": uid,
        "current_user_pid": os.getpid(),
    }


def process_identity(pid: int) -> str:
    """Linux start-time ticks distinguish a process from a reused PID."""
    text = Path(f"/proc/{pid}/stat").read_text()
    return text[text.rfind(")") + 2:].split()[19]


def kill_process(pid: int, signal_name: str = "TERM", *, expected_start: str,
                 port: int, protocol: str = "tcp") -> dict[str, Any]:
    """Revalidate ownership and signal through a pinned C pidfd handle."""
    from native_bridge import library, checked
    pid = int(pid)
    signal_name = signal_name.upper().removeprefix("SIG")
    allowed = {"TERM": signal.SIGTERM, "INT": signal.SIGINT, "KILL": signal.SIGKILL}
    if signal_name not in allowed:
        raise ValueError("signal_name must be TERM, INT, or KILL")
    if pid <= 2 or pid in {os.getpid(), os.getppid()}:
        raise PermissionError("Protected process.")
    lib = library()
    descriptor = checked(lib.ps_open_process(pid))
    try:
        if process_identity(pid) != expected_start:
            raise PermissionError("Process identity changed; inspect again.")
        info = get_process_info(pid)
        if info.get("uid") != os.getuid():
            raise PermissionError("Only processes owned by the service user may be stopped.")
        fresh = find_port_process(port, protocol)
        owners = fresh["processes"]
        if {p["pid"] for p in owners} != {pid} or any(not row["pids"] for row in fresh["sockets"]):
            raise PermissionError("Ownership changed or is ambiguous; inspect again.")
        if process_identity(pid) != expected_start:
            raise PermissionError("Process identity changed; inspect again.")
        checked(lib.ps_signal_process(descriptor, int(allowed[signal_name])))
    finally:
        os.close(descriptor)
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        after = find_port_process(port, protocol)
        if not after["found"]:
            return {"success": True, "pid": pid, "signal": signal_name,
                    "port_released": True, "message": "Signal sent; port is now free."}
        time.sleep(0.1)
    return {"success": True, "pid": pid, "signal": signal_name,
            "port_released": False, "message": "Signal sent; port remains occupied."}
