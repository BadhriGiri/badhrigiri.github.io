# badhri-site

Personal site for Badhri Narayanan Giri. Plain HTML, one CSS file, one small JS file.
No build step, no dependencies, no tracking.

## Run it locally

Open `index.html` in a browser, or serve the folder:

```bash
cd C:/GitHub/badhri-site && python -m http.server 8123
```

## Structure

```
index.html                    Home: hero, selected work, how I work, background, toolkit, off the desk
work/blockmediary.html        The case study
coursework.html               Ten modules, every file individually linked
documents.html                The compliance documents
notes.html + notes/*.html     Writing
off-the-desk.html             Walking, cycling, the charity hike
assets/css/site.css           Every style, in numbered sections
assets/js/site.js             Theme toggle, mobile menu, scroll reveal
assets/docs/                  Compliance PDFs and your CV
assets/docs/coursework/       One folder per module, holding that module's files
assets/img/outdoors/          Photographs, one folder per walk
tools/gpx-to-map.py           Bakes a static route map from a GPX export
tools/gpx-to-svg.py           Route stats, and a plain trace with no basemap
_tile-cache/                  Downloaded map tiles, git ignored
tools/prepare-photos.py       Resizes photos, strips EXIF, builds thumbnails
tools/build-photos.py         Writes the photo markup to match the folders
tools/publish-documents.py    Holds the assessed work back, or puts it back
_withheld/                    Assessed work kept out of the repo, git ignored
_photo-originals/             Full resolution originals, git ignored, never deployed
```

Header and footer are copied into each page rather than shared, because there is no build step.
Change a nav link and you change it in all seven HTML files. Pages inside `work/` and `notes/`
use `../` prefixes; top level pages do not.

## The assessed work is currently held back

The coursework and the Blockmediary documents are **not** in the published site. They sit in
`_withheld/`, which is git ignored, so they stay on this machine and never reach the repository.
Both pages say "Available on request" instead.

This is waiting on the university confirming that publishing your own marked work is allowed.

```bash
python tools/publish-documents.py --status     # which way round it is
python tools/publish-documents.py --restore    # files back into the site
```

`--restore` moves the files; the links then need putting back in `coursework.html` and
`documents.html`, which I can do in one pass.

**Why the files move rather than the links just being removed.** GitHub Pages needs a public
repository on a free account, so anything left in the deployed tree is reachable at its URL whether
or not a page links to it. Unlinking hides a document from a reader; it does not hide it from
anyone who looks.

Once restored, every file lives at a stable path, so you can send one link to one document:

```
https://badhrigiri.github.io/assets/docs/coursework/beam046-financial-modelling/individual-report.pdf
```

Every link that leaves the page, whether to a hosted file or to an external site, carries
`target="_blank" rel="noopener"`, so the visitor never loses the page they were reading. `mailto:`
links are deliberately left alone, since opening a mail client in a new tab strands an empty one.
If you add a link by hand, follow the same rule.

To regenerate a notebook after editing it:

```bash
python -m nbconvert --to html --template lab --output-dir assets/docs/coursework/MODULE --output NAME path/to/notebook.ipynb
```

## Adding photographs

Drop the files into the matching folder under `assets/img/outdoors/`: `torquay-to-exeter`,
`ivybridge` or `newton-st-cyres`. There is a `README.txt` in there saying the same. Any filename
works; they appear in alphabetical order, so `01.jpg`, `02.jpg` and so on is the simplest way to
control the sequence. Then run both of these:

```bash
python tools/prepare-photos.py && python tools/build-photos.py
```

The first copies each original into `_photo-originals/` before touching anything, applies the EXIF
rotation flag so sideways photos come out upright, writes two sizes (1600px in place for the
lightbox and 1100px in `medium/` for the carousels), and strips all
EXIF on the way out. Phone photos can carry GPS coordinates and a public page is the wrong place
for them. Running it again is safe: it always works from the backed up original, so quality never
degrades.

The second writes the markup to match what is on disk: the slides, the strip, the counts, the image
dimensions and each carousel's shape. You do not edit the HTML for a photograph at all.

It only touches the photograph markup. Your prose, the stats, the map slides and the headings are
left alone, and running it twice with nothing changed produces an identical file.

