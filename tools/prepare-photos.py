"""
Prepare photographs for the Off the Desk page.

Usage:
    python tools/prepare-photos.py

Straight off a phone, these files are around 37 megapixels and 10 MB each. Nobody
is going to wait for that. This script:

  1. Copies every original into _photo-originals/ (git ignored) before touching it,
     so nothing is ever destroyed.
  2. Applies the EXIF rotation flag, so photos taken sideways are saved upright
     rather than relying on the browser to work it out.
  3. Writes two sizes: 1600px in place for the lightbox and 1100px into medium/
     for the carousels.
  4. Strips all EXIF on the way out. Phone photos can carry GPS coordinates, and
     a public page is the wrong place for them.

Safe to run again: it always works from _photo-originals/ when a backup exists,
so quality never degrades through repeated passes.

Needs Pillow:  python -m pip install pillow
"""

import pathlib
import shutil
import sys

from PIL import Image, ImageOps

SITE = pathlib.Path(__file__).resolve().parent.parent
PHOTOS = SITE / "assets" / "img" / "outdoors"
BACKUP = SITE / "_photo-originals"

FULL_EDGE = 1600
MEDIUM_EDGE = 1100
FULL_QUALITY = 82
MEDIUM_QUALITY = 80


def save(image, destination, long_edge, quality):
    out = image.copy()
    out.thumbnail((long_edge, long_edge), Image.LANCZOS)
    if out.mode not in ("RGB", "L"):
        out = out.convert("RGB")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # exif is not passed on, so nothing from the camera survives into the file
    out.save(destination, "JPEG", quality=quality, optimize=True, progressive=True)
    return out.size, destination.stat().st_size


def main():
    if not PHOTOS.exists():
        sys.exit(f"no photo folder at {PHOTOS}")

    total_before = total_after = 0
    for group in sorted(p for p in PHOTOS.iterdir() if p.is_dir() and p.name != "medium"):
        originals = sorted(group.glob("*.jpg"))
        if not originals:
            continue
        print(f"\n{group.name}")
        for photo in originals:
            backup = BACKUP / group.name / photo.name
            if backup.exists():
                source = backup           # already backed up, work from the original
            else:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(photo, backup)
                source = backup

            before = photo.stat().st_size
            with Image.open(source) as im:
                im = ImageOps.exif_transpose(im)     # honour the rotation flag
                full_size, full_bytes = save(im, photo, FULL_EDGE, FULL_QUALITY)
                mid_size, mid_bytes = save(im, group / "medium" / photo.name, MEDIUM_EDGE, MEDIUM_QUALITY)

            total_before += before
            total_after += full_bytes + mid_bytes
            print(
                f"  {photo.name}  {before / 1048576:5.1f} MB  ->  "
                f"full {full_size[0]}x{full_size[1]} {full_bytes / 1024:4.0f} KB  "
                f"medium {mid_bytes / 1024:4.0f} KB"
            )

    print(
        f"\ntotal {total_before / 1048576:.0f} MB -> {total_after / 1048576:.1f} MB "
        f"({total_after / total_before * 100:.1f}% of the original)"
    )
    print(f"originals kept in {BACKUP}")


if __name__ == "__main__":
    main()
