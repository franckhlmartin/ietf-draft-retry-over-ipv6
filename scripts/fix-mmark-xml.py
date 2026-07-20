#!/usr/bin/env python3
"""Post-process mmark XML for idnits.

1. Unwrap mmark's outer <references><name>References</name> (invalid for idnits).
2. Drop rfc submissionType when Datatracker has stream=null for this draft
   (individual I-Ds); otherwise idnits reports SUBMISSION_TYPE_UNEXPECTED.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def fix_submission_type(text: str) -> str:
    return re.sub(r'(<rfc[^>]*)\s+submissionType="[^"]*"', r"\1", text, count=1)


def fix_references_wrapper(text: str) -> str:
    open_tag = "<references><name>References</name>\n"
    if open_tag not in text:
        return text
    text = text.replace(open_tag, "", 1)
    text, n = re.subn(
        r"</references>\n</references>\n\n</back>",
        "</references>\n\n</back>",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit(
            "fix-mmark-xml: expected double </references> before </back>; "
            "mmark output format may have changed"
        )
    return text


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <draft.xml>")
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    text = fix_submission_type(text)
    text = fix_references_wrapper(text)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