**It keeps alt text you have written.** Only its own placeholder wording ("Photograph 3 of 8
from...") gets regenerated, so those counts stay honest as the folder grows. Replace them with real
descriptions when you can: that text is what a blind visitor hears and what shows when an image
fails to load, so describe the view rather than repeating the caption. The script prints how many
are still placeholders each time it runs.

Every photograph lives in a walk's carousel: the route map is the first slide and the photographs
follow it, with the arrows wrapping back round to the map. Clicking one opens it full size. It all
works without JavaScript too, where the slides simply stack down the page and each is a real link
to the full size photograph.

**You never need to strip metadata yourself.** `prepare-photos.py` removes all EXIF, GPS included,
on the way out. Put the file in the folder exactly as it came off the camera.

Three things worth knowing if you change the carousel CSS.

The slides are switched with `display`, not a cross fade. A stuck opacity transition leaves every
photograph after the first invisible.

Each carousel has one fixed shape, `--card-ratio` in the markup: the tallest slide it holds,
capped at four to three. Fixed, because a card that resized as you paged moved the arrows out from
under the cursor. Capped, because the tallest slide is a portrait photograph and letting it set the
height stranded the wider maps in a lot of empty space.

The map slide keeps the map's own shape (`--map-ratio`) and centres it, rather than stretching to
fill the card. The route is an SVG laid over the image, so if the image were letterboxed inside a
taller box the line would float off the map entirely.

The originals are git ignored, so they stay on your machine and never deploy. Do not delete
`_photo-originals/` unless you have the photos somewhere else.

## Adding a walk to Off the Desk

Export the activity from Strava as **GPX**, not FIT. On the activity page: the three dots menu,
then Export GPX. Then two steps:

```bash
python tools/gpx-to-svg.py path/to/activity.gpx     # distance, ascent, elapsed, date
python tools/gpx-to-map.py NAME path/to/activity.gpx   # the map image and route path
```

The map tool downloads the OpenStreetMap tiles it needs, stitches them, crops to the route, and
saves a JPEG into `assets/img/routes/`. The route is not drawn into the image: it comes back as an
SVG path in the image's coordinates, laid over the map in the page, so the line keeps the site's
accent colour and survives the dark mode inversion. Copy both into a new `.route--feature` block in
`off-the-desk.html`, following one of the three already there.

**Every map needs the OpenStreetMap attribution line under it.** That is a licence condition, not a
courtesy. Copy the `<p class="map-credit">` from an existing block.

Baking the maps here means a visitor's browser makes no request to any tile server, so the page
stays fast and the site keeps its promise not to phone anywhere home. Tiles are cached in
`_tile-cache/` so a rebuild costs nothing, and the tool spaces its requests out and sends a real
User-Agent, as the OSM usage policy asks.

The elevation figure ignores changes under four metres, because GPS altitude drifts constantly and
counting every wobble roughly doubles the reported ascent.

Do not commit the GPX files. They are a few megabytes each and contain exact coordinates.

## Before you publish

**Must fix**

1. **Alt text.** All 22 photographs carry a generic description, along the lines of "Photograph 3
   of 8 from the Torquay to Exeter charity walk". That is honest but not useful. A blind visitor
   hears the alt text, and it is what shows when an image fails to load, so each one wants a line
   describing the actual view. `build-photos.py` keeps anything you write by hand and prints how
   many are still placeholders.
2. **The charity walk** was for the Devon Wildlife Trust, not a cancer charity. That was my error
   earlier and it is corrected everywhere. The fundraising page is no longer live, so there is no
   link to add.
**Check before it goes live**

3. **Coursework publishing rules.** Waiting on the university. Nothing assessed is published until
   they answer, see the section above. The assignment briefs were never included either way, since
   those are Exeter's copyright rather than yours.
4. **BEAM047.** Fundamentals of Financial Management shows "Assessed by coursework" with no
   download. If a shareable submission turns up, drop it into `assets/docs/coursework/beam047-financial-management/`
   and swap the `<span class="file-none">` for a link.
5. **Compliance PDFs.** Held back with the coursework, for the same reason. The UCP 600 and
   Incoterms source PDFs were never copied in at all, because those are ICC copyright.
6. **Strava.** The link is live on three pages. Check your privacy zones first, since Strava can
   expose where you routinely start and finish.
7. **The note.** `notes/unregulated-is-not-an-opportunity.html` is built from the reasoning in
    your own report, but the sentences are mine. Rewrite it in your voice before it goes live.

**The published CV** at `assets/docs/CV.pdf` is the copy with your mobile number removed.

**Deliberately left out:** no photo of you, no teammate names, no individual module marks, no
student number, no tutor name, no visa detail, no full postcode.

**Em dashes:** none in any page I wrote. Two of the converted notebooks contain five between them.
Those are submitted work and stay untouched, by your decision and mine.

## Deploying

### GitHub Pages, free

```bash
cd C:/GitHub/badhri-site
git init
git add -A
git commit -m "Personal site"
git branch -M main
git remote add origin https://github.com/BadhriGiri/badhrigiri.github.io.git
git push -u origin main
```

Create the repo on GitHub first, named exactly `badhrigiri.github.io`. Live within a minute or two.
For a custom domain, add a file called `CNAME` containing just the domain and point its DNS at
GitHub Pages.

The site is about 12 MB with the coursework files, which is comfortably inside every limit.

### Vercel, free, easiest custom domain

Push to any GitHub repo, then import at vercel.com. Framework preset "Other", no build command,
output directory `.`.

## Editing notes

- Colours, fonts and spacing are custom properties at the top of `assets/css/site.css`. Change
  `--accent` and the whole site follows.
- Dark mode follows the system setting and can be overridden by the header toggle.
- `class="reveal"` fades a section in on scroll. Remove the class to disable it there.
- The site works with JavaScript off. The script adds the theme toggle, the mobile menu, the fade
  in and the carousels; without it the carousel slides simply stack down the page.
- Mobile is covered: the two column blocks fold to one below 900px, the nav becomes a menu below
  780px, and on touch screens the controls grow to 44px so they can actually be tapped. Checked at
  375px across all seven pages with no horizontal overflow.
