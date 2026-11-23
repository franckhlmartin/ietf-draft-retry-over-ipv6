#!/usr/bin/env python3
"""Portable TCP Happy Eyeballs probing tool (measurement, not a client stack).

Measures per-endpoint TCP connection establishment times for dual-stack hosts,
similar to the C tool https://github.com/vbajpai/happy (Schoenwälder / Bajpai).
DNS resolution time is displayed separately and is never included in connect
timings. This script does not implement RFC 8305 / Happy Eyeballs v3; it only
measures inputs to that race and prints informative Connection Attempt Delay
(CAD) projections.

Clean-room reimplementation of the metric and CLI shape; not a copy of happy.c.
"""

from __future__ import annotations

import argparse
import errno
import selectors
import socket
import sys
import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

DEFAULT_PORT = 80
DEFAULT_QUERIES = 3
DEFAULT_TIMEOUT_MS = 2000
DEFAULT_DELAY_MS = 25
DEFAULT_CAD_MS = (200, 250)  # curl typical head-start; RFC 8305 recommendation


@dataclass
class EndpointResult:
    host: str
    port: int
    family: int
    addr: str
    sockaddr: tuple
    canonname: str = ""
    reverse: str = ""
    times_us: list[int | None] = field(default_factory=list)

    @property
    def family_label(self) -> str:
        return "IPv6" if self.family == socket.AF_INET6 else "IPv4"

    def successful_times(self) -> list[int]:
        return [t for t in self.times_us if t is not None and t >= 0]

    def average_us(self) -> float | None:
        ok = self.successful_times()
        if not ok:
            return None
        return sum(ok) / len(ok)


def now_us() -> int:
    return time.perf_counter_ns() // 1000


def format_ms(us: int | float | None) -> str:
    if us is None:
        return "-"
    return f"{us / 1000.0:.3f}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    epilog = """\
Manual
------
This tool resolves each hostname with getaddrinfo(3), then measures TCP
connection establishment time to every returned address using staggered
non-blocking connect() calls. DNS duration is shown separately and is NOT
included in connect timings (same metric boundary as vbajpai/happy).

It is a measurement aid for dual-stack / Happy Eyeballs diagnosis, not an
RFC 8305 or Happy Eyeballs v3 client. After timings it prints informative
projections for Connection Attempt Delay (CAD) values (default: 200 ms as
used by curl, 250 ms as recommended by RFC 8305). OS address order may
differ from browsers.

Examples
--------
  # Human-readable connect times + DNS detail, sorted by average:
  python3 scripts/happy.py -acs www.ietf.org

  # Compare why one host may lose IPv6 under curl HE (~200 ms CAD):
  python3 scripts/happy.py -acs -p 443 ipv6forum.com whynoipv6.com

  # Machine-readable output (HAPPY.0 / RESOLVE.0 / DNS.0 lines):
  python3 scripts/happy.py -m -q 5 -p 443 example.com

  # Targets from a file (one hostname per line) or stdin:
  python3 scripts/happy.py -acs -f hosts.txt
  printf 'www.ietf.org\\nexample.com\\n' | python3 scripts/happy.py -acs -f -

