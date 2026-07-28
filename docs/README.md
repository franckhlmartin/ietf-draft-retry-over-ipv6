# Server configuration examples

Informative examples for implementing
[draft-martin-retry-over-ipv6](../draft-martin-retry-over-ipv6.md)
(**HTTP Signaling of Planned IPv4 Unavailability**) on common HTTP servers and
proxies.

These guides cover the **server side** of the draft: when a request arrives on
an **IPv4 client-facing** connection during a planned outage, return **`503
Service Unavailable`** with **`Retry-Over-IPv6: ?1`** and the other draft header
fields, plus a response body. Serve the application normally over **IPv6**. Log
`Retry-Over-IPv6-Recovery` on successful IPv6 retries for soft/hard failure
metrics.

This material is **not** part of the Internet-Draft. The Markdown draft remains
the normative source.

## Per-server guides

| Server | Guide |
|--------|-------|
| NGINX | [nginx.md](nginx.md) |
| Apache HTTP Server | [apache.md](apache.md) |

Add a new file under `docs/` when contributing another stack (for example
`caddy.md`, `haproxy.md`).

## Status code

Use **`503 Service Unavailable`** with **`Retry-Over-IPv6: ?1`**. The status
alone is ambiguous with overload; the header is required for this signal. Do
**not** invent a custom status such as `566`.

## What the server must do

| Requirement | Behavior |
|-------------|----------|
| Address family | Emit the signal **only** when the client-facing transport is IPv4 |
| Status | `503 Service Unavailable` |
| Headers | `Retry-Over-IPv6: ?1` (**mandatory**); optional `IPv4-Unavailable-Until`, `Retry-Over-IPv6-Token` |
| Cache | Prefer `Cache-Control: private, no-store` |
| Body | Human-readable and/or Problem Details (`application/problem+json`) with type `urn:ietf:params:problem:ipv4-unavailable` |
| Loopback | **MAY** skip signaling for `127.0.0.0/8` (health checks) |
| Methods | Prefer idempotent methods; avoid `POST` without app-level deduplication |
| IPv6 path | Do **not** send this signal on IPv6; serve normally |
| Recovery | Log `Retry-Over-IPv6-Recovery`; do **not** change the response based on it |

Example wire response (from the draft):

```http
HTTP/1.1 503 Service Unavailable
Retry-Over-IPv6: ?1
IPv4-Unavailable-Until: Sun, 07 Jun 2026 00:00:00 GMT
Retry-Over-IPv6-Token: "a1b2c3d4e5f6"
Cache-Control: private, no-store
Content-Type: application/problem+json
```

## Shared response body

Create a Problem Details body the origin can serve from any stack.

**`/var/www/ipv4-unavailable.json`** (adjust path as needed):

```json
{
  "type": "urn:ietf:params:problem:ipv4-unavailable",
  "title": "IPv4 Unavailable",
  "status": 503,
  "detail": "IPv4 unavailable until 2026-06-07T00:00:00Z; retry over IPv6.",
  "ipv4UnavailableUntil": "2026-06-07T00:00:00Z",
  "ipv6OnlySite": "https://ipv6.example.com/"
}
```

Omit `ipv6OnlySite` if you do not publish an IPv6-only-reachable alternate host.
For end-user browsers, prefer an HTML body instead of (or in addition to) JSON;
see the draft response-body section for plain-language guidance.

Set the outage end time consistently in:

- `IPv4-Unavailable-Until` (HTTP-date)
- `ipv4UnavailableUntil` / `detail` in the JSON body
- optional `Retry-After` (seconds) for legacy clients

## Enabling and disabling the outage

| Action | Approach |
|--------|----------|
| Start drill | Flip a config flag (or enable an IPv4-only listener that returns `503` + headers) |
| End drill | Clear the flag or restore normal IPv4 service |
| Rollback | Reload config; no DNS TTL wait |
| Recurring (e.g. 6th of each month) | Gate on calendar day in config, or use cron to flip the flag |

Keep IPv6 listeners serving the real application the entire time. See each
per-server guide for the exact knobs.

### Recurring drills (6th of every month)

Neither NGINX nor Apache needs an external scheduler for a simple “all day on
the 6th” window: both can read the current day from request-time variables and
enable signaling only then (see [nginx.md](nginx.md) and [apache.md](apache.md)).

Useful patterns:

| Pattern | When to use |
|---------|-------------|
| Native day-of-month gate | Full calendar day on the 6th; no reload required |
| Cron / systemd timer | Shorter windows (e.g. 09:00–10:00 UTC), or coordinated fleet enable/disable |
| Handler computes `IPv4-Unavailable-Until` | End of day 6 / start of day 7, or end of a timed window |

Use a consistent timezone (prefer **UTC**) so every node in a fleet agrees on
“the 6th.” Monthly public-Internet drills can be noisy; prefer operator-controlled
environments, or keep windows short and announced (see the draft’s intended
deployment guidance).

## Verification

```bash
# Expect 503 + Retry-Over-IPv6 on IPv4:
curl -4 -sD- https://example.com/ -o /dev/null

# Expect normal success on IPv6 (no Retry-Over-IPv6):
curl -6 -sD- https://example.com/ -o /dev/null

# Simulate recovery header on IPv6 (server must not change status):
curl -6 -sD- https://example.com/ \
  -H 'Retry-Over-IPv6-Recovery: recovered; token="a1b2c3d4e5f6"' \
  -o /dev/null
```

Check access logs for `503` responses that include `Retry-Over-IPv6` and for `Retry-Over-IPv6-Recovery` on
IPv6 requests. Join on token off-box when estimating soft vs hard failures (see
the draft’s measuring-outage section).

## Operational checklist

1. Confirm the host is dual-stack and IPv6 serves the same authority successfully.
2. Prefer applying the signal to **idempotent** methods during drills.
3. Skip **loopback** IPv4 if you rely on local health checks.
4. Send `Cache-Control: private, no-store` on dynamically generated outage responses.
5. Use short-lived, unguessable tokens.
6. Instrument at this hop; do not assume edge soft-failure rates prove IPv6-only readiness for backends (split-stack).
7. On the public Internet, use advance notice and limit duration/frequency.

## References

- Source draft: [`draft-martin-retry-over-ipv6.md`](../draft-martin-retry-over-ipv6.md)
- Datatracker: https://datatracker.ietf.org/doc/draft-martin-retry-over-ipv6/
- Problem Details: [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html)
- HTTP semantics: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)
