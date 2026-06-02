#!/usr/bin/env python3
"""Post-process mmark XML for idnits and RFC 7991 compliance.

mmark v2 wraps normative and informative reference sections in an outer
<references><name>References</name> element. idnits rejects that wrapper;
only Normative References and Informative References are valid section names.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


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
    path.write_text(fix_references_wrapper(path.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main()