See also: docs/README.md (Verification), https://github.com/vbajpai/happy
"""
    parser = argparse.ArgumentParser(
        prog="happy.py",
        description=(
            "TCP Happy Eyeballs probing tool: measure per-endpoint connect "
            "times (DNS shown separately; not an RFC 8305 client)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "-a",
        action="store_true",
        help="show DNS detail (canonical name and reverse mapping per endpoint)",
    )
    parser.add_argument(
        "-c",
        action="store_true",
        help="measure TCP connect time per endpoint (default if no mode selected)",
    )
    parser.add_argument(
        "-s",
        action="store_true",
        help="sort endpoints by average successful connect time",
    )
    parser.add_argument(
        "-m",
        action="store_true",
        help="machine-readable semicolon output (HAPPY.0 / RESOLVE.0 / DNS.0)",
    )
    parser.add_argument(
        "-p",
        dest="ports",
        type=int,
        action="append",
        metavar="port",
        help=f"TCP port to probe (default: {DEFAULT_PORT}; repeatable)",
    )
    parser.add_argument(
        "-q",
        dest="nqueries",
        type=int,
        default=DEFAULT_QUERIES,
        metavar="nqueries",
        help=f"connect attempts per endpoint (default: {DEFAULT_QUERIES})",
    )
    parser.add_argument(
        "-t",
        dest="timeout_ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        metavar="timeout",
        help=f"connect timeout in milliseconds (default: {DEFAULT_TIMEOUT_MS})",
    )
    parser.add_argument(
        "-d",
        dest="delay_ms",
        type=int,
        default=DEFAULT_DELAY_MS,
        metavar="delay",
        help=f"stagger between SYN starts in milliseconds (default: {DEFAULT_DELAY_MS})",
    )
    parser.add_argument(
        "-f",
        dest="file",
        metavar="file",
        help="read target hostnames from file, or '-' for stdin",
    )
    parser.add_argument(
        "--cad",
        dest="cad_ms",
        type=int,
        action="append",
        metavar="ms",
        help=(
            "Connection Attempt Delay(s) for HE projections in ms "
            f"(default: {', '.join(str(c) for c in DEFAULT_CAD_MS)}; repeatable)"
        ),
    )
    parser.add_argument(
        "hosts",
        nargs="*",
        metavar="hostname",
        help="target hostname(s)",
    )
    args = parser.parse_args(argv)

    if not args.c and not args.a:
        args.c = True

    if args.ports is None:
        args.ports = [DEFAULT_PORT]
    if args.nqueries < 1:
        parser.error("-q nqueries must be >= 1")
    if args.timeout_ms < 1:
        parser.error("-t timeout must be >= 1")
    if args.delay_ms < 0:
        parser.error("-d delay must be >= 0")
    if args.cad_ms is None:
        args.cad_ms = list(DEFAULT_CAD_MS)

    return args


def load_hosts(args: argparse.Namespace) -> list[str]:
    hosts: list[str] = list(args.hosts)
    if args.file is not None:
        if args.file == "-":
            lines = sys.stdin.read().splitlines()
        else:
            with open(args.file, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hosts.append(line)
    if not hosts:
        print("happy.py: no targets specified (hostname... or -f file)", file=sys.stderr)
        sys.exit(2)
    return hosts


def reverse_lookup(addr: str) -> str:
    try:
        name, _aliases, _addrs = socket.gethostbyaddr(addr)
        return name
    except OSError:
        return ""


def resolve_host(
    host: str, port: int, want_dns_detail: bool
) -> tuple[list[EndpointResult], int | None, str | None]:
    """Return endpoints, DNS duration in microseconds, and error message if any."""
    hints = socket.AI_ADDRCONFIG
    t0 = now_us()
    try:
        infos = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
            flags=hints,
        )
    except socket.gaierror as exc:
        dns_us = now_us() - t0
        return [], dns_us, str(exc)
    dns_us = now_us() - t0

    seen: set[tuple[int, str, int]] = set()
    endpoints: list[EndpointResult] = []
    for family, _socktype, _proto, canonname, sockaddr in infos:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        if family == socket.AF_INET:
            addr = sockaddr[0]
            key = (family, addr, sockaddr[1])
        else:
            addr = sockaddr[0]
            key = (family, addr, sockaddr[1])
        if key in seen:
            continue
        seen.add(key)
        ep = EndpointResult(
            host=host,
            port=port,
            family=family,
            addr=addr,
            sockaddr=sockaddr,
            canonname=canonname or "",
        )
        if want_dns_detail:
            ep.reverse = reverse_lookup(addr)
        endpoints.append(ep)
    return endpoints, dns_us, None


@dataclass
class _PendingConnect:
    ep: EndpointResult
    sock: socket.socket
    t0: int
    done: bool = False
    result: int | None = None


def _start_connect(ep: EndpointResult) -> _PendingConnect | None:
    try:
        sock = socket.socket(ep.family, socket.SOCK_STREAM)
    except OSError:
        return None
    sock.setblocking(False)
    t0 = now_us()
    try:
        err = sock.connect_ex(ep.sockaddr)
    except OSError:
        sock.close()
        return None
    pending = _PendingConnect(ep=ep, sock=sock, t0=t0)
    if err in (0, errno.EISCONN):
        pending.done = True
        pending.result = now_us() - t0
        sock.close()
    elif err not in (errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EAGAIN):
        pending.done = True
        pending.result = None
        sock.close()
    return pending


def measure_endpoints(
    endpoints: list[EndpointResult],
    nqueries: int,
    timeout_ms: int,
    delay_ms: int,
) -> None:
    """Stagger SYN starts across endpoints; collect nqueries samples each.

    Within each round, start non-blocking connects to all endpoints with a
    short delay between SYN starts (original happy behaviour), then wait via
    selectors until each finishes or the timeout elapses. Elapsed time is
    measured from each connect start only (DNS excluded).
    """
    timeout_us = timeout_ms * 1000
    for round_i in range(nqueries):
        pending: list[_PendingConnect] = []
        for i, ep in enumerate(endpoints):
            if delay_ms and (i > 0 or round_i > 0):
                time.sleep(delay_ms / 1000.0)
            started = _start_connect(ep)
            if started is None:
                ep.times_us.append(None)
            else:
                pending.append(started)

        open_pending = [p for p in pending if not p.done]
        if open_pending:
            sel = selectors.DefaultSelector()
            sock_map: dict[int, _PendingConnect] = {}
            for p in open_pending:
                sel.register(p.sock, selectors.EVENT_WRITE)
                sock_map[p.sock.fileno()] = p
            deadline = time.perf_counter() + (timeout_ms / 1000.0)
            try:
                while sock_map:
                    remaining = deadline - time.perf_counter()
                    if remaining <= 0:
                        break
                    for key, _events in sel.select(timeout=remaining):
                        p = sock_map.get(key.fd)
                        if p is None or p.done:
                            continue
                        so_err = p.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                        if so_err == 0:
                            p.result = now_us() - p.t0
                            p.done = True
                        elif so_err not in (
                            errno.EINPROGRESS,
                            errno.EWOULDBLOCK,
                            errno.EAGAIN,
                        ):
                            p.result = None
                            p.done = True
                        if p.done:
                            try:
                                sel.unregister(p.sock)
                            except Exception:
                                pass
                            p.sock.close()
                            sock_map.pop(key.fd, None)
            finally:
                for p in list(sock_map.values()):
                    if not p.done:
                        p.result = -timeout_us
                        p.done = True
                    try:
                        sel.unregister(p.sock)
                    except Exception:
                        pass
                    p.sock.close()
                sel.close()

        for p in pending:
            p.ep.times_us.append(p.result)


def he_projection(
    endpoints: Sequence[EndpointResult], cad_ms: int
) -> str:
    """Heuristic: IPv6 gets a CAD head-start; report which family would win."""
    v6 = [e.average_us() for e in endpoints if e.family == socket.AF_INET6]
    v4 = [e.average_us() for e in endpoints if e.family == socket.AF_INET]
    v6_ok = [t for t in v6 if t is not None]
    v4_ok = [t for t in v4 if t is not None]
    if not v6_ok and not v4_ok:
        return f"CAD={cad_ms} ms: no successful connects"
    if not v6_ok:
        return f"CAD={cad_ms} ms: IPv4 would win (no successful IPv6)"
    if not v4_ok:
        return f"CAD={cad_ms} ms: IPv6 would win (no successful IPv4)"
    best_v6 = min(v6_ok)
    best_v4 = min(v4_ok)
    # IPv6 attempt starts at t=0; IPv4 at t=CAD. Winner is earliest completion.
    v6_done = best_v6
    v4_done = cad_ms * 1000 + best_v4
    if v6_done <= v4_done:
        margin_ms = (v4_done - v6_done) / 1000.0
        return (
            f"CAD={cad_ms} ms: IPv6 would typically win "
            f"(v6={format_ms(best_v6)} ms vs v4+CAD={format_ms(v4_done)} ms; "
            f"margin {margin_ms:.3f} ms)"
        )
    margin_ms = (v6_done - v4_done) / 1000.0
    return (
        f"CAD={cad_ms} ms: IPv4 would typically win "
        f"(v6={format_ms(best_v6)} ms vs v4+CAD={format_ms(v4_done)} ms; "
        f"IPv4 ahead by {margin_ms:.3f} ms)"
    )


def emit_machine_resolve(
    ts: int, host: str, port: int, dns_us: int | None, ok: bool
) -> None:
    status = "OK" if ok else "FAIL"
    dns_field = dns_us if dns_us is not None else ""
    print(f"RESOLVE.0;{ts};{status};{host};{port};{dns_field}")


def emit_machine_dns(ts: int, ep: EndpointResult) -> None:
    print(
        f"DNS.0;{ts};OK;{ep.host};{ep.addr};{ep.canonname};{ep.reverse}"
    )


def emit_machine_happy(ts: int, ep: EndpointResult) -> None:
    # One line per endpoint with all sample times (us); negative = timeout.
    parts = [
        "HAPPY.0",
        str(ts),
        "OK" if any(t is not None for t in ep.times_us) else "FAIL",
        ep.host,
        str(ep.port),
        ep.addr,
    ]
    for t in ep.times_us:
        if t is None:
            parts.append("")
        else:
            parts.append(str(t))
    print(";".join(parts))


def emit_human_dns_block(
    host: str,
    port: int,
    dns_us: int | None,
    endpoints: Sequence[EndpointResult],
) -> None:
    print(f"{host}:{port}")
    if dns_us is not None:
        print(f"  dns {format_ms(dns_us)} ms")
    for ep in endpoints:
        bits = [ep.canonname or host, ">", ep.addr]
        if ep.reverse:
            bits.extend([">", ep.reverse])
        print("  " + " ".join(bits))
    print()


def emit_human_connect_block(
    host: str,
    port: int,
    dns_us: int | None,
    endpoints: Sequence[EndpointResult],
    sort_results: bool,
    cad_ms_list: Iterable[int],
) -> None:
    print(f"{host}:{port}")
    if dns_us is not None:
        print(f"  dns {format_ms(dns_us)} ms")

    ordered = list(endpoints)
    if sort_results:
        ordered.sort(
            key=lambda e: (e.average_us() is None, e.average_us() or 0)
        )

    for ep in ordered:
        samples: list[str] = []
        for t in ep.times_us:
            if t is None:
                samples.append("FAIL")
            elif t < 0:
                samples.append(f"TIMEOUT({format_ms(-t)})")
            else:
                samples.append(format_ms(t))
        print(f"  {ep.addr}  {' '.join(samples)}")

    for cad in cad_ms_list:
        print(f"  # {he_projection(endpoints, cad)}")
    print()


def run_target(
    host: str,
    port: int,
    args: argparse.Namespace,
    ts: int,
) -> int:
    """Probe one host:port. Return 0 on success, 1 on resolve/connect issues."""
    endpoints, dns_us, err = resolve_host(host, port, want_dns_detail=args.a)
    if err is not None:
        if args.m:
            emit_machine_resolve(ts, host, port, dns_us, ok=False)
        else:
            print(f"{host}:{port}")
            print(f"  dns {format_ms(dns_us)} ms (FAIL: {err})")
            print()
        return 1

    if args.m:
        emit_machine_resolve(ts, host, port, dns_us, ok=True)
        if args.a:
            for ep in endpoints:
                emit_machine_dns(ts, ep)
    elif args.a:
        emit_human_dns_block(host, port, dns_us, endpoints)

    if not endpoints:
        if not args.m and not args.a:
            print(f"{host}:{port}")
            print(f"  dns {format_ms(dns_us)} ms")
            print("  no addresses")
            print()
        return 1

    if args.c:
        measure_endpoints(endpoints, args.nqueries, args.timeout_ms, args.delay_ms)
        if args.m:
            for ep in endpoints:
                emit_machine_happy(ts, ep)
        else:
            # When -a already printed a DNS detail block, omit repeating dns_us
            # on the connect block header unless -a was not used.
            show_dns = None if args.a else dns_us
            emit_human_connect_block(
                host, port, show_dns, endpoints, args.s, args.cad_ms
            )

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    hosts = load_hosts(args)
    ts = int(time.time())
    rc = 0
    for host in hosts:
        for port in args.ports:
            if run_target(host, port, args, ts) != 0:
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
