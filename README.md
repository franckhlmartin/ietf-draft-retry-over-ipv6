# ietf-draft-retry-over-ipv6

This repository contains the source for the IETF Internet-Draft:
**"HTTP Signaling of Planned IPv4 Unavailability"**.

**Source of truth:** `draft-martin-retry-over-ipv6.md` is the only authoritative
source. The repository also includes generated `draft-martin-retry-over-ipv6-00.xml`,
`.txt`, and `.html` files so you can read the draft on GitHub without building
locally. Those copies may be out of date if someone edits the Markdown without
running `make` and committing the outputs; when in doubt, build from the `.md`
file or trust the version on the IETF Datatracker after submission.

## Building

Install the toolchain (or let `make` bootstrap mmark and xml2rfc automatically):

- [Go](https://go.dev/dl/) — for mmark
- Python 3.10+ — for xml2rfc (a project `.venv` is created on first build)
- [idnits](https://github.com/ietf-tools/idnits) (Node.js 20+, optional for lint): `npm install -g @ietf-tools/idnits`

Then build from the repository root:

```sh
make          # install missing tools, then generate XML, text, and HTML
make lint     # run idnits on the generated XML
make clean    # remove generated outputs
make clean-all # also remove the local .venv
```

Before submitting, run `make` and commit the updated `.xml`, `.txt`, and `.html`
if you want the GitHub copies to stay in sync. The submission file is
`draft-martin-retry-over-ipv6-00.xml`. Upload it to the
[IETF Datatracker submission tool](https://datatracker.ietf.org/submit/).

When editing the Markdown source, use [mmark](https://github.com/mmarkdown/mmark)
conventions: internal links are `(#anchor)` (not `{{anchor}}`), and tables use
`col1 | col2` with a `---|---` header row (not GitHub-style `| col |` tables).

## License

All contributions to this draft are subject to the **IETF Trust Legal Provisions (BCP 78 / RFC 5378)**.
See [https://trustee.ietf.org/license-info](https://trustee.ietf.org/license-info) for details.

## Contributing

Pull requests are welcome! Please ensure your contributions comply with IETF policies.
