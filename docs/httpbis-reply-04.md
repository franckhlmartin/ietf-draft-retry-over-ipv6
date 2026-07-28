# Draft mailing-list reply (-04 pivot)

Informative only — not part of the Internet-Draft. Paste/adapt to v6ops and/or
httpbis as needed.

---

Subject: draft-martin-retry-over-ipv6-04: dropping new status code; 503 + Retry-Over-IPv6

Thank you for the feedback on status-code registration pressure and closed-
system deployment.

Revision -04 takes that guidance: this document no longer proposes a new HTTP
status code (the earlier 5NN / 566 stand-in).

Planned IPv4 unavailability is now signaled as:

- 503 Service Unavailable
- mandatory Retry-Over-IPv6: ?1 (primary machine trigger for address-family retry)
- optional IPv4-Unavailable-Until, Retry-Over-IPv6-Token, and
  Retry-Over-IPv6-Recovery
- optional application/problem+json body with registered problem type
  urn:ietf:params:problem:ipv4-unavailable

Why not Retry-After alone on 503: Retry-After means wait, then retry the same
path. Aware clients need an immediate IPv6 retry of the same target URI, which
is a different semantic — hence Retry-Over-IPv6 and IPv4-Unavailable-Until.

Why not only a new Content-Type / body: Content-Type types the representation;
headers remain the control plane so clients can act without parsing a body, and
so HTML/plain human responses still carry the same machine signal.

The draft keeps a short Design Alternatives section covering a new status code,
503+Retry-After only, 500+body, a dedicated media type without headers, 3xx, and
421.

Comments welcome on -04.
