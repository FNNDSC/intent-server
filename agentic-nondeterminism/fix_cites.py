#!/usr/bin/env python3
r"""
fix_cites.py

Post-process a LaTeX file to convert escaped citation commands produced by the
DocBook -> pandoc pipeline into real LaTeX citations that BibTeX can see.

Specifically replaces patterns like:
  \textbackslash cite{key}   or   \textbackslash\cite{key}
with:
  \cite{key}

Usage:
    fix_cites.py path/to/file.tex
"""

import pathlib
import re
import sys


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: fix_cites.py path/to/file.tex", file=sys.stderr)
        sys.exit(1)

    path = pathlib.Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    # Replace \textbackslash cite{...} and \textbackslash\cite{...}
    patterns = [
        # \textbackslash cite{...}  (braces may be escaped)
        re.compile(r"\\textbackslash\s+cite\\?\{([^}]+)\\?\}"),
        # \textbackslash\cite{...}
        re.compile(r"\\textbackslash\\cite\\?\{([^}]+)\\?\}"),
    ]
    for pat in patterns:
        text = pat.sub(r"\\cite{\1}", text)

    # Clean up any residual backslash before closing brace: \cite{...\\}
    text = re.sub(r"\\cite\{([^}]*)\\\}", r"\\cite{\1}", text)

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
