# Changelog

Significant content changes to `draft-martin-retry-over-ipv6.md` are recorded here.
Formatting-only edits are omitted unless they affect published semantics.

## Unreleased

- **Happy Eyeballs (§5.1.5):** RFC 8305 scope (transport vs HTTP); IPv6-first
  vs RTT-driven IPv4 preference; `5xx` not defined as race-wide failure per
  RFC 8305 §9.2.
- **Idempotent methods:** brief client retry note restored in §7.3; server and
  operator guidance remains in §8.2 ({#idempotent-methods}).
- **Response body (§6):** guidance for non-technical readers (IPv6 transition
  context, relay text for ISP/IT, no self-service assumptions); standard
  example plain-text and HTML wording.
- Server guidance: operators **MAY** omit `566` on the IPv4 loopback interface
  (`127.0.0.0/8`), since loopback often stays up during planned routable IPv4
  outages (health checks, local admin).

## [draft-martin-retry-over-ipv6-00] — 2026-06-06

Initial Internet-Draft: **HTTP Signaling of Planned IPv4 Unavailability**.

- Motivation for planned IPv4 outages (World IPv6 Day/Launch context, HTTP-layer
  vs network/DNS-only approaches).
- **`566` (IPv4 Unavailable)** status code with rationale for the 6/6 mnemonic;
  transitional **`503`** fallback with **`Retry-Over-IPv6: ?1`**.
- Response header fields: **`Retry-Over-IPv6`**, **`IPv4-Unavailable-Until`**,
  **`Retry-Over-IPv6-Token`** (ABNF and semantics).
- Request header **`Retry-Over-IPv6-Recovery`**, connection lifecycle guidance,
  cross-backend logging, and Happy Eyeballs interaction.
- Client requirements (IPv6 retry, loop prevention, recovery signaling,
  idempotent methods, NAT64 notes).
- Server and operational considerations (when to send 566, metrics, CDN/proxy,
  token generation, transitional fallback).
- Informative application-protocol notes (gRPC), deployment model comparison,
  security considerations, IANA registrations, and worked examples.
