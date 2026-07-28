# Changelog

Significant content changes to `draft-martin-retry-over-ipv6.md` are recorded here.
Formatting-only edits are omitted unless they affect published semantics.

**Submitted to IETF:** `draft-martin-retry-over-ipv6-00` (2026-06-06) and
`draft-martin-retry-over-ipv6-01` (2026-06-11) are on the
[IETF Datatracker](https://datatracker.ietf.org/doc/draft-martin-retry-over-ipv6/).

## [draft-martin-retry-over-ipv6-04] - 2026-07-28

- **Introduction:** note DNS/network IPv4 withdrawal is all-or-nothing for blast
  radius; HTTP-layer signaling can limit exposure per host/path/slice.
- **Semantic pivot:** drop the proposed `5NN` / `566` status code. Planned IPv4
  unavailability is signaled with existing **`503 Service Unavailable`** plus
  **mandatory** `Retry-Over-IPv6: ?1`.
- **Design alternatives (§):** informative discussion of new status code,
  `503`+`Retry-After` only, `500`+body, dedicated media type without headers,
  `3xx`, and `421`; document why headers + `503` + Problem Details `type` wins.
- **Problem Details:** register `urn:ietf:params:problem:ipv4-unavailable`;
  prefer `application/problem+json` (no new media type). Headers remain the
  primary machine trigger for address-family retry.
- **IANA:** remove HTTP status code registration; keep field names; add problem
  type registration. Cite RFC 9457 as normative for the problem type.
- **Ops/metrics:** note that `503` alone mixes with overload; count the header
  (or a custom metric). Prometheus/Grafana do not auto-parse problem+json.
- **gRPC:** rely on existing `503`→`UNAVAILABLE` mapping; honor
  `Retry-Over-IPv6` before same-path retry.
- **Docs:** server examples (`docs/`) updated from `566` to `503`+headers.
- Version bump to `-04`.

## [draft-martin-retry-over-ipv6-03] - 2026-07-19

- **Intended deployment (§1.3):** soften public-Internet guidance from
  **SHOULD NOT** to use-with-care (annoyance, support load, advance notice);
  note that even controlled environments need a shared signal because operators
  do not control all software and libraries.
- **About This Document:** removable note with GitHub source, Datatracker,
  v6ops discussion, httpbis expert input; tests use `566`, prose uses `5NN`.
- **Status code:** normative `5NN` placeholder per RFC 9110 §16.2.2; soft-request
  IANA assign **566**; 505 analogy; expanded new-status-code checklist (scope,
  content, cacheability); why not 3xx (no IPv6-only URI flag, loop risk,
  DNS/cert cost, IPv4-only clients get connection failures not logged HTTP errors).
- **Response body:** optional IPv6-only-reachable alternate site link for humans
  (examples use `example.com` / `ipv6.example.com` per RFC 2606); separate
  example bodies with and without that link; moderate ISP-help wording so
  Happy Eyeballs / client preference is not blamed on the provider; MAY
  suggest a "what is my IP" or IPv6 evaluation check (e.g. test-ipv6.com);
  machines keep same-authority `Retry-Over-IPv6`.
- **IANA / Security:** soft-request wording; advisory-link security notes.
- **Build:** set `consensus = true` in the Markdown title block (mmark);
  wrap long HTML example URL in the draft text.
- Version bump to `-03`.

## [draft-martin-retry-over-ipv6-02] - 2026-06-30

- **Status code selection (§3.1):** informative rationale for 5xx class vs
  hypothetical 466 (4xx); legacy x00 fallback per RFC 9110 §15; why not 421;
  caching note.
- **Happy Eyeballs (§5.1.5):** RFC 6555/8305/HEv3 scope; typical 566 race
  outcomes; informative browser/gRPC/Rest.li retry behavior (no automatic
  IPv6 retry without this spec).
- **gRPC (§10):** cite HTTP-to-gRPC status mapping; 566 → UNAVAILABLE vs
  default UNKNOWN for unregistered codes.
- **Anchors:** {#grpc-and-other-http-apis}, {#transitional-fallback},
  {#security-considerations}.
- **References:** GRPC-HTTP-MAPPING, HEV3 (informative).
- Version bump to `-02`.

## [draft-martin-retry-over-ipv6-01] - 2026-06-11 (submitted)

Submitted to the IETF; see
<https://datatracker.ietf.org/doc/draft-martin-retry-over-ipv6/>.

- **Introduction (§1.1):** note that government IPv6 mandates are often only
  partially met, possibly for lack of application-layer transition mechanisms
  this document addresses; additional examples (US OMB M-21-07, Netherlands,
  Washington State EA-04); Czech Republic as rare fixed IPv4 end date; IETF 71
  (March 2008) meeting-network IPv4 outage as early precedent
  ([@?IETF71-IPV4-OUTAGE]).
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
- **Scope (§1.2):** HTTP-first focus (enterprise APIs, microservices); CNI/prefix
  delegation out of scope; internal HTTP gateways **MAY** use same signaling;
  HTTP-version-agnostic signaling (HTTP/1.1, HTTP/2, HTTP/3) with
  transport-layer IPv4 detection.
- **Technical motivation (§1.4):** asymmetric dual-stack, internal HTTP entry
  points; clarify examples as HTTP-carried APIs (REST, gRPC, GraphQL, JSON-RPC).
- **CDN/proxy (§8.4):** internal gateway variant; **Deployment models (§10):**
  client-to-signaling-entity limitation.
- **Examples (§13.4):** ingress soft failure with internal IPv4 dependency.
- **Abstract:** intended deployment audience; enterprise/internal focus; no
  section references (idnits); no normative references (idnits).
- **README / CHANGELOG:** note that `-00` is submitted and link to IETF Datatracker.
- **Submission hygiene:** Unicode em/en dashes replaced with ASCII (`---`, `-`)
  for Datatracker XML checks.
- **Build:** `scripts/fix-mmark-xml.py` removes mmark's invalid outer
  `References` wrapper; title-block `date` moved above `[seriesInfo]` (TOML
  scoping).
- **HTTP versions (informative):** deployment notes for HTTP/1.1, HTTP/2
  (connection-level `566`), HTTP/3 (QUIC, concurrent connections), and Alt-Svc;
  gRPC subsection retitled.
- **Security considerations (§11):** optional operator-validatable tokens (e.g.
  site identifier + nonce + HMAC) for log filtering; not client authentication.
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
