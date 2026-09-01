"""
Rebuild the photograph markup in off-the-desk.html from whatever is on disk.

Usage:
    python tools/prepare-photos.py     # resize, rotate, strip EXIF, make thumbs
    python tools/build-photos.py       # write the markup to match

Add a photograph to a folder under assets/img/outdoors/, run those two, done.
No hand editing of HTML, no counts to keep in step, no dimensions to look up.

What it rewrites, and only this:
  * the photograph slides inside each walk's carousel, after the map slide
  * each carousel's --card-ratio, which has to be the tallest slide it holds

Everything else in the page is left exactly as it is. The prose, the stats, the
map slides and the section headings are all yours.

Alt text: a description you have written by hand is kept. Only the placeholder
wording this script generates gets regenerated, so the counts inside it stay
honest as you add photographs. Write real descriptions whenever you can, they
are what a blind visitor hears and what shows when an image fails to load.

Needs Pillow:  python -m pip install pillow
"""

import pathlib
import re
import sys
from fractions import Fraction

from PIL import Image

SITE = pathlib.Path(__file__).resolve().parent.parent
PHOTOS = SITE / "assets" / "img" / "outdoors"
ROUTES = SITE / "assets" / "img" / "routes"
PAGE = SITE / "off-the-desk.html"

# tallest a carousel is allowed to be, height over width. The tallest slide is
# always a portrait photograph, and letting it set the height strands the wider
# maps in a great deal of empty space.
CARD_CAP = Fraction(4, 3)

WALKS = [
    ("torquay-to-exeter", "Torquay to Exeter", "the Torquay to Exeter charity walk"),
    ("newton-st-cyres", "Newton St Cyres to Crediton", "the Newton St Cyres to Crediton walk"),
    ("ivybridge", "Ivybridge", "the Ivybridge walk on Dartmoor"),
]
# alt text this script wrote itself, as opposed to something a human typed
PLACEHOLDER_ALT = re.compile(r"^Photograph \d+ of \d+ from .+$")


def shots(slug):
    return sorted(p for p in (PHOTOS / slug).glob("*.jpg"))


def size_of(path):
    with Image.open(path) as im:
        return im.size


def existing_alts(page_text):
    """Map every image src in the page to the alt text it currently carries."""
    found = {}
    for tag in re.findall(r"<img\b[^>]*>", page_text, re.S):
        src = re.search(r'src="([^"]+)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag, re.S)
        if src and alt:
            found[src.group(1)] = " ".join(alt.group(1).split())
    return found


def alt_for(src, index, total, context, kept):
    """Keep a hand written description; regenerate the placeholder wording."""
    current = kept.get(src)
    if current and not PLACEHOLDER_ALT.match(current):
        return current
    return f"Photograph {index} of {total} from {context}"


def plural(n):
    return "1 photograph" if n == 1 else f"{n} photographs"


def card_ratio(slug):
    """Widest over tallest for the carousel: the tallest slide, capped."""
    sizes = [size_of(ROUTES / f"{slug}.jpg")]
    sizes += [size_of(PHOTOS / slug / "medium" / s.name) for s in shots(slug)]
    tallest = max(Fraction(h, w) for w, h in sizes)
    used = min(tallest, CARD_CAP)
    return used.denominator, used.numerator


def build_walk(page_text, slug, title, context, kept):
    files = shots(slug)
    total = len(files)

    slides = []
    for i, shot in enumerate(files, 1):
        src = f"assets/img/outdoors/{slug}/medium/{shot.name}"
        w, h = size_of(PHOTOS / slug / "medium" / shot.name)
        alt = alt_for(src, i, total, context, kept)
        slides.append(
            f'''          <div class="carousel-slide">
            <a href="assets/img/outdoors/{slug}/{shot.name}" data-group="{title}">
              <img src="{src}" alt="{alt}"
                   width="{w}" height="{h}" loading="lazy" decoding="async">
            </a>
          </div>'''
        )

    body = "\n" + f"          <!-- photos:{slug} -->\n"
    body += ("\n".join(slides) + "\n") if slides else ""
    body += "          <!-- /photos -->\n"

    # locate this walk's carousel, then the span between the map slide and the arrows
    at = page_text.index(f"assets/img/routes/{slug}.jpg")
    open_tag = page_text.rindex('<div class="route-carousel"', 0, at)
    tag_end = page_text.index(">", open_tag) + 1
    nav_at = page_text.index('<div class="stack-nav">', tag_end)

    marker = f"<!-- photos:{slug} -->"
    if marker in page_text:
        start = page_text.rindex("\n", 0, page_text.index(marker, tag_end))
    else:
        first_photo = page_text.find('<div class="carousel-slide">', tag_end, nav_at)
        start = page_text.rindex("\n", 0, first_photo if first_photo != -1 else nav_at)
    end = page_text.rindex("\n", 0, nav_at) + 1

    page_text = page_text[:start] + body + " " * 10 + page_text[end + 10:]

    # the card has to be shaped for the tallest thing it now holds
    cw, ch = card_ratio(slug)
    mw, mh = size_of(ROUTES / f"{slug}.jpg")
    open_tag = page_text.rindex('<div class="route-carousel"', 0, page_text.index(f"assets/img/routes/{slug}.jpg"))
    tag_end = page_text.index(">", open_tag) + 1
    page_text = (
        page_text[:open_tag]
        + f'<div class="route-carousel" style="--card-ratio: {cw} / {ch}; --map-ratio: {mw} / {mh}">'
        + page_text[tag_end:]
    )

    print(f"  {slug}: {plural(total)}, card {cw}/{ch}")
    return page_text


def main():
    if not PAGE.exists():
        sys.exit(f"no page at {PAGE}")

    text = PAGE.read_text(encoding="utf-8")
    kept = existing_alts(text)

    print("rebuilding photograph markup")
    for slug, title, context in WALKS:
        text = build_walk(text, slug, title, context, kept)

    # The newline argument is deliberate. Letting Windows translate on the way
    # out rewrites every line in the file, and a diff where everything changed
    # tells you nothing about what actually moved.
    PAGE.write_text(text, encoding="utf-8", newline="\n")

    # say plainly what the page now holds, so a bad run is obvious
    check = PAGE.read_text(encoding="utf-8")
    print(
        f"\nwritten: {check.count('carousel-slide ')} map slides, "
        f"{check.count('<div class=\"carousel-slide\">')} photograph slides"
    )
    # only photographs, not the maps, which carry their own permanent description
    photo_alts = {
        src: alt for src, alt in existing_alts(check).items()
        if "assets/img/outdoors/" in src
    }
    written = sum(1 for a in photo_alts.values() if a and not PLACEHOLDER_ALT.match(a))
    print(
        f"photograph alt text: {written} written by hand and kept, "
        f"{len(photo_alts) - written} still placeholder"
    )


if __name__ == "__main__":
    main()
