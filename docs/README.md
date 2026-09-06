# Planned IPv4 outage drills — call for volunteers

Many organizations must move services to **IPv6-only**. So far, most progress has
been **dual-stack**: keep IPv4 and **add** IPv6. That is relatively easy —
enabling a feature usually does not take anything away from users.

Going **IPv6-only** is different: it means **removing IPv4**. That is a potential
IPv4 outage, with real consequences for apps, devices, and users that still
depend on it. Those consequences need to be **found and controlled before** a
permanent cutover. That is the purpose of this initiative.

We ask operators to run short, **reversible monthly drills**: for a planned
window, stop serving over IPv4 while **keeping the site up on IPv6**, warn users
a week ahead, and measure who recovers automatically versus who stays stuck.
That is cheaper and safer than ripping IPv4 out of the network or DNS (slow to
undo, affects everyone at once, looks like a silent outage, and gives little
hard data).

With more than half of the world’s users already reaching major services over
IPv6 — and some countries at 90% or more — it is time to plan **how** we remove
IPv4. Simply pulling the plug will not work.

**Recommended window:** the **6th of each month (UTC)** — either the full day or
one hour at **06:00–07:00**. Start on an internal or low-risk site if you prefer.
Live examples and a list of participating sites are at the bottom of this page.

This page is also the **server configuration guide** for implementing the signal
from [draft-martin-retry-over-ipv6](../draft-martin-retry-over-ipv6.md)
(**HTTP Signaling of Planned IPv4 Unavailability**). The technical sections
below are for implementers; the next sections are for anyone who needs to
approve or explain the drill.

This material is **not** part of the Internet-Draft. The Markdown draft remains
the normative source.

## In plain language

| Idea | What it means |
|------|----------------|
| Planned IPv4 outage | For a known window, visitors on the older Internet address (IPv4) get a clear “use IPv6” message; visitors on IPv6 keep using the site normally |
| Why do it | Dual-stack *adds* IPv6; IPv6-only *removes* IPv4. Controlled drills find remaining IPv4 dependencies **before** a permanent cutover |
| Why not just “turn off IPv4” in the network | Hard to roll back quickly, hard to limit who is affected, users see timeouts with no explanation, impact is hard to measure |
| What we ask | Join a coordinated monthly window, put up a banner a week ahead, measure results, and share what you learn |
| Who feels what | Updated software can switch to IPv6 and succeed; older or IPv4-only paths see a temporary unavailable page with guidance |

Prefer **operator-controlled** environments first (enterprise intranet, government
network, staging, internal APIs). Public drills are fine when announced early and
kept short.

## Coordinated monthly window (recommendation)

Volunteers should **use the same calendar window** so teams can compare notes.
Current recommendation — **6th of each month (UTC)**:

| Option | When (UTC) | Notes |
|--------|------------|-------|
| Full day | 00:00–24:00 on the 6th | Matches World IPv6 Day / Launch heritage; simplest schedule |
| One hour | **06:00–07:00** on the 6th | Lower impact; good default for public sites |

Show a **site banner at least one week in advance** (date, duration, and that
the service remains available over IPv6). Align any “until” time you publish with
the chosen end of the window.

Live reference deployments (full-day window + 7-day pre-outage banner):

