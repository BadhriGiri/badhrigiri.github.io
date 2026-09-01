"""
Turn Strava GPX exports into route data for the Off the Desk page.

Usage:
    python tools/gpx-to-svg.py path/to/one.gpx path/to/another.gpx

For each file it prints the distance, elevation gain, elapsed time, date and a
ready to paste SVG path. Nothing is written to disk, so you can check the output
before it goes anywhere near the site.

Why an SVG path rather than the GPX itself: a normalised path carries no
latitude or longitude, so publishing it reveals nothing about where you were.
It is also about a thousand times smaller than the source file and needs no
mapping library.

Only the standard library is used.
"""

import datetime
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

NS = {"g": "http://www.topografix.com/GPX/1/1"}

# Elevation from a phone or a watch drifts by a metre or two constantly. Counting
# every rise inflates the total badly, so only a sustained climb above this many
# metres is counted.
ELEVATION_NOISE_FLOOR_M = 4.0

# How far a point may sit from the simplified line before it has to be kept,
# expressed as a fraction of the route's own bounding box. Relative rather than
# absolute, so a 9 km walk keeps the same level of detail as a 47 km one.
# Larger means a smaller path and a coarser trace.
SIMPLIFY_RELATIVE = 0.0016

VIEW_W = 1000.0
PADDING = 24.0

# Widest the drawing box is allowed to get in either direction, so a long thin
# route still produces a card that sits sensibly beside a column of text.
MAX_ASPECT = 1.6


def haversine_m(a, b):
    """Great circle distance in metres between two (lat, lon) pairs."""
    radius = 6371000.0
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat = lat2 - lat1
    dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def read_points(path):
    root = ET.parse(path).getroot()
    name_el = root.find(".//g:trk/g:name", NS)
    points = []
    for pt in root.findall(".//g:trkpt", NS):
        ele = pt.find("g:ele", NS)
        tm = pt.find("g:time", NS)
        points.append(
            (
                float(pt.get("lat")),
                float(pt.get("lon")),
                float(ele.text) if ele is not None else None,
                tm.text if tm is not None else None,
            )
        )
    return (name_el.text if name_el is not None else os.path.basename(path)), points


def elevation_gain_m(elevations):
    """Total ascent, ignoring drift below the noise floor."""
    if not elevations:
        return 0.0
    gain = 0.0
    reference = elevations[0]
    for value in elevations[1:]:
        change = value - reference
        if change >= ELEVATION_NOISE_FLOOR_M:
            gain += change
            reference = value
        elif change <= -ELEVATION_NOISE_FLOOR_M:
            reference = value
    return gain


