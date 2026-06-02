# Changelog

Significant content changes to `draft-martin-retry-over-ipv6.md` are recorded here.
Formatting-only edits are omitted unless they affect published semantics.

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