- [pacific.ipv6forum.com](https://pacific.ipv6forum.com)
- [caribbean.ipv6forum.com](https://caribbean.ipv6forum.com)
- [whynoipv6.com](https://whynoipv6.com/)
- [www.peachymango.org](https://www.peachymango.org/)

Source and schedule logic for the IPv6 Forum sites:
[franckhlmartin/ipv6-pacific](https://github.com/franckhlmartin/ipv6-pacific)
(`internal/ipv4outage/`).

### Sample advance notice

**Site banner** (adapt tone to your brand):

> **Planned maintenance — IPv4 path only.** On the **6th of [Month] (UTC)**
> [this site will be unavailable over IPv4 for 24 hours /
> from 06:00 to 07:00 UTC]. The site remains available over **IPv6**. If you
> cannot reach us that day, ask your network provider or IT team whether IPv6 is
> enabled. [Learn more / status page link]

**Status page / email blurb:**

> We are running a scheduled IPv6 readiness drill. During the window above,
> connections that only use IPv4 will see a temporary unavailable message. This
> is intentional and reversible. Service on IPv6 is unchanged. We will publish
> a short summary afterward.

## How to join

### Champions (approve or sponsor)

1. Pick the **full day** or the **one-hour** window on the 6th (UTC).
2. Approve a **week-ahead** banner (and status-page note) using the samples above.
3. Prefer starting on an **internal or low-risk** site; expand after the first drill.
4. Ask your platform or web team to implement the signal using the guides below,
   then **add your public site** to [Sites running the drill](#sites-running-the-drill)
   via a pull request.

### Engineers (implement and measure)

World IPv6 Day and World IPv6 Launch stress-tested *enabling* IPv6. The inverse —
what still breaks when IPv4 is intentionally unavailable — needs a common HTTP
signal. On IPv4 during the window, return `503 Service Unavailable` with
`Retry-Over-IPv6: ?1` (plus optional related fields and a clear body); serve
normally over IPv6; log `Retry-Over-IPv6-Recovery` on successful retries so you
can estimate soft vs hard failures.

1. **Implement** the signal on NGINX, Apache, or another stack (contribute a new
   guide under `docs/` if yours is missing).
2. **Join the coordinated drill** on the 6th (full day or 06:00–07:00 UTC), with
   a banner up a week ahead — or start with a single hostname / internal service.
3. **Report what you learn** — recovery rates, library gaps, config gotchas — via
   [GitHub issues](https://github.com/franckhlmartin/ietf-draft-retry-over-ipv6/issues)
   or the [v6ops](https://www.ietf.org/mailman/listinfo/v6ops/) / httpbis lists.
4. **Wire clients** that understand `Retry-Over-IPv6` (close IPv4, retry over
   IPv6, optionally send `Retry-Over-IPv6-Recovery`).
5. **List your site** in [Sites running the drill](#sites-running-the-drill) via PR.

## Server configuration examples

These guides cover the **server side** of the draft: on an **IPv4 client-facing**
connection during a planned outage, return **`503 Service Unavailable`** with
**`Retry-Over-IPv6: ?1`** (and optional related headers) plus a response body;
serve the application normally over **IPv6**; log `Retry-Over-IPv6-Recovery` on
successful IPv6 retries.

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

See [Coordinated monthly window](#coordinated-monthly-window-recommendation)
above for the volunteer recommendation (full UTC day 6, or 06:00–07:00 UTC on
the 6th, plus a one-week advance banner).

Neither NGINX nor Apache needs an external scheduler for a simple “all day on
the 6th” window: both can read the current day from request-time variables and
enable signaling only then (see [nginx.md](nginx.md) and [apache.md](apache.md)).

Useful patterns:

| Pattern | When to use |
|---------|-------------|
| Native day-of-month gate | Full calendar day on the 6th; no reload required |
| Cron / systemd timer | One-hour window (**06:00–07:00 UTC** recommended), or coordinated fleet enable/disable |
| Handler computes `IPv4-Unavailable-Until` | End of day 6 / start of day 7, or end of a timed window |
| Pre-outage banner | Show planned outage notice for **≥7 days** before the window |

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

## Sites running the drill

Public sites currently emitting planned IPv4-unavailability signaling on the
coordinated monthly window:

| Site | Notes |
|------|-------|
| [pacific.ipv6forum.com](https://pacific.ipv6forum.com) | IPv6 Forum Pacific; [ipv6-pacific](https://github.com/franckhlmartin/ipv6-pacific) |
| [caribbean.ipv6forum.com](https://caribbean.ipv6forum.com) | IPv6 Forum Caribbean; same codebase |
| [whynoipv6.com](https://whynoipv6.com/) | |
| [www.peachymango.org](https://www.peachymango.org/) | |

Running the drill on your dual-stack site? **Add it to this table via a pull
request** so other volunteers can discover peers and compare results.