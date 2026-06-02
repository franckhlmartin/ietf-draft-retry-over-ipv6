%%%
title = "HTTP Signaling of Planned IPv4 Unavailability"
abbrev = "retry-over-ipv6"
ipr = "trust200902"
area = "art"
workgroup = "HTTP Working Group"
keyword = ["IPv6", "IPv4", "HTTP", "retry", "dual-stack", "Happy Eyeballs"]

[seriesInfo]
name = "Internet-Draft"
value = "draft-martin-retry-over-ipv6-00"
stream = "IETF"
status = "standard"

date = 2026-06-06T00:00:00Z

[[author]]
initials = "F."
surname = "Martin"
fullname = "Franck Martin"
organization = "Peachymango.org"
  [author.address]
  email = "franck@peachymango.org"
%%%

.# Abstract

As operators transition services to IPv6-only, planned IPv4 outages help identify
remaining dependencies before permanent decommission. Such outages must be
measurable, reversible, and understandable to end users. This document defines
the `566` (IPv4 Unavailable) HTTP response status code and associated header
fields that signal an intentional, often time-bounded IPv4 outage, instruct
aware clients to retry over IPv6 after closing the IPv4 connection, and allow
clients to confirm successful IPv6 recovery via an optional correlation token
so operators can distinguish soft failures from hard failures in centralized
logs. The mechanism supports coordinated events (for example, 6/6 IPv6 Day
drills), staged enterprise rollouts, and permanent IPv6-only migration. Legacy
clients receive a conventional server error as specified in [@!RFC9110] and MAY
use the response body for human-readable guidance.

{mainmatter}

# Introduction

## Why Planned IPv4 Outages

IPv6 deployment has been validated through coordinated industry events. On
World IPv6 Day (8 June 2011), major content providers enabled IPv6 for 24 hours
to measure brokenness in clients, networks, and middleboxes
[@?WORLD-IPV6-DAY]. World IPv6 Launch (6 June 2012) moved many of those sites
to permanently enabled IPv6 [@?WORLD-IPV6-LAUNCH]. Some participants retained
IPv6; others reverted toward IPv4-only operation until a later 6/6 commitment.
These events tested enabling IPv6; the inverse problem — identifying what still
breaks when IPv4 is intentionally unavailable — remains under-specified at the
application layer.

Operators have adopted time-bounded **planned IPv4 outages** as a complement:
deliberately making IPv4 service unavailable for minutes, hours, or days to
expose software, protocol, and operational gaps before irreversible
decommissioning.

Network-layer IPv4 removal is a poor fit for staged drills:

* Rollback is hard — routing, ACL, and DNS changes propagate slowly and are
  error-prone under pressure.
* End users lack context — a silent timeout looks like a site outage, not an
  IPv4-path policy.
* Impact is unmeasured — without an HTTP-visible signal, operators cannot count
  affected clients or quantify business loss (even a small percentage of
  requests can be material).

HTTP-layer IPv4 outages address these gaps:

* **Easy rollback** — disable the `566` policy at the load balancer or origin
  without waiting for DNS TTL expiry.
* **Advance communication** — site banners, email, and status pages can
  reference the same window as `IPv4-Unavailable-Until`.
* **Clear user messaging** — a response body explains that IPv4 is
  intentionally unavailable, when service may resume, and that IPv6 (or
  contacting an ISP or IT department) is the remedy.
* **Operator metrics** — count `566` responses and join them with
  `Retry-Over-IPv6-Recovery` (and optional tokens) in centralized logs to
  estimate soft versus hard failure rates.

## Technical Motivation

Many operators plan to remove or disable IPv4 while retaining IPv6 service.
During migration, maintenance, or decommissioning, a client that connects over
IPv4 may observe connection failures or HTTP errors even though the same origin
remains available over IPv6.

IPv4-only clients cannot switch address families; they need a clear, loggable
explanation that the service no longer supports IPv4 (optionally until a stated
time). Dual-stack clients on networks where Happy Eyeballs [@!RFC8305] selects
IPv4 may treat the failure as a general outage unless the server explicitly
signals that IPv4 is intentionally unavailable and IPv6 should be used instead.

Application-to-application traffic (REST, gRPC over HTTP/2, and similar
protocols) benefits from a machine-readable signal distinct from connectivity
failures on other addresses. For example, a gRPC client that tries multiple
resolved addresses may surface an error from the first failing attempt, masking
the fact that the meaningful signal was returned on an IPv4 connection.

## Requirements Language

