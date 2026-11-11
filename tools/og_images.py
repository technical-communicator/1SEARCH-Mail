"""Make the 1200x630 "share images" used in link previews (og:image).

When someone shares a link on Instagram, iMessage, Facebook, X or Slack,
the preview shows a picture. Those apps want it 1200 pixels wide and 630
tall. This file makes three kinds:

  default_image()  the site-wide picture (images/og/default.jpg)
  post_image()     a blog post's cover, cropped to 1200x630
  event_image()    a card for one event: category colour, title, date, venue

Images are only rewritten when they actually change, so git doesn't see
"new" files on every build. Fonts are in tools/fonts (Anton and
Courier Prime, both free under the SIL Open Font License).

This file is a helper: tools/build_site.py uses it.
"""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OG_DIR = ROOT / "images" / "og"
SIZE = (1200, 630)

# The same colours as style.css.
RED = "#8a0f26"
PAPER = "#f6f1e7"
INK = "#1a1a1a"
CATEGORY_COLOURS = {
    "Music": "#4f4c7a", "Art": "#8a0f26", "Markets": "#2e6b3a",
    "Food and Drink": "#a84300", "Film": "#1f4e8c", "Comedy": "#b0245e",
    "Community": "#00707a", "Workshops": "#6b4e16",
}


def font(name, size):
    files = {"anton": "Anton-Regular.woff", "courier": "CourierPrime-Bold.woff"}
    return ImageFont.truetype(str(FONTS / files[name]), size)


def save(image, path):
    """Save as JPEG, but only if it's different from what's already there."""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "JPEG", quality=86, optimize=True, progressive=True)
    data = buffer.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def halftone(draw, colour, box, step=22, radius=3):
    """A field of small dots, the site's halftone accent."""
    x0, y0, x1, y1 = box
    for row, y in enumerate(range(y0, y1, step)):
        offset = step // 2 if row % 2 else 0
        for x in range(x0 + offset, x1, step):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour)


def paste_fit(canvas, image_path, box):
    """Paste an image (keeping its transparency) scaled to fit inside box."""
    art = Image.open(image_path).convert("RGBA")
    x0, y0, x1, y1 = box
    scale = min((x1 - x0) / art.width, (y1 - y0) / art.height)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    canvas.paste(art, (x0 + ((x1 - x0) - art.width) // 2, y0 + ((y1 - y0) - art.height) // 2), art)


def wrap(draw, text, face, width):
    """Split text into lines that fit `width` pixels."""
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=face) <= width or not line:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def default_image():
    """images/og/default.jpg: the cherry red site card with the mascot."""
    canvas = Image.new("RGB", SIZE, RED)
    draw = ImageDraw.Draw(canvas)
    halftone(draw, "#7a0c21", (0, 0, 1200, 630))
    paste_fit(canvas, ROOT / "images" / "mascot-head-color-large.webp", (70, 85, 470, 545))
    paste_fit(canvas, ROOT / "images" / "wordmark-white.webp", (520, 150, 1130, 360))
    small = font("courier", 30)
    draw.text((535, 400), "Orlando arts, culture and events", font=small, fill="white")
    draw.text((535, 448), "+ a snail mail club", font=small, fill="white")
    draw.text((535, 520), "searchcentralfl.com", font=font("courier", 26), fill="#f3c6cf")
    path = OG_DIR / "default.jpg"
    save(canvas, path)
    return path


def post_image(cover, slug):
    """A blog post's cover, cropped to fill 1200x630, with a slim name band."""
    art = Image.open(ROOT / cover).convert("RGB")
    scale = max(SIZE[0] / art.width, SIZE[1] / art.height)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    left, top = (art.width - SIZE[0]) // 2, (art.height - SIZE[1]) // 2
    canvas = art.crop((left, top, left + SIZE[0], top + SIZE[1]))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 570, 1200, 630), fill=RED)
    draw.text((32, 583), "SEARCH Central Florida  /  blog", font=font("courier", 28), fill="white")
    path = OG_DIR / "blog" / f"{slug}.jpg"
    save(canvas, path)
    return path


def event_image(event, slug, nice_when):
    """A share card for one event: colour band, title, date and venue.
    nice_when is the date and time as text, e.g. "Sat, Nov 14 · 8:00 PM"."""
    colour = CATEGORY_COLOURS.get(event.get("category"), "#5c5c5c")
    canvas = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(canvas)

    # Top: the category colour with halftone dots, like the event cards.
    draw.rectangle((0, 0, 1200, 400), fill=colour)
    halftone(draw, _darker(colour), (0, 0, 1200, 400))
    draw.text((60, 46), event.get("category", "").upper(), font=font("courier", 30), fill="white")

    # The title, as big as fits in up to three lines.
    for size in (96, 84, 72, 62, 54):
        face = font("anton", size)
        lines = wrap(draw, event["title"].upper(), face, 860)
        if len(lines) <= 3:
            break
    lines = lines[:3]
    y = 380 - len(lines) * int(size * 1.12)
    for line in lines:
        draw.text((60, y), line, font=face, fill="white")
        y += int(size * 1.12)

    # Bottom: when and where, in the typewriter font.
    draw.text((60, 430), nice_when, font=font("courier", 40), fill=INK)
    venue = event.get("venue", "")
    venue_lines = wrap(draw, venue, font("courier", 32), 860)[:2]
    for i, line in enumerate(venue_lines):
        draw.text((60, 490 + i * 40), line, font=font("courier", 32), fill="#444444")
    draw.text((60, 580), "searchcentralfl.com", font=font("courier", 24), fill=colour)

    paste_fit(canvas, ROOT / "images" / "mascot-head-color-large.webp", (950, 300, 1170, 600))
    path = OG_DIR / "events" / f"{slug}.jpg"
    save(canvas, path)
    return path


def _darker(hex_colour, amount=0.85):
    """The same colour a little darker, for the halftone dots."""
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return (int(r * amount), int(g * amount), int(b * amount))
