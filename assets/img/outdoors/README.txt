Photographs for the Off the Desk page.

One folder per walk:

  torquay-to-exeter\   The Devon Wildlife Trust charity walk, 6 June 2026
  ivybridge\           Dartmoor, 25 April 2026
  newton-st-cyres\     Newton St Cyres to Crediton, 30 May 2026

Drop the files in. Any names work; they appear in alphabetical order, so 01.jpg,
02.jpg and so on is the simplest way to control the sequence. Then run, from the
site folder:

  python tools/prepare-photos.py && python tools/build-photos.py

That is the whole job. The first command resizes each photo, turns it upright if
the camera recorded it sideways, builds the two smaller versions the page needs,
and strips the EXIF metadata including any GPS coordinates. You do not need to
clean anything off a photo before putting it here. The second writes the markup,
so there is no HTML to edit and no counts to keep in step.

The thumb\ and medium\ folders are generated. Leave them alone.

Originals are copied to _photo-originals\ before anything is touched, so nothing
is ever lost.
