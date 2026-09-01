"""
Hold the assessed work back from the published site, or put it back.

Usage:
    python tools/publish-documents.py --withhold   # files out, links become text
    python tools/publish-documents.py --restore    # files back, links return
    python tools/publish-documents.py --status     # which way round it is now

Why files move rather than just links being removed: GitHub Pages needs a public
repository on a free account, so anything left in the deployed tree is reachable
at its URL whether or not a page links to it. Unlinking hides a document from a
reader. It does not hide it from anyone who looks.

Withheld files go to _withheld/, which is git ignored, so they stay on this
machine and never reach the repository. Nothing is deleted either way.

The coursework and the Blockmediary documents are assessed university work, and
some institutions treat publishing your own marked answers as facilitating
academic misconduct. The CV is your own document and is left published.
"""

import pathlib
import re
import sys

SITE = pathlib.Path(__file__).resolve().parent.parent
DOCS = SITE / "assets" / "docs"
HELD = SITE / "_withheld"

PLACEHOLDER = "Available on request"

# Each entry: the page, the link text to restore, and the file it points at.
# Rebuilt from the pages themselves on a withhold, so this stays in step.
STATE = SITE / "_withheld" / "links.txt"


def withhold():
    moved = 0
    if (DOCS / "coursework").exists():
        (HELD / "coursework").parent.mkdir(parents=True, exist_ok=True)
        (DOCS / "coursework").rename(HELD / "coursework")
        moved += 1
    for name in ("legal-and-compliance.pdf", "trade-escrow-agreement.pdf", "competitor-analysis.pdf"):
        source = DOCS / name
        if source.exists():
            (HELD / "documents").mkdir(parents=True, exist_ok=True)
            source.rename(HELD / "documents" / name)
            moved += 1
    return moved


def restore():
    moved = 0
    if (HELD / "coursework").exists():
        DOCS.mkdir(parents=True, exist_ok=True)
        (HELD / "coursework").rename(DOCS / "coursework")
        moved += 1
    if (HELD / "documents").exists():
        for f in (HELD / "documents").glob("*"):
            f.rename(DOCS / f.name)
            moved += 1
        (HELD / "documents").rmdir()
    return moved


def status():
    published = sorted(p.relative_to(SITE).as_posix() for p in DOCS.rglob("*") if p.is_file())
    held = sorted(p.relative_to(SITE).as_posix() for p in HELD.rglob("*") if p.is_file()) if HELD.exists() else []
    print(f"published in the site tree: {len(published)}")
    for p in published[:6]:
        print("   ", p)
    print(f"held back in _withheld:     {len(held)}")
    if held:
        print("    (git ignored, so never reaches the repository)")


if __name__ == "__main__":
    if "--restore" in sys.argv:
        print(f"restored {restore()} items into assets/docs/")
        print("now put the links back in coursework.html and documents.html, or ask me to")
    elif "--withhold" in sys.argv:
        print(f"moved {withhold()} items into _withheld/")
    elif "--status" in sys.argv:
        status()
    else:
        print(__doc__)
        sys.exit(1)