The key words "**MUST**", "**MUST NOT**", "**REQUIRED**", "**SHALL**",
"**SHALL NOT**", "**SHOULD**", "**SHOULD NOT**", "**RECOMMENDED**",
"**NOT RECOMMENDED**", "**MAY**", and "**OPTIONAL**" in this document are to be
interpreted as described in BCP 14 [@!RFC2119] [@!RFC8174] when, and only when,
they appear in all capitals, as shown here.

## Terminology

This document uses terms from [@!RFC9110]. Additional terms:

**Authority**: The host and port derived from the target URI.

**Planned IPv4 outage**: An operator-initiated period during which IPv4 HTTP
service for an authority is intentionally unavailable while IPv6 service is
expected to remain available.

**Aware client**: A client implementation that supports the mechanisms defined
in this document.

**Legacy client**: A client that does not implement this document.

**Soft failure**: A client receives `566` (or transitional `503` with
`Retry-Over-IPv6`) over IPv4 and subsequently completes the same request
successfully over IPv6.

**Hard failure**: A client receives `566` over IPv4 but cannot successfully
complete the request over IPv6.

# Overview

When IPv4 service is intentionally unavailable for an authority, the responding
entity that receives a request over IPv4 sends:

1. **`566` (IPv4 Unavailable)**, or during transitional deployments **`503
   Service Unavailable`** with the same header fields — the IPv4 path is
   unavailable; the service is not a general outage if IPv6 is expected to work.
2. **`Retry-Over-IPv6: ?1`** — the client should retry the same request over
   IPv6.
3. **`IPv4-Unavailable-Until`** (optional) — when IPv4 service may be restored.
4. **`Retry-Over-IPv6-Token`** (optional, on the IPv4-unavailability response)
   and **`Retry-Over-IPv6-Recovery`** (on a successful IPv6 retry) — optional
   telemetry so operators can correlate soft failures across load-balanced
   backends.

