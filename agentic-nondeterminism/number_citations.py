#!/usr/bin/env python3
"""
number_citations.py

Preprocess LLM-to-IAS.adoc for numeric IEEE-style citations.

Authoring convention:
  - In the body text, citations use AsciiDoc-style cross references: <<key>>
    or comma-separated sequences like <<key1>>, <<key2>>.
  - In the References section, each reference begins with an anchor [[key]]:

        * [[key]] Author, Title, ...

This script:
  1. Parses the References section to collect keys in order of appearance.
  2. Assigns each key an integer citation number (1-based).
  3. Rewrites <<key>> in the body as [n], and sequences as [n1, n2, ...].
  4. Rewrites the References section as a numbered list [n] ... in the same order.

The transformed document is written to stdout. The original source is untouched.
"""

import re
import sys
from typing import Dict, List, Tuple


def split_sections(text: str) -> Tuple[str, str, str]:
    """Split the document into (before_refs, references_block, after_refs)."""
    m = re.search(r"^== References\s*$", text, flags=re.MULTILINE)
    if not m:
        return text, "", ""
    start = m.start()
    # Find next top-level section or end of file
    m_next = re.search(r"^==\s+[^=\s].*$", text[start + 1 :], flags=re.MULTILINE)
    if m_next:
        refs_end = start + 1 + m_next.start()
    else:
        refs_end = len(text)
    before = text[:start]
    refs = text[start:refs_end]
    after = text[refs_end:]
    return before, refs, after


def parse_reference_keys(refs: str) -> Tuple[List[str], Dict[str, int]]:
    """
    Extract reference keys from lines like:
      * [[key]] ...
    Returns (ordered_keys, key_to_num).
    """
    keys: List[str] = []
    key_to_num: Dict[str, int] = {}
    for line in refs.splitlines():
        m = re.search(r"\[\[([^\]]+)\]\]", line)
        if m:
            key = m.group(1).strip()
            if key not in key_to_num:
                keys.append(key)
                key_to_num[key] = len(keys)
    return keys, key_to_num


def replace_citations(body: str, key_to_num: Dict[str, int]) -> str:
    """
    Replace <<key>> and <<key1>>, <<key2>> sequences with numeric [n] citations.
    We preserve the original ordering of keys within each citation group.
    """

    # Pattern to match one or more <<key>> with optional commas/whitespace
    pattern = re.compile(
        r"""
        (                           # whole match
          <<[^>]+>>                 # first <<key>>
          (?:\s*,\s*<<[^>]+>>)*     # zero or more , <<key>>
        )
        """,
        re.VERBOSE,
    )

    def repl(match: re.Match) -> str:
        group = match.group(1)
        # Extract individual keys
        keys = re.findall(r"<<\s*([^>]+?)\s*>>", group)
        nums: List[str] = []
        for k in keys:
            if k not in key_to_num:
                # If a key is unknown, leave it as-is to avoid silent corruption
                return group
            nums.append(str(key_to_num[k]))
        # Collapse to [n] or [n1, n2, ...]
        return "[" + ", ".join(nums) + "]"

    return pattern.sub(repl, body)


def renumber_references(refs: str, ordered_keys: List[str]) -> str:
    """
    Rewrite the References section from:
      * [[key]] ...
    to:
      * [n] ...
    using the order in ordered_keys.
    """
    key_to_num = {k: i + 1 for i, k in enumerate(ordered_keys)}
    out_lines: List[str] = []
    for line in refs.splitlines():
        m = re.search(r"\[\[([^\]]+)\]\]", line)
        if m:
            key = m.group(1).strip()
            n = key_to_num.get(key)
            if n is not None:
                # Replace [[key]] with [n]
                line = re.sub(r"\[\[[^\]]+\]\]", f"[{n}]", line, count=1)
        out_lines.append(line)
    return "\n".join(out_lines)


def main() -> None:
    if len(sys.argv) > 2:
        print("Usage: number_citations.py [LLM-to-IAS.adoc]", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) == 1 or sys.argv[1] == "-":
        text = sys.stdin.read()
    else:
        path = sys.argv[1]
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

    before, refs, after = split_sections(text)
    if not refs:
        # No references section; just passthrough
        sys.stdout.write(text)
        return

    ordered_keys, key_to_num = parse_reference_keys(refs)
    body_numbered = replace_citations(before, key_to_num)
    refs_numbered = renumber_references(refs, ordered_keys)

    sys.stdout.write(body_numbered)
    sys.stdout.write(refs_numbered)
    sys.stdout.write(after)


if __name__ == "__main__":
    main()