def perpendicular_distance(point, start, end):
    (px, py), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def simplify(points, tolerance):
    """Ramer Douglas Peucker, iterative so a long track cannot blow the stack."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        worst_dist, worst_index = 0.0, None
        for i in range(first + 1, last):
            d = perpendicular_distance(points[i], points[first], points[last])
            if d > worst_dist:
                worst_dist, worst_index = d, i
        if worst_index is not None and worst_dist > tolerance:
            keep[worst_index] = True
            stack.append((first, worst_index))
            stack.append((worst_index, last))
    return [p for p, k in zip(points, keep) if k]


def to_svg_path(points):
    """Project to a plain rectangle, normalise, and return (path_d, view_w, view_h)."""
    mean_lat = sum(p[0] for p in points) / len(points)
    scale_lon = math.cos(math.radians(mean_lat))

    # y is negated because latitude grows north while SVG y grows down
    projected = [(p[1] * scale_lon, -p[0]) for p in points]

    span_x = max(p[0] for p in projected) - min(p[0] for p in projected)
    span_y = max(p[1] for p in projected) - min(p[1] for p in projected)
    if span_x <= 0 and span_y <= 0:
        return "", 100.0, 100.0

    projected = simplify(projected, max(span_x, span_y) * SIMPLIFY_RELATIVE)

    xs = [p[0] for p in projected]
    ys = [p[1] for p in projected]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)

    # Scale so the longer axis fills the box, then let the viewBox hug the route
    # rather than forcing a square. A point to point walk is long and thin, and a
    # square box would leave most of the card empty.
    inner = VIEW_W - 2 * PADDING
    scale = inner / max(span_x, span_y)
    drawn_w, drawn_h = span_x * scale, span_y * scale

    view_w = drawn_w + 2 * PADDING
    view_h = drawn_h + 2 * PADDING

    # A very thin route still needs a card that lays out sensibly next to text,
    # so widen whichever side is too narrow until the box is inside the limit.
    if view_w / view_h < 1 / MAX_ASPECT:
        view_w = view_h / MAX_ASPECT
    elif view_w / view_h > MAX_ASPECT:
        view_h = view_w / MAX_ASPECT

    offset_x = (view_w - drawn_w) / 2
    offset_y = (view_h - drawn_h) / 2

    coords = [
        (round((x - min(xs)) * scale + offset_x, 1), round((y - min(ys)) * scale + offset_y, 1))
        for x, y in projected
    ]
    d = "M" + " L".join(f"{x} {y}" for x, y in coords)
    return d, round(view_w), round(view_h)


def describe(path):
    name, points = read_points(path)
    if len(points) < 2:
        print(f"{path}: not enough track points")
        return

    distance_m = sum(haversine_m(points[i - 1][:2], points[i][:2]) for i in range(1, len(points)))
    elevations = [p[2] for p in points if p[2] is not None]
    gain = elevation_gain_m(elevations)

    stamps = [p[3] for p in points if p[3]]
    started = elapsed = None
    if len(stamps) > 1:
        started = datetime.datetime.fromisoformat(stamps[0].replace("Z", "+00:00"))
        ended = datetime.datetime.fromisoformat(stamps[-1].replace("Z", "+00:00"))
        elapsed = ended - started

    d, view_w, view_h = to_svg_path([(p[0], p[1]) for p in points])

    print(f"=== {os.path.basename(path)}")
    print(f"    name      {name}")
    print(f"    distance  {distance_m / 1000:.1f} km")
    print(f"    ascent    {gain:.0f} m  (raw points: {len(points)}, drawn: {d.count('L') + 1})")
    if started:
        print(f"    date      {started:%-d %B %Y}" if os.name != "nt" else f"    date      {started.day} {started:%B %Y}")
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        print(f"    elapsed   {hours}h {remainder // 60:02d}m")
    print(f'    <svg viewBox="0 0 {view_w} {view_h}">')
    print(f'      <path d="{d}" />')
    print("    </svg>")
    print()


def as_record(path):
    """The same numbers as describe(), returned as a dict for scripting."""
    name, points = read_points(path)
    distance_m = sum(haversine_m(points[i - 1][:2], points[i][:2]) for i in range(1, len(points)))
    elevations = [p[2] for p in points if p[2] is not None]
    stamps = [p[3] for p in points if p[3]]
    started = datetime.datetime.fromisoformat(stamps[0].replace("Z", "+00:00")) if stamps else None
    ended = datetime.datetime.fromisoformat(stamps[-1].replace("Z", "+00:00")) if len(stamps) > 1 else None
    d, view_w, view_h = to_svg_path([(p[0], p[1]) for p in points])
    return {
        "file": os.path.basename(path),
        "name": name,
        "km": round(distance_m / 1000, 1),
        "ascent_m": round(elevation_gain_m(elevations)),
        "date": started.strftime("%Y-%m-%d") if started else None,
        "seconds": int((ended - started).total_seconds()) if ended else None,
        "path": d,
        "view_w": view_w,
        "view_h": view_h,
    }


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--json"]
    if not args:
        print(__doc__)
        sys.exit(1)
    if "--json" in sys.argv:
        print(json.dumps([as_record(a) for a in args], indent=2))
    else:
        for arg in args:
            describe(arg)