Implementations that cannot emit `566` (for example, before the status code is
registered or supported by their HTTP stack) **MAY** send **`503 Service
Unavailable`** instead, with **`Retry-Over-IPv6: ?1`** and the other response
header fields defined in this document. Aware clients treat `503` with
`Retry-Over-IPv6: ?1` the same as `566` when deciding to retry over IPv6 (see
(#retry-over-ipv6) and (#client-requirements)). Operators **SHOULD** use `566`
once their deployment supports it.

The responding entity **MUST** send `566` (or `503` with `Retry-Over-IPv6: ?1`
during transitional deployments) only when the request was received over an
IPv4 transport connection on the client-facing path (see
(#server-and-operational-considerations)).

Clients that do not implement this specification and receive an unrecognized
`566` status code MUST treat it as `500 Internal Server Error`, as required by
Section 15 of [@!RFC9110]. Operators SHOULD include a response body explaining
the IPv4 outage for human readers and for logging by generic HTTP clients.

# The 566 IPv4 Unavailable Status Code

The `566` (IPv4 Unavailable) status code indicates that the responding entity
is intentionally not offering the requested service over IPv4 for this authority,
while service over IPv6 is expected to be available. The client SHOULD retry
the same request to the same target URI using IPv6 if IPv6 connectivity is
available.

This status code applies when the responding entity received the request over
IPv4. It MUST NOT be used to indicate general server overload or maintenance
that affects all address families (`503 Service Unavailable` is appropriate for
that case). It is generally inappropriate on the IPv4 loopback interface (see
(#when-to-send-566)).

Intermediaries and caches MUST NOT transform a `566` response into a successful
response. Caching of `566` is governed by normal HTTP cache rules
[@?RFC9111]; operators SHOULD send appropriate `Cache-Control` when responses
are generated dynamically based on the client-facing address family.

A `566` response SHOULD include `Retry-Over-IPv6` as defined in
(#retry-over-ipv6). It MAY include `IPv4-Unavailable-Until`, a response body,
and `Retry-Over-IPv6-Token`.

## Status Code Selection

This document registers `566` (IPv4 Unavailable) in the HTTP status code range
512–599, which is currently unassigned. The code number is chosen to align with
**6/6 (June 6)**, the date used for coordinated IPv6 deployment events such as
World IPv6 Launch, and embeds **66** as a mnemonic for IPv6 within the 5xx
server-error class. This mnemonic is for human operability only; protocol
behavior does not depend on the numeric value beyond its 5xx class.

## Example

~~~ http
HTTP/1.1 566 IPv4 Unavailable
Retry-Over-IPv6: ?1
IPv4-Unavailable-Until: Sun, 07 Jun 2026 00:00:00 GMT
Retry-Over-IPv6-Token: "a1b2c3d4e5f6"
Content-Type: application/problem+json
Content-Length: 0

~~~

# Response Header Fields

## Retry-Over-IPv6 {#retry-over-ipv6}

The `Retry-Over-IPv6` response header field indicates that the client should
retry the same request over IPv6.

### Syntax

The field value is a Boolean (see [@!RFC9651]):

~~~ abnf
Retry-Over-IPv6 = "Retry-Over-IPv6" OWS ":" OWS boolean
boolean         = "?0" / "?1"
~~~

On `566` responses, the value **MUST** be `?1`.

For transitional deployments, `503 Service Unavailable` responses MAY include
`Retry-Over-IPv6: ?1`; once `566` is widely supported, operators SHOULD NOT
rely on the `503` fallback.

### Semantics

When a client receives `Retry-Over-IPv6: ?1`, it SHOULD retry the same request
to the same target URI using IPv6 transport if IPv6 connectivity is available,
but only if the response was received on an IPv4 connection. If the client
already used IPv6 for that attempt, it MUST NOT retry solely because of this
header field.

The header field conveys intent only. It does not guarantee that a retry over
IPv6 will succeed.

This header field is a response header field as defined in Section 6.3 of
[@!RFC9110].

## IPv4-Unavailable-Until

The `IPv4-Unavailable-Until` response header field indicates the time after
which IPv4 service for this authority may be restored.

### Syntax

~~~ abnf
IPv4-Unavailable-Until = "IPv4-Unavailable-Until" OWS ":"
                          OWS HTTP-date
~~~

`HTTP-date` is defined in Section 5.6.7 of [@!RFC9110].

### Semantics

For a permanent IPv6-only transition, this field MAY be omitted; permanence
SHOULD be stated in the response body instead.

This field is informational for logging and client caching. It does not mean
the client should wait until that time before retrying over IPv6 — the IPv6
retry SHOULD happen promptly (subject to the client algorithm in
(#client-requirements)).

`IPv4-Unavailable-Until` differs from `Retry-After` [@!RFC9110]: `Retry-After`
indicates how long to wait before a follow-up request in overload or rate-limit
scenarios, while `IPv4-Unavailable-Until` marks the end of a planned IPv4
unavailability window.

Operators MAY also send `Retry-After` for legacy clients that do not understand
`566` or `IPv4-Unavailable-Until`.

## Retry-Over-IPv6-Token

The `Retry-Over-IPv6-Token` response header field carries an opaque token that
a client MAY echo on a subsequent successful IPv6 retry so operators can
correlate a `566` response with a recovery in centralized logs.

### Syntax

~~~ abnf
Retry-Over-IPv6-Token = "Retry-Over-IPv6-Token" OWS ":"
                        OWS quoted-string
~~~

`quoted-string` is defined in Section 5.6.4 of [@!RFC9110].

### Semantics

The token is opaque to the client. The client MUST NOT interpret its internal
structure.

Tokens SHOULD be short-lived (on the order of minutes, and not extending beyond
`IPv4-Unavailable-Until` when that header is present). Deployments SHOULD use
stateless tokens verifiable or loggable by any node in a load-balanced fleet
without session affinity to a particular origin server.

This header is RECOMMENDED on `566` responses when operators want pairwise
566-to-recovery correlation across backends.

## Legacy Client Compatibility

Legacy clients that do not implement this document might still benefit from:

* `Retry-After` with seconds until the outage ends.
* `Cache-Control: no-store` on dynamically generated outage responses.
* A response body with plain language, for example: "This service no longer
  supports IPv4. Please use IPv6. IPv4 service resumes at …"

Aware clients MUST prefer `566`, `Retry-Over-IPv6`, and `IPv4-Unavailable-Until`
over inferring outage semantics from the body alone.

# Request Header Fields

## Retry-Over-IPv6-Recovery {#retry-over-ipv6-recovery}

The `Retry-Over-IPv6-Recovery` request header field allows an aware client to
confirm that a successful request over IPv6 is the retry following a `566`
response (or transitional `503` with `Retry-Over-IPv6: ?1`) received over IPv4.

### Syntax

~~~ abnf
Retry-Over-IPv6-Recovery = "Retry-Over-IPv6-Recovery" OWS ":"
                           OWS "recovered"
                           *( OWS ";" OWS recovery-param )
recovery-param           = token "=" ( token / quoted-string )
~~~

The only recovery parameter defined by this document is `token`, whose value
SHOULD be copied from `Retry-Over-IPv6-Token` on the prior `566` response.

### Semantics

The field value `recovered` means: the responding entity previously returned
`566` (or `503` with `Retry-Over-IPv6: ?1`) on an IPv4 connection for this
logical request attempt, and this request is the successful retry over IPv6.

The client MUST send this header on the first successful IPv6 request that
follows such a response for the same target URI. The client MUST NOT send it on
every subsequent request to the authority.

The client MUST NOT send this header to unrelated origins. The header MUST NOT
contain personally identifiable information.

There is no failure variant defined in this document. If the IPv6 connection
attempt fails before any HTTP response is received, the client cannot report that
failure in-band to the origin during a full IPv4 outage.

### Connection Lifecycle

In typical implementations, a client does not keep the IPv4 connection open while
also retrying the same request over IPv6. Maintaining both connections in
parallel for one logical request increases operational complexity (connection
state, cancellation, and handling of duplicate or late responses) and is
therefore uncommon.

For this reason, `Retry-Over-IPv6-Recovery` is carried on the **IPv6** retry
request. Operators **MUST NOT** expect recovery signaling on the IPv4
connection that received `566` (or `503` with `Retry-Over-IPv6: ?1`).

A typical sequence is:

1. Receive `566` (and optional `Retry-Over-IPv6-Token`) on IPv4.
2. Close or abandon the IPv4 connection.
3. Open a new connection over IPv6 and retry the same request.
4. On success, include `Retry-Over-IPv6-Recovery` on that IPv6 request.

### Cross-Backend Logging

In load-balanced deployments, the `566` response and the recovery request often
reach different origin servers. Correlation is an operator responsibility:

* Log `566` events with `Retry-Over-IPv6-Token` at the edge, load balancer, or
  origin.
* Log `Retry-Over-IPv6-Recovery` (and echoed `token`) at the same aggregation
  tier when possible.
* Join events off-box by token across all backend logs.

Operators SHOULD NOT assume that the origin server that emitted `566` will
receive the recovery report.

Without tokens, operators MAY compare aggregate `566` counts with aggregate
recovery counts over an outage window; this yields ratio estimates only, not
per-session pairing.

### Interaction with Happy Eyeballs

Implementations using the connection establishment algorithm in [@!RFC8305]
MAY attempt IPv4 and IPv6 connections in parallel, with the IPv4 attempt often
delayed relative to IPv6.

Implications:

* If IPv6 succeeds first, the client MAY cancel the IPv4 attempt before `566`
  is received. No `Retry-Over-IPv6-Recovery` is sent. `566` counts may
  under-represent total exposure — this is often the desired outcome during an
  outage.
* The client MUST send `Retry-Over-IPv6-Recovery` only if it fully received
  `566` (or `503` with `Retry-Over-IPv6: ?1`) on an IPv4 connection for this
  logical request attempt.
* If IPv6 already succeeded for this logical request attempt via Happy
  Eyeballs, the client MUST NOT treat a late or abandoned IPv4 `566` as
  requiring another IPv6 retry or recovery signal.

Operators interpreting `566` and recovery metrics during planned outages SHOULD
account for Happy Eyeballs race behavior.

### Example

~~~ http
GET /api/v1/resource HTTP/1.1
Host: example.com
Retry-Over-IPv6-Recovery: recovered; token="a1b2c3d4e5f6"

~~~

# Response Body

Responses with `566` SHOULD include a body explaining the planned IPv4 outage
for legacy clients and human readers.

For machine-readable errors, deployments MAY use Problem Details
[@?RFC9457], for example:

~~~ json
{
  "type": "about:blank",
  "title": "IPv4 Unavailable",
  "status": 566,
  "detail": "IPv4 unavailable until 2026-06-07T00:00:00Z.",
  "retryOverIPv6": true,
  "ipv4UnavailableUntil": "2026-06-07T00:00:00Z"
}
~~~

For browsers, `Content-Type: text/html` with equivalent text is sufficient.

# Client Requirements {#client-requirements}

## Processing 566

When a client receives `566` (or `503` with `Retry-Over-IPv6: ?1`):

1. If the client knows the response arrived on an IPv4 connection, it SHOULD
   proceed with an IPv6 retry as below.
2. If the address family is unknown, it MAY retry over IPv6 once.
3. If Happy Eyeballs [@!RFC8305] already delivered a successful response for
   this logical request attempt over IPv6, it MUST NOT perform another retry or
   send `Retry-Over-IPv6-Recovery` based on a late IPv4 response.

## IPv6 Retry

The client SHOULD close or abandon the IPv4 connection before retrying over IPv6,
consistent with the lifecycle described in (#retry-over-ipv6-recovery). The
retry MUST use the same method, target URI, and authority. The client SHOULD force address-family selection to IPv6 for this
retry. The client MUST NOT change the host, scheme, or port solely because of
`566` or `Retry-Over-IPv6`.

## Loop Prevention

The client MUST NOT perform more than one IPv4-to-IPv6 retry per logical
request attempt triggered by `566` or `Retry-Over-IPv6`.

After receiving `566`, the client SHOULD prefer IPv6 for subsequent connections
to the authority until `IPv4-Unavailable-Until` (if present) or for a default
period (for example, 10 minutes).

If the IPv6 retry fails with connectivity errors, the client SHOULD apply
backoff before further attempts and SHOULD NOT fall back to IPv4 while
`IPv4-Unavailable-Until` is in the future.

## IPv4-Only Clients

Clients without IPv6 connectivity cannot retry over IPv6. They SHOULD surface
`IPv4-Unavailable-Until` (if present) and the response body to the user or
calling application for logging and support tickets.

## Recovery Signaling

On the first successful IPv6 request following a fully received `566` over IPv4,
the client SHOULD send `Retry-Over-IPv6-Recovery: recovered` and SHOULD echo
`Retry-Over-IPv6-Token` in the `token` parameter when a token was provided.

## Idempotent Methods

For safe methods [@!RFC9110], automatic retry is generally acceptable. For
non-idempotent methods such as `POST`, clients SHOULD retry only when the
application can tolerate duplicate processing. Operators SHOULD prefer applying
`566` to idempotent methods during outage tests, or document application-level
deduplication for APIs that require non-idempotent methods.

## NAT64 and Translation

Clients on translated IPv4 paths (for example NAT64/464XLAT) might not be able
to initiate a native IPv6 retry even when dual-stack is reported at the API
layer. Implementations SHOULD present the response body explanation to the user;
operators SHOULD not assume all "IPv4" clients can switch address families.

# Server and Operational Considerations {#server-and-operational-considerations}

## When to Send 566 {#when-to-send-566}

The responding entity SHOULD send `566` when:

* IPv4 HTTP service for the authority is intentionally unavailable;
* IPv6 service for the requested resource is expected to be available; and
* The request was received over IPv4 on the client-facing path.

The responding entity MAY omit `566` (and the transitional `503` with
`Retry-Over-IPv6`) for requests received on the IPv4 loopback interface — for
example, when the client-facing connection uses addresses in `127.0.0.0/8`
such as `127.0.0.1`. Routable IPv4 service may be disabled during a planned
outage while loopback remains available for local health checks, monitoring, and
administration; those clients do not need a signal to retry over IPv6.

Operators MAY run staged rollouts: short canary outages (for example, one
minute), longer windows (hours or a full day aligned with 6/6), and eventually
permanent IPv6-only service.

## Measuring Outage Impact

Operators SHOULD instrument at the edge or load balancer, aggregating all
backends:

Metric | Source
-------|------
566 count | `566` responses logged with optional token
Recovery count | Requests carrying `Retry-Over-IPv6-Recovery`
Paired recoveries | Off-box join on matching token values
Unrecovered 566 | `566 count - paired recoveries` (estimated hard fail and legacy clients)

Hard-failure counts are estimates: clients with no IPv6 path cannot send
recovery signals in-band.

The responding entity SHOULD log recovery headers but MUST NOT alter the
response based on them.

## CDN and Reverse Proxy Deployment

When an edge terminates client IPv4 and connects to an origin over IPv6, the
**edge** sends `566` to the client when IPv4 to the edge is disabled — not
necessarily the origin application. The entity that generates `566` MUST know
the client-facing address family.

## Token Generation

Token format and validation are deployment-specific. Tokens SHOULD be
unguessable, short-lived, and loggable without affinity to the issuing server.

## Transitional Fallback

Deployments that cannot emit `566` MAY use `503 Service Unavailable` with
`Retry-Over-IPv6: ?1` and `IPv4-Unavailable-Until` until `566` support is
available.

# Application Protocol Considerations

This section is informative.

gRPC maps HTTP `566` to `UNAVAILABLE`, the same as `503`. gRPC implementations
SHOULD inspect `Retry-Over-IPv6` on the HTTP response before aggregating
multi-address connection errors, so that an IPv4 policy signal is not confused
with IPv6 connectivity failure.

Suggested error text for logs: "IPv4 unavailable until \<date\>; retry over
IPv6."

Retry policies SHOULD retry over IPv6 when `Retry-Over-IPv6: ?1` is present,
not blindly retry the same address list.

# Deployment Models

This section compares HTTP-layer signaling with other transition techniques.

Method | Limitation for staged outages
-------|------------------------------
DNS-only (withdraw A records) | Hard rollback; poor application errors; difficult time-bounded windows
Network ACL or routing | Complex rollback; timeouts instead of policy signals; weak metrics
Happy Eyeballs alone [@!RFC8305] | Implicit; may misattribute IPv4 policy as IPv6 brokenness
Site banner only | Applications and APIs do not see banners; no automatic IPv6 retry
HTTP 566 + headers (this document) | Reversible at LB; structured retry; measurable soft/hard fail

HTTP-layer signaling complements DNS and network changes, especially when A
records remain or when the client already connected over IPv4.

# Security Considerations

An attacker who can inject or modify HTTP responses could attempt to influence
client connection behavior by adding `Retry-Over-IPv6` or related header
fields. Implementations SHOULD only honor these fields on authenticated
transport connections to the intended authority.

Misuse could cause clients to prefer IPv6 paths that are slower, unavailable, or
subject to different policy than the original IPv4 path. Operators SHOULD
monitor IPv6 reachability before signaling clients to retry over IPv6.

Recovery headers and tokens are operational telemetry, not authentication.
Deployments SHOULD rate-limit and treat forged recovery signals as untrusted
hints.

`566` responses that depend on the client-facing address family SHOULD use
`Cache-Control: private, no-store` when appropriate to avoid cache poisoning.

This mechanism does not by itself provide confidentiality or integrity for
retried requests. Any security properties depend on the underlying transport and
application protocol in use.

# IANA Considerations

IANA is requested to make the following registrations.

## HTTP Status Code

In the "Hypertext Transfer Protocol (HTTP) Status Code Registry"
(<https://www.iana.org/assignments/http-status-codes/>):

Value | Description | Reference
------|-------------|----------
566 | IPv4 Unavailable | This document

## HTTP Field Names

In the "Hypertext Transfer Protocol (HTTP) Field Name Registry"
(<https://www.iana.org/assignments/http-fields/>):

Field Name | Status | Struct | Reference
-----------|--------|--------|----------
Retry-Over-IPv6 | permanent | - | This document
IPv4-Unavailable-Until | permanent | - | This document
Retry-Over-IPv6-Token | permanent | - | This document
Retry-Over-IPv6-Recovery | permanent | - | This document

# Examples

This section is informative.

## Dual-Stack Browser

A browser receives:

~~~ http
HTTP/1.1 566 IPv4 Unavailable
Retry-Over-IPv6: ?1
IPv4-Unavailable-Until: Sun, 07 Jun 2026 00:00:00 GMT
Content-Length: 0

~~~

It closes the IPv4 connection, retries over IPv6, and completes the page load
without displaying an error page.

## Legacy Browser with HTML Body

~~~ http
HTTP/1.1 566 IPv4 Unavailable
Retry-After: 86400
Content-Type: text/html; charset=utf-8
Content-Length: 142

<html><body><p>IPv4 unavailable until 7 June 2026.
Please use IPv6 or contact IT support.</p></body></html>
~~~

## Cross-Backend Recovery

Backend A (IPv4 path) returns:

~~~ http
HTTP/1.1 566 IPv4 Unavailable
Retry-Over-IPv6: ?1
Retry-Over-IPv6-Token: "abc123"
Content-Length: 0

~~~

The client retries over IPv6; backend B receives:

~~~ http
GET /index.html HTTP/1.1
Host: example.com
Retry-Over-IPv6-Recovery: recovered; token="abc123"

~~~

An edge log pipeline joins both events on `token=abc123`.

<reference anchor="WORLD-IPV6-DAY" target="https://www.worldipv6launch.org/faq/">
  <front>
    <title>World IPv6 Launch FAQ</title>
    <author>
      <organization>Internet Society</organization>
    </author>
  </front>
</reference>

<reference anchor="WORLD-IPV6-LAUNCH" target="https://www.worldipv6launch.org/">
  <front>
    <title>World IPv6 Launch</title>
    <author>
      <organization>Internet Society</organization>
    </author>
  </front>
</reference>

{backmatter}
