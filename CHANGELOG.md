# Changelog

Significant content changes to `draft-martin-retry-over-ipv6.md` are recorded here.
Formatting-only edits are omitted unless they affect published semantics.

**Submitted to IETF:** `draft-martin-retry-over-ipv6-00` has been submitted as an
IETF Internet-Draft and is tracked at
<https://datatracker.ietf.org/doc/draft-martin-retry-over-ipv6/>.

## Unreleased

- **Introduction (§1.1):** note that government IPv6 mandates are often only
  partially met, possibly for lack of application-layer transition mechanisms
  this document addresses; additional examples (US OMB M-21-07, Netherlands,
  Washington State EA-04); Czech Republic as rare fixed IPv4 end date.
- **Intended deployment (§1.3):** primary use in operator-controlled /
  closed environments; **SHOULD NOT** routine public-Internet deployment;
  viable interim step when an IPv4 outage is obligatory; public 6/6 drills
  with notice remain **MAY**.
- **Split-stack (§8.5):** container/cloud north-south vs east-west; edge soft
  failure vs internal IPv4; multi-hop drills and metrics correlation.
- **Terminology (§1.5):** soft/hard failure scoped per signaling hop, not
  end-to-end.
- **Measuring outage impact (§8.3):** interpret edge metrics with origin/downstream
  health; split-stack pitfall table.
- **Scope (§1.2):** CNI/prefix delegation out of scope; internal HTTP gateways
  **MAY** use same signaling.
- **Technical motivation (§1.4):** asymmetric dual-stack and internal HTTP
  entry points.
- **CDN/proxy (§8.4):** internal gateway variant; **Deployment models (§10):**
  client-to-signaling-entity limitation.
- **Examples (§13.4):** ingress soft failure with internal IPv4 dependency.
- **Abstract:** intended deployment audience; enterprise/internal focus; no
  section references (idnits).
- **README / CHANGELOG:** note that `-00` is submitted and link to IETF Datatracker.
- **Submission hygiene:** Unicode em/en dashes replaced with ASCII (`---`, `-`)
  for Datatracker XML checks.
- **Build:** `scripts/fix-mmark-xml.py` removes mmark's invalid outer
  `References` wrapper; title-block `date` moved above `[seriesInfo]` (TOML
  scoping).
- **Abstract:** no normative references (idnits); legacy-client wording unchanged
  in meaning.
- **Introduction (§1.1):** IETF 71 (March 2008) meeting-network IPv4 outage as
  early precedent for planned IPv4 drills ([@?IETF71-IPV4-OUTAGE]).
- **Scope (§1.2):** HTTP-first focus (enterprise APIs, microservices); other
  protocols out of scope; HTTP-version-agnostic signaling (HTTP/1.1, HTTP/2,
  HTTP/3) with transport-layer IPv4 detection.
- **Technical motivation (§1.3):** clarify examples as HTTP-carried APIs (REST,
  gRPC, GraphQL, JSON-RPC).
- **HTTP versions (informative):** deployment notes for HTTP/1.1, HTTP/2
  (connection-level `566`), HTTP/3 (QUIC, concurrent connections), and Alt-Svc;
  gRPC subsection retitled.
- **Security considerations (§11):** optional operator-validatable tokens (e.g.
  site identifier + nonce + HMAC) for log filtering; not client authentication.
- **Introduction:** Czech Republic state administration IPv4 end date (6 June
  2032) and need for staged transition before cutover
  ([@?KONEC-IPV4-CZ](https://konecipv4.cz/en/)).
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

## [draft-martin-retry-over-ipv6-00] - 2026-06-06 (submitted)

Initial Internet-Draft: **HTTP Signaling of Planned IPv4 Unavailability**.
Submitted to the IETF; see
<https://datatracker.ietf.org/doc/draft-martin-retry-over-ipv6/>.

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
