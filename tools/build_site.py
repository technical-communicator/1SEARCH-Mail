#!/usr/bin/env python3
"""Build the whole site: one command, run after any content change.

    python3 tools/build_site.py

(Needs: pip install markdown pyyaml pillow)

What it does, in order:
  1. Builds the blog (tools/build_blog.py): post pages, blog.html, series pages.
  2. Builds one page per event at events/<name>-<date>/ so search engines
     can read every event without running JavaScript, plus an "all events"
     page at events/. Past events keep their pages (they never 404); the
     page just says the event has passed.
  3. Writes a plain list of upcoming events into events.html, for search
     engines (the calendar script replaces it for visitors).
  4. Writes the SEO tags into the <head> of the hand-written pages
     (index, events, mailclub, about, submit, admin) from seo/pages.json.
  5. Checks every page: a title and description on each, no two pages with
     the same title, one <h1>, alt text on images, lang="en".
     Problems that matter stop the build; smaller ones print a warning.
  6. Writes sitemap.xml, robots.txt and the IndexNow key file, and prints
     the pages that changed (tools/indexnow.py tells Bing about them).

Events come from events.json. Every event gets a "slug" (its web address
name, like "mex-market-2026-11-09"); the script adds it to events.json the
first time. Every event ever listed is also kept in data/events-archive.json,
so its page stays up after it's removed from events.json.

Approved submissions from Supabase only exist in the database, so they
show on the calendar but don't get their own page. To give one a page,
copy it into events.json and run this script.
"""

import datetime
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_blog                                    # noqa: E402
import og_images                                     # noqa: E402
import seo                                           # noqa: E402
from seo import esc                                  # noqa: E402

ROOT = seo.ROOT
EVENTS_FILE = ROOT / "events.json"
ARCHIVE_FILE = ROOT / "data" / "events-archive.json"
EVENTS_DIR = ROOT / "events"
PAGES_FILE = ROOT / "seo" / "pages.json"
EASTERN = ZoneInfo("America/New_York")
TODAY = seo.today_in_orlando()

SEO_START = "<!-- SEO:START"
SEO_END = "<!-- SEO:END -->"
LIST_START = "<!-- EVENTS-LIST:START"
LIST_END = "<!-- EVENTS-LIST:END -->"


# ---------------------------------------------------------------------------
# Dates, times and names
# ---------------------------------------------------------------------------

def slugify(text):
    """'OTR: Open Stage Fight Night' -> 'otr-open-stage-fight-night'"""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "event"


def nice_time(hhmm):
    """'19:30' -> '7:30 PM' (the same as formatTime() in events-common.js)."""
    hours, minutes = (int(n) for n in hhmm.split(":"))
    return f"{hours % 12 or 12}:{minutes:02d} {'PM' if hours >= 12 else 'AM'}"


def short_time(hhmm):
    """'19:00' -> '7 PM', '19:30' -> '7:30 PM' (for titles and descriptions)."""
    return nice_time(hhmm).replace(":00 ", " ")


def event_date(event):
    return datetime.date.fromisoformat(event["date"])


def long_date(day):
    """Saturday, November 14, 2026"""
    return f"{day:%A}, {day:%B} {day.day}, {day.year}"


def short_date(day):
    """Sat, Nov 14"""
    return f"{day:%a}, {day:%b} {day.day}"


def start_and_end(event):
    """The start and end as full date-times with the Orlando offset, e.g.
    2026-11-14T20:00:00-05:00 (-04:00 in summer). An end time earlier than
    the start (like a party until 2 AM) is on the next day."""
    day = event_date(event)

    def at(hhmm, on):
        hours, minutes = (int(n) for n in hhmm.split(":"))
        return datetime.datetime(on.year, on.month, on.day, hours, minutes, tzinfo=EASTERN)

    start = at(event["start_time"], day)
    end = None
    if event.get("end_time"):
        end = at(event["end_time"], day)
        if end <= start:
            end = at(event["end_time"], day + datetime.timedelta(days=1))
    return start, end


