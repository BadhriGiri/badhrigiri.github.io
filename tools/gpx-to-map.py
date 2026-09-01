"""
Render a Strava GPX export as a static map image plus a matching SVG route path.

Usage:
    python tools/gpx-to-map.py NAME path/to/activity.gpx
    python tools/gpx-to-map.py --all

The map is baked once, here, and saved into assets/img/routes/. Nothing is
fetched when somebody visits the site: no tile server, no mapping library, no
third party request from the visitor's browser. That keeps the page fast and
keeps the site's promise that it does not phone anywhere home.

The route itself is NOT drawn into the image. It comes back as an SVG path in
the image's own pixel coordinates, to be laid over the map in the page. That way
the line uses the site's accent colour and stays correct when the map image is
inverted for dark mode.

Basemap tiles come from the standard OpenStreetMap tile server, which needs no
API key. They are colourful in the raw; the page desaturates them in CSS so they
sit quietly behind the route and can be inverted for dark mode. Attribution to
OpenStreetMap is required and appears under every map.

The tile server is a donated service. Tiles are cached in _tile-cache/ so a
rebuild costs nothing, and requests are spaced out and carry a real User-Agent,
as their usage policy asks.

Needs Pillow:  python -m pip install pillow
"""

import json
import math
import pathlib
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image

SITE = pathlib.Path(__file__).resolve().parent.parent
OUT = SITE / "assets" / "img" / "routes"
CACHE = SITE / "_tile-cache"

NS = {"g": "http://www.topografix.com/GPX/1/1"}

TILE = 256
RETINA = 1                      # the standard tile server offers no @2x tiles
TARGET_MIN, TARGET_MAX = 900, 1500   # wanted span of the route in CSS pixels
PAD = 0.07                      # breathing room around the route, as a fraction

# A point to point walk is long and thin. Left alone it produces a map far too
# tall to sit in a column beside text, so the box is widened to show more of the
# surrounding country instead.
MAX_PORTRAIT = 1.35             # height / width
MAX_LANDSCAPE = 2.0             # width / height

SIMPLIFY_PX = 0.7               # drop points closer than this to the drawn line
JPEG_QUALITY = 84
POLITE_DELAY = 0.15             # seconds between tile requests, to be a good guest

URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
UA = "badhri-site/1.0 static route maps for one personal portfolio (badhrinarayanan2005@gmail.com)"


def read_track(path):
    root = ET.parse(path).getroot()
    return [
        (float(p.get("lat")), float(p.get("lon")))
        for p in root.findall(".//g:trkpt", NS)
    ]


def project(lat, lon, zoom):
    """Web Mercator, in pixels at the given zoom."""
    n = TILE * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def pick_zoom(points):
    for zoom in range(18, 3, -1):
        xs, ys = zip(*(project(lat, lon, zoom) for lat, lon in points))
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        if span <= TARGET_MAX:
            if span >= TARGET_MIN or zoom == 4:
                return zoom
    return 12


def simplify(points, tolerance):
    """Ramer Douglas Peucker in pixel space, iterative to keep the stack shallow."""
    if len(points) < 3:
        return points

    def gap(point, start, end):
        (px, py), (x1, y1), (x2, y2) = point, start, end
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        worst, index = 0.0, None
        for i in range(first + 1, last):
            d = gap(points[i], points[first], points[last])
            if d > worst:
                worst, index = d, i
        if index is not None and worst > tolerance:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [p for p, k in zip(points, keep) if k]


def fetch_tile(zoom, tx, ty):
    name = f"{zoom}_{tx}_{ty}@{RETINA}x.png"
    cached = CACHE / name
    if cached.exists():
        return Image.open(cached).convert("RGB")

    url = URL.format(z=zoom, x=tx, y=ty)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    time.sleep(POLITE_DELAY)
    return Image.open(cached).convert("RGB")


def build(name, gpx_path):
    points = read_track(gpx_path)
    if len(points) < 2:
        raise SystemExit(f"{gpx_path}: not enough track points")

    zoom = pick_zoom(points)
    pixels = [project(lat, lon, zoom) for lat, lon in points]
    xs = [p[0] for p in pixels]
    ys = [p[1] for p in pixels]

    pad_x = max((max(xs) - min(xs)) * PAD, 30)
    pad_y = max((max(ys) - min(ys)) * PAD, 30)
    left, right = min(xs) - pad_x, max(xs) + pad_x
    top, bottom = min(ys) - pad_y, max(ys) + pad_y

    box_w, box_h = right - left, bottom - top
    if box_h / box_w > MAX_PORTRAIT:
        grow = (box_h / MAX_PORTRAIT - box_w) / 2
        left, right = left - grow, right + grow
    elif box_w / box_h > MAX_LANDSCAPE:
        grow = (box_w / MAX_LANDSCAPE - box_h) / 2
        top, bottom = top - grow, bottom + grow

    tile_x0, tile_x1 = int(left // TILE), int(right // TILE)
    tile_y0, tile_y1 = int(top // TILE), int(bottom // TILE)
    across = (tile_x1 - tile_x0 + 1) * TILE * RETINA
    down = (tile_y1 - tile_y0 + 1) * TILE * RETINA

    canvas = Image.new("RGB", (across, down), "#f4f2ee")
    count = 0
    for tx in range(tile_x0, tile_x1 + 1):
        for ty in range(tile_y0, tile_y1 + 1):
            try:
                tile = fetch_tile(zoom, tx, ty)
            except Exception as exc:                      # a gap is better than a crash
                print(f"    tile {zoom}/{tx}/{ty} failed: {exc}")
                continue
            canvas.paste(tile, ((tx - tile_x0) * TILE * RETINA, (ty - tile_y0) * TILE * RETINA))
            count += 1

    crop_left = (left - tile_x0 * TILE) * RETINA
    crop_top = (top - tile_y0 * TILE) * RETINA
    width = (right - left) * RETINA
    height = (bottom - top) * RETINA
    image = canvas.crop((
        round(crop_left), round(crop_top),
        round(crop_left + width), round(crop_top + height),
    ))

    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / f"{name}.jpg"
    image.save(destination, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

    # route path in the cropped image's own coordinate space, CSS pixels
    view_w = round(width / RETINA)
    view_h = round(height / RETINA)
    raw = [(x - left, y - top) for x, y in pixels]
    coords = [(round(x, 1), round(y, 1)) for x, y in simplify(raw, SIMPLIFY_PX)]
    path = "M" + " L".join(f"{x} {y}" for x, y in coords)

    print(f"  {name}: zoom {zoom}, {count} tiles, {view_w}x{view_h}, "
          f"{destination.stat().st_size / 1024:.0f} KB, {len(coords)} drawn points")

    return {
        "name": name,
        "image": f"assets/img/routes/{name}.jpg",
        "view_w": view_w,
        "view_h": view_h,
        "path": path,
        "start": coords[0],
        "end": coords[-1],
    }


ROUTES = {
    "torquay-to-exeter": r"C:\Users\beast\Downloads\Torquay_to_Exeter.gpx",
    "ivybridge": r"C:\Users\beast\Downloads\Ivybridge_Hike.gpx",
    "newton-st-cyres": r"C:\Users\beast\Downloads\Newton_St_Cyres_to_Crediton.gpx",
}

if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--all"]:
        jobs = list(ROUTES.items())
    elif len(args) == 2:
        jobs = [(args[0], args[1])]
    else:
        print(__doc__)
        sys.exit(1)

    print("building static maps")
    records = [build(name, path) for name, path in jobs]
    print(json.dumps(records, indent=2))
