"""
Make QR codes for the site, and check they actually scan.

Usage:
    python tools/make-qr.py

Writes into qr/:
    badhri-qr.png        black on white, the one to use if in doubt
    badhri-qr-card.png   the same with the address printed underneath
    badhri-qr-brand.png  the site's green on its off white, for a slide
    badhri-qr.svg        vector, for print at any size

Rendered large enough that a phone showing it on screen displays it at native
resolution rather than upscaling and softening the edges. Error correction is
set high, so the code still reads if a corner is scuffed, partly covered or
printed small. Every file is decoded again after it is written
and the result compared to the URL, because a QR code that does not scan is
worse than no QR code: nobody tells you, they just walk away.

Needs:  python -m pip install segno opencv-python-headless pillow
"""

import pathlib
import sys

import cv2
import numpy as np
import segno
from PIL import Image, ImageDraw, ImageFont

SITE = pathlib.Path(__file__).resolve().parent.parent
OUT = SITE / "qr"
URL = "https://badhrigiri.github.io"

INK = "#000000"
PAPER = "#FFFFFF"
BRAND_INK = "#1F4B3F"      # the site's accent green
BRAND_PAPER = "#FBFAF7"    # the site's off white

# 28 puts the code around 1150px across, so a phone at 1080 to 1290px wide shows
# it without upscaling. Upscaled QR edges go soft, and soft edges cost scans.
SCALE = 28

MONO = "C:/Windows/Fonts/consola.ttf"
MONO_BOLD = "C:/Windows/Fonts/consolab.ttf"


def contrast_ratio(a, b):
    """WCAG contrast between two hex colours. Scanners want plenty of it."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def decodes_to(path, expected):
    """Read the file back with a real scanner and compare."""
    image = cv2.imread(str(path))
    if image is None:
        return False, "could not open the file"
    found, *_ = cv2.QRCodeDetector().detectAndDecode(image)
    if not found:
        return False, "no QR code detected"
    return found == expected, found


def card(qr_png, caption, ink, paper):
    """The QR with the address printed under it, so it is readable either way."""
    qr = Image.open(qr_png).convert("RGB")
    pad = 150
    strip = 250
    canvas = Image.new("RGB", (qr.width + pad * 2, qr.height + pad * 2 + strip), paper)
    canvas.paste(qr, (pad, pad))

    draw = ImageDraw.Draw(canvas)
    try:
        big = ImageFont.truetype(MONO_BOLD, 90)
        small = ImageFont.truetype(MONO, 56)
    except OSError:
        big = small = ImageFont.load_default()

    y = qr.height + pad + 40
    for text, font, gap in ((caption, big, 104), (URL.replace("https://", ""), small, 0)):
        w = draw.textbbox((0, 0), text, font=font)[2]
        draw.text(((canvas.width - w) / 2, y), text, font=font, fill=ink)
        y += gap
    return canvas


def main():
    OUT.mkdir(exist_ok=True)
    # error="h" is the highest of the four levels: about 30% of the code can be
    # lost and it still reads
    qr = segno.make(URL, error="h")
    results = []

    plain = OUT / "badhri-qr.png"
    qr.save(plain, scale=SCALE, border=4, dark=INK, light=PAPER)
    results.append(("badhri-qr.png", plain))

    brand = OUT / "badhri-qr-brand.png"
    qr.save(brand, scale=SCALE, border=4, dark=BRAND_INK, light=BRAND_PAPER)
    results.append(("badhri-qr-brand.png", brand))

    svg = OUT / "badhri-qr.svg"
    qr.save(svg, scale=SCALE, border=4, dark=INK, light=PAPER)

    card_path = OUT / "badhri-qr-card.png"
    card(plain, "Badhri Narayanan Giri", INK, PAPER).save(card_path, "PNG")
    results.append(("badhri-qr-card.png", card_path))

    print(f"encoded: {URL}")
    print(f"version {qr.version}, error correction {qr.error.upper()}\n")
    print(f"brand contrast: {contrast_ratio(BRAND_INK, BRAND_PAPER):.1f} to 1 "
          f"({'ample' if contrast_ratio(BRAND_INK, BRAND_PAPER) >= 7 else 'thin, use the plain one'})\n")

    ok = True
    for name, path in results:
        good, got = decodes_to(path, URL)
        size = path.stat().st_size / 1024
        print(f"  {'scans' if good else 'FAILED'}  {name:22s} {size:5.0f} KB  ->  {got}")
        ok = ok and good

    print(f"\nsvg written, not decodable as an image but the same data")
    if not ok:
        sys.exit("at least one code did not scan, do not use these")


if __name__ == "__main__":
    main()