def postal_address(address):
    """'2240 W Fairbanks Ave, Winter Park, FL 32789' -> a schema.org PostalAddress."""
    parts = [p.strip() for p in str(address or "").split(",") if p.strip()]
    result = {"@type": "PostalAddress", "addressCountry": "US"}
    if parts:
        match = re.match(r"^([A-Z]{2})(?:\s+(\d{5}))?$", parts[-1])
        if match:
            result["addressRegion"] = match.group(1)
            if match.group(2):
                result["postalCode"] = match.group(2)
            parts.pop()
    if parts:
        result["addressLocality"] = parts.pop()
    if parts:
        result["streetAddress"] = ", ".join(parts)
    return result


def link_label(url):
    """The same labels as linkLabel() in events-common.js."""
    if "instagram.com" in url:
        return "Instagram"
    if "eventbrite." in url or "ticket" in url:
        return "Tickets"
    return "Website"


# ---------------------------------------------------------------------------
# Events: slugs and the archive
# ---------------------------------------------------------------------------

def load_events():
    """Read events.json and the archive, give every event a slug, and keep
    the archive up to date. Returns every event ever listed, by slug."""
    events = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    archive = {}
    if ARCHIVE_FILE.exists():
        archive = {e["slug"]: e for e in json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))}

    for field in ("title", "date", "start_time", "venue", "category", "description"):
        for event in events:
            if not event.get(field):
                sys.exit(f"events.json: '{event.get('title', '?')}' is missing '{field}'")

    # Give each new event a slug, making sure no two events share one.
    taken = {e["slug"] for e in events if e.get("slug")}
    changed = False
    for event in events:
        if event.get("slug"):
            continue
        base = f"{slugify(event['title'])}-{event['date']}"
        slug, n = base, 2
        while slug in taken or (slug in archive and
                                (archive[slug]["title"], archive[slug]["date"]) != (event["title"], event["date"])):
            slug, n = f"{base}-{n}", n + 1
        taken.add(slug)
        # Put the slug right after the title, so events.json stays easy to read.
        rebuilt = {}
        for key, value in event.items():
            rebuilt[key] = value
            if key == "title":
                rebuilt["slug"] = slug
        event.clear()
        event.update(rebuilt)
        changed = True

    if changed:
        EVENTS_FILE.write_text(json.dumps(events, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("added slugs to events.json")

    # Events in events.json are the latest version; the archive keeps the rest.
    for event in events:
        archive[event["slug"]] = event
    ARCHIVE_FILE.parent.mkdir(exist_ok=True)
    ordered = sorted(archive.values(), key=lambda e: (e["date"], e["start_time"], e["title"]))
    ARCHIVE_FILE.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ordered


# ---------------------------------------------------------------------------
# Event pages
# ---------------------------------------------------------------------------

def event_title(event):
    """'Mex Market, Nov 9 | Search Central Florida', kept to 60 characters.
    A long name drops the date; a very long one is shortened."""
    day = event_date(event)
    room = seo.TITLE_MAX - len(seo.SITE["title_suffix"])
    with_date = f"{event['title']}, {day:%b} {day.day}"
    if len(with_date) <= room:
        return seo.full_title(with_date)
    return seo.full_title(seo.shorten(event["title"], room))


def event_description(event):
    """Made from the event's details, e.g. 'Sat, Nov 14, 8 PM at Anthem
    Orlando. Anthem's alternative drag night...' (155 characters at most)."""
    day = event_date(event)
    text = f"{short_date(day)}, {short_time(event['start_time'])} at {event['venue']}. {event['description']}"
    return seo.shorten(text, seo.DESCRIPTION_MAX)


def event_json_ld(event, url, image):
    """Event structured data, so Google can show it as an event. Music
    events use the more specific MusicEvent type."""
    start, end = start_and_end(event)
    data = {
        "@context": "https://schema.org",
        "@type": "MusicEvent" if event["category"] == "Music" else "Event",
        "name": event["title"],
        "description": event.get("long_description") or event["description"],
        "startDate": start.isoformat(),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {
            "@type": "Place",
            "name": event["venue"],
            "address": postal_address(event.get("address")),
        },
        "image": [seo.absolute(image)],
        "url": url,
    }
    if end:
        data["endDate"] = end.isoformat()
    if event.get("lat") and event.get("lng"):
        data["location"]["geo"] = {"@type": "GeoCoordinates",
                                   "latitude": event["lat"], "longitude": event["lng"]}
    # Optional in events.json: "organizer": {"name": "...", "url": "..."}
    organizer = event.get("organizer")
    if isinstance(organizer, str):
        organizer = {"name": organizer}
    if organizer and organizer.get("name"):
        data["organizer"] = {"@type": "Organization", **organizer}
    return data


def breadcrumb_nav(prefix, trail):
    """The visible "Home / Events / This event" trail at the top of a page."""
    items = []
    for name, path in trail[:-1]:
        items.append(f'<li><a href="{prefix}{path or "index.html"}">{esc(name)}</a></li>')
    items.append(f'<li aria-current="page">{esc(trail[-1][0])}</li>')
    return ('    <nav class="breadcrumb" aria-label="Breadcrumb">\n      <ol>'
            + "".join(items) + "</ol>\n    </nav>")


def page_shell(prefix, head_html, body_class, current, main_html, scripts=""):
    """A whole page around some main content: head, header, banner, footer."""
    return f"""<!DOCTYPE html>
<!-- GENERATED FILE: made by tools/build_site.py from events.json.
     Edit events.json and run the script; changes made here get overwritten. -->
<html lang="en">
{head_html}
<body class="{body_class}">
{build_blog.header(prefix, current)}

{main_html}

{build_blog.footer(prefix)}
{scripts}</body>
</html>
"""


def build_event_page(event):
    slug = event["slug"]
    prefix = "../../"
    path = f"events/{slug}/"
    file = EVENTS_DIR / slug / "index.html"
    url = seo.absolute(path)
    day = event_date(event)
    start, end = start_and_end(event)
    passed = day < TODAY

    when = f"{short_date(day)} · {nice_time(event['start_time'])}"
    image = og_images.event_image(event, slug, when).relative_to(ROOT).as_posix()
    trail = [("Home", ""), ("Events", "events.html"), (event["title"], path)]
    head_html = build_blog.head(
        prefix, path, file, event_title(event), event_description(event), "website",
        json_ld=[event_json_ld(event, url, image), seo.breadcrumbs(trail)],
        image=image, image_alt=f"{event['title']}: {when} at {event['venue']}")

    times = f'<span class="time-chip">{nice_time(event["start_time"])}</span>'
    if event.get("end_time"):
        times += f'<span class="time-until">until {nice_time(event["end_time"])}</span>'

    buttons = []
    if event.get("link"):
        label = link_label(event["link"])
        buttons.append(f'<a class="event-link" href="{esc(event["link"])}" target="_blank" rel="noopener" '
                       f'aria-label="{esc(event["title"])}: {label}, opens in a new tab">{label} ↗</a>')
    if event.get("address"):
        maps = "https://www.google.com/maps/search/?api=1&query=" + \
               re.sub(r"\s+", "+", f"{event['venue']}, {event['address']}")
        buttons.append(f'<a class="event-link" href="{esc(maps)}" target="_blank" rel="noopener" '
                       f'aria-label="Directions to {esc(event["venue"])}, opens in a new tab">Directions ↗</a>')

    # Upcoming: more on the same day. Past: what's on this week instead.
    if passed:
        more_button = f'<a class="button" href="{prefix}events.html">What\'s on this week</a>'
    else:
        more_button = (f'<a class="button" href="{prefix}events.html?day={day.isoformat()}">'
                       f'More on {day:%A}, {day:%b} {day.day}</a>')

    address = f'\n          <p class="event-address">{esc(event["address"])}</p>' if event.get("address") else ""
    category_class = "cat-" + event["category"].lower().replace(" ", "-")

    main_html = f"""  <main class="event-page">
{breadcrumb_nav(prefix, trail)}

    <!-- Shown when the event's date has passed. The build sets "hidden" for
         upcoming events, and the little script at the bottom double-checks
         against today's date, in case the site hasn't been rebuilt since. -->
    <p class="event-passed" data-event-date="{day.isoformat()}"{"" if passed else " hidden"}>
      This event has passed. <a href="{prefix}events.html">See what's on this week</a>.
    </p>

    <article class="event-card event-detail {category_class}">
      <div class="card-top">
        <span class="event-category">{esc(event["category"])}</span>
        <h1>{esc(event["title"])}</h1>
        <p class="event-venue">{esc(event["venue"])}</p>
      </div>
      <div class="card-bottom">
        <p class="event-when"><time datetime="{start.isoformat()}">{long_date(day)}</time></p>
        <div class="times">{times}</div>
        <p class="event-description">{esc(event.get("long_description") or event["description"])}</p>{address}
        <div class="card-footer">{"".join(buttons)}</div>
      </div>
    </article>

    <p class="disclaimer"><strong>Good to know:</strong> Search Central Florida curates this event but doesn't produce, host or manage it. Details can change, so always check with the event host before you commit to going or buy tickets.</p>

    <div class="buttons event-more">
      {more_button}
      <a class="button button-outline" href="{prefix}events/">All events</a>
    </div>
  </main>"""

    scripts = f"""  <script>
    // Show "This event has passed" once the date is behind us (Orlando time),
    // even if the site hasn't been rebuilt since the event.
    (function () {{
      const note = document.querySelector(".event-passed");
      const today = new Intl.DateTimeFormat("en-CA", {{ timeZone: "America/New_York" }}).format(new Date());
      if (note.dataset.eventDate < today) note.hidden = false;
    }})();
  </script>
"""
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(page_shell(prefix, head_html, "page-events", "Events", main_html, scripts), encoding="utf-8")


def event_row(event, prefix):
    """One line in an event list: linked title, then when and where."""
    day = event_date(event)
    return (f'        <li><a href="{prefix}events/{event["slug"]}/">{esc(event["title"])}</a>'
            f' <span class="event-index-meta">{short_date(day)} · {nice_time(event["start_time"])}'
            f' · {esc(event["venue"])} · {esc(event["category"])}</span></li>')


def build_events_index(events):
    """events/index.html: every event we've listed, upcoming first."""
    prefix = "../"
    path = "events/"
    file = EVENTS_DIR / "index.html"
    upcoming = [e for e in events if event_date(e) >= TODAY]
    past = sorted((e for e in events if event_date(e) < TODAY),
                  key=lambda e: (e["date"], e["start_time"]), reverse=True)
    trail = [("Home", ""), ("Events", "events.html"), ("All events", path)]
    head_html = build_blog.head(
        prefix, path, file, seo.full_title("All Orlando Events"),
        "Every Orlando art, music, market, comedy, film and community event we've listed, "
        "coming up and past, each with its own page.", "website",
        json_ld=[seo.breadcrumbs(trail)])

    def section(heading, rows, empty):
        body = "\n".join(event_row(e, prefix) for e in rows) if rows else f"        <li>{empty}</li>"
        return f"""    <h2 class="section-head">{heading}</h2>
      <ul class="event-index">
{body}
      </ul>"""

    main_html = f"""  <main class="events-main">
{breadcrumb_nav(prefix, trail)}
    <header class="masthead">
      <p class="section-chip">Orlando events</p>
      <h1>All events</h1>
      <p class="masthead-intro">Everything we've put on the calendar. For this week's picks on a map, see the <a href="{prefix}events.html">events page</a>.</p>
    </header>

{section("Coming up", upcoming, "Nothing listed yet. Check back soon!")}

{section("Past events", past, "No past events yet.")}
  </main>"""
    file.write_text(page_shell(prefix, head_html, "page-events", "Events", main_html), encoding="utf-8")


def update_events_list(events):
    """Write a plain list of upcoming events into events.html, between the
    EVENTS-LIST markers. Search engines read it; for visitors, the calendar
    script replaces it with the day's cards a moment after the page opens."""
    path = ROOT / "events.html"
    page = path.read_text(encoding="utf-8")
    if LIST_START not in page:
        print("events.html has no EVENTS-LIST markers; skipped the static list")
        return
    upcoming = [e for e in events if event_date(e) >= TODAY]
    rows = "\n".join(event_row(e, "") for e in upcoming) or "        <li>Nothing listed yet.</li>"
    inner = (" (written by tools/build_site.py; the script below replaces it) -->\n"
             '      <ul class="event-index">\n' + rows + "\n      </ul>\n      ")
    before, rest = page.split(LIST_START, 1)
    _, after = rest.split(LIST_END, 1)
    path.write_text(before + LIST_START + inner + LIST_END + after, encoding="utf-8")


# ---------------------------------------------------------------------------
# The hand-written pages
# ---------------------------------------------------------------------------

def faq_json_ld(page):
    """FAQPage structured data, read from the <details> questions in the page."""
    questions = []
    for question, answer in re.findall(r"<details>\s*<summary>(.*?)</summary>(.*?)</details>", page, re.S):
        text = html.unescape(re.sub(r"<[^>]+>", "", answer))
        questions.append({
            "@type": "Question",
            "name": html.unescape(question.strip()),
            "acceptedAnswer": {"@type": "Answer", "text": " ".join(text.split())},
        })
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": questions}


def update_hand_written_pages():
    """Write each hand-written page's SEO tags between its SEO markers."""
    pages = json.loads(PAGES_FILE.read_text(encoding="utf-8"))
    for name, info in pages.items():
        if name.startswith("_"):
            continue
        file = ROOT / name
        page = file.read_text(encoding="utf-8")
        if SEO_START not in page:
            sys.exit(f"{name}: no {SEO_START} ... {SEO_END} markers in its <head>")

        schema = []
        for kind in info.get("schema", []):
            schema.append({"Organization": seo.organization, "WebSite": seo.website,
                           "FAQPage": lambda: faq_json_ld(page)}[kind]())

        tags = seo.render_head(
            path="" if name == "index.html" else name, file=file,
            title=seo.full_title(info["topic"]), description=info["description"],
            robots=info.get("robots", "index, follow"), og_type=info.get("og_type", "website"),
            json_ld=schema, sitemap=info.get("sitemap", True))
        block = (" These tags are written by tools/build_site.py from\n"
                 "       seo/pages.json and seo/site.json. Edit those files, not this block. -->\n"
                 + tags + "\n  ")
        before, rest = page.split(SEO_START, 1)
        _, after = rest.split(SEO_END, 1)
        file.write_text(before + SEO_START + block + SEO_END + after, encoding="utf-8")


# ---------------------------------------------------------------------------
# Fresh files after every update ("cache busting")
# ---------------------------------------------------------------------------

# The site's own CSS and JavaScript files. Browsers keep a saved copy of
# these, so after an update a visitor could see the new page with the OLD
# styles. Adding "?v=" plus a code made from the file's contents, like
# style.css?v=3f9a1c2e, gives each version its own address: when the file
# changes, the code changes, and every browser fetches the new copy.
VERSIONED_FILES = ["style.css", "banner.js", "events-common.js", "config.js"]


def add_version_codes():
    codes = {name: seo.fingerprint(ROOT / name)[:8] for name in VERSIONED_FILES}
    names = "|".join(re.escape(name) for name in VERSIONED_FILES)
    pattern = re.compile(r'((?:src|href)="(?:\.\./)*)(' + names + r')(?:\?v=[0-9a-f]+)?"')
    for page in seo.PAGES:
        text = page["file"].read_text(encoding="utf-8")
        new = pattern.sub(lambda m: f'{m.group(1)}{m.group(2)}?v={codes[m.group(2)]}"', text)
        if new != text:
            page["file"].write_text(new, encoding="utf-8")


# ---------------------------------------------------------------------------

def main():
    og_images.default_image()

    print("\n== Blog")
    build_blog.main()

    print("\n== Events")
    events = load_events()
    for event in events:
        build_event_page(event)
    build_events_index(events)
    update_events_list(events)
    print(f"built {len(events)} event pages and events/index.html")

    print("\n== Hand-written pages")
    update_hand_written_pages()
    print("updated the SEO tags in " + ", ".join(
        k for k in json.loads(PAGES_FILE.read_text(encoding="utf-8")) if not k.startswith("_")))

    add_version_codes()

    print("\n== Checks")
    errors, warnings = seo.check_pages()
    for warning in warnings:
        print("  warning: " + warning)
    if errors:
        for error in errors:
            print("  ERROR: " + error)
        sys.exit(f"\n{len(errors)} problem(s) to fix before publishing (see ERROR lines above).")
    print(f"  {len(seo.PAGES)} pages checked, {len(warnings)} warning(s), no errors")

    print("\n== Sitemap, robots.txt, IndexNow")
    published, changed, removed = seo.update_published()
    seo.write_sitemap(published)
    seo.write_robots()
    key = seo.SITE["indexnow_key"]
    (ROOT / f"{key}.txt").write_text(key, encoding="utf-8")
    print(f"  sitemap.xml lists {len(published)} pages")
    if changed or removed:
        print(f"  {len(changed)} page(s) changed and {len(removed)} removed since the last build:")
        for url in changed + removed:
            print("    " + url)
        print("  After publishing, tools/indexnow.py tells Bing about them.")
    else:
        print("  no pages changed since the last build")


if __name__ == "__main__":
    main()
