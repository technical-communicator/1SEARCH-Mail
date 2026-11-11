"""Shared SEO helpers: one place that writes every page's <head> tags.

Every page on the site, hand-written or generated, gets its search and
social tags from render_head() below, so they always match:

  - <title> and <meta name="description">
  - <link rel="canonical"> (the page's one "official" address)
  - <meta name="robots"> (may search engines list this page?)
  - Open Graph tags (og:...) for link previews on Instagram, iMessage, etc.
  - Twitter / X card tags
  - JSON-LD structured data (the <script type="application/ld+json"> blocks
    that tell Google "this is an event", "this is an FAQ", ...)

The site-wide defaults (address, name, default share image) live in ONE
file, seo/site.json. Titles and descriptions for the hand-written pages
live in seo/pages.json.

Each time render_head() runs, it also notes the page in PAGES. At the end
of a build, check_pages() looks for missing or duplicate titles and
descriptions (and a few accessibility basics), and update_sitemap() writes
sitemap.xml with each page's last-changed date.

This file is a helper: run tools/build_site.py, which uses it.
"""

import datetime
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "seo" / "site.json").read_text(encoding="utf-8"))
BASE_URL = SITE["base_url"]                      # ends with "/"
TITLE_MAX = SITE["limits"]["title_max"]
DESCRIPTION_MAX = SITE["limits"]["description_max"]

# Where we remember each page's fingerprint and last-changed date, so the
# sitemap's <lastmod> dates are real and IndexNow only hears about pages
# that actually changed.
PUBLISHED_FILE = ROOT / "seo" / "published.json"

# Every page made or updated in this build. render_head() adds to it.
PAGES = []


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def esc(text):
    """Escape text for safe use inside HTML."""
    return html.escape(str(text), quote=True)


def absolute(path):
    """'blog/x.html' -> 'https://www.searchcentralfl.com/blog/x.html'"""
    return BASE_URL + str(path).lstrip("/")


def full_title(topic):
    """'Orlando Events This Week' -> 'Orlando Events This Week | Search Central Florida'"""
    return topic + SITE["title_suffix"]


def today_in_orlando():
    """Today's date in Orlando (Eastern time), as a date object."""
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo("America/New_York")).date()


def shorten(text, limit):
    """Cut text to at most `limit` characters, at a word break, adding "..."."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 3].rsplit(" ", 1)[0].rstrip(" ,.;:!-")
    return cut + "..."


def git_date(path):
    """The date a file was last changed: its last commit, or today if it has
    changes that aren't committed yet (or isn't in git at all)."""
    path = Path(path)
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", str(path)],
                               cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if not dirty:
            out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(path)],
                                 cwd=ROOT, capture_output=True, text=True).stdout.strip()
            if out:
                return datetime.date.fromisoformat(out)
    except (OSError, ValueError):
        pass
    return today_in_orlando()


# ---------------------------------------------------------------------------
# Structured data (JSON-LD)
# ---------------------------------------------------------------------------

def json_ld_script(data, indent="  "):
    """One <script type="application/ld+json"> block. It's written into the
    page's HTML by the build, so Google sees it without running JavaScript.
    ("</" is escaped so text can never close the script tag early.)"""
    body = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    body = body.replace("\n", "\n" + indent)
    return f'{indent}<script type="application/ld+json">\n{indent}{body}\n{indent}</script>'


def organization():
    """Who runs the site. Used on the home page and as the publisher of posts."""
    org = SITE["organization"]
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": BASE_URL + "#organization",
        "name": org["name"],
        "alternateName": org["alternate_name"],
        "url": BASE_URL,
        "logo": absolute(org["logo"]),
        "description": org["description"],
        "email": org["email"],
        "areaServed": org["area_served"],
        "sameAs": org["same_as"],
    }


def website():
    """The site itself (helps Google show the site name in results)."""
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": BASE_URL + "#website",
        "name": SITE["site_name"],
        "alternateName": SITE["organization"]["alternate_name"],
        "url": BASE_URL,
        "inLanguage": "en-US",
        "publisher": {"@id": BASE_URL + "#organization"},
    }


def publisher():
    """A short reference to the organisation, for posts and events."""
    org = SITE["organization"]
    return {"@type": "Organization", "@id": BASE_URL + "#organization",
            "name": org["name"], "url": BASE_URL,
            "logo": {"@type": "ImageObject", "url": absolute(org["logo"])}}


def breadcrumbs(trail):
    """The "Home > Blog > This post" trail Google can show above a result.
    trail is a list of (name, path) pairs, starting from the home page."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": absolute(path)}
            for i, (name, path) in enumerate(trail, start=1)
        ],
    }


# ---------------------------------------------------------------------------
# The <head> tags
# ---------------------------------------------------------------------------

def render_head(*, path, file, title, description, robots="index, follow",
                og_type="website", image=None, image_alt=None, json_ld=(),
                extra_meta=(), sitemap=True, indent="  "):
    """Return the SEO tags for one page, as HTML lines.

      path        the page's address from the site root, e.g. "blog/x.html"
                  ("" for the home page). Used for the canonical and og:url.
      file        where the page is saved, e.g. ROOT / "blog" / "x.html"
      title       the full <title>, e.g. "Orlando Events | Search Central Florida"
      description up to 155 characters, shown under the title in Google
      robots      "index, follow" (normal) or "noindex, nofollow" (private)
      og_type     "website", or "article" for blog posts. (Open Graph has
                  no "event" type, so event pages use "website".)
      image       path to a 1200x630 share image (default from site.json)
      json_ld     a list of structured data dicts (see the helpers above)
      extra_meta  extra (property, content) Open Graph pairs
      sitemap     False to leave the page out of sitemap.xml
    """
    url = absolute(path)
    image = image or SITE["default_og_image"]
    image_alt = image_alt or SITE["default_og_image_alt"]

    PAGES.append({"path": path, "url": url, "file": Path(file), "title": title,
                  "description": description, "robots": robots,
                  "sitemap": sitemap and robots.startswith("index")})

    lines = [
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
        f'<link rel="canonical" href="{esc(url)}">',
        f'<meta name="robots" content="{esc(robots)}">',
        "",
        "<!-- Open Graph and Twitter tags: how the link looks when it's shared. -->",
        f'<meta property="og:site_name" content="{esc(SITE["site_name"])}">',
        f'<meta property="og:locale" content="{esc(SITE["locale"])}">',
        f'<meta property="og:type" content="{esc(og_type)}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="og:image" content="{esc(absolute(image))}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(image_alt)}">',
    ]
    lines += [f'<meta property="{esc(p)}" content="{esc(c)}">' for p, c in extra_meta]
    lines += [
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
        f'<meta name="twitter:image" content="{esc(absolute(image))}">',
        f'<meta name="twitter:image:alt" content="{esc(image_alt)}">',
    ]
    # The site icon (the mascot), in the sizes Google and phones want.
    # Google only uses icons whose size is a multiple of 48 pixels.
    # The paths start with "/" so they work from any folder.
    lines += [
        "",
        "<!-- Site icon: the mascot head. Google shows it next to search results. -->",
        '<link rel="icon" href="/favicon.ico" sizes="48x48">',
        '<link rel="icon" type="image/png" sizes="96x96" href="/images/icons/icon-96.png">',
        '<link rel="icon" type="image/png" sizes="192x192" href="/images/icons/icon-192.png">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
    ]
    out = "\n".join((indent + line) if line else "" for line in lines)
    if json_ld:
        out += "\n\n" + indent + "<!-- Structured data for search engines (schema.org). -->\n"
        out += "\n".join(json_ld_script(item, indent) for item in json_ld)
    return out


# ---------------------------------------------------------------------------
# Checks, run at the end of every build
# ---------------------------------------------------------------------------

def check_pages():
    """Check every page made in this build. Returns (errors, warnings).
    Errors stop the build; warnings are printed so they can be fixed."""
    errors, warnings = [], []
    seen_titles, seen_urls = {}, {}

    for page in PAGES:
        name = page["path"] or "index.html (home)"
        if not page["title"].strip():
            errors.append(f"{name}: has no title")
        if not page["description"].strip():
            errors.append(f"{name}: has no meta description")
        if len(page["title"]) > TITLE_MAX:
            warnings.append(f"{name}: title is {len(page['title'])} characters "
                            f"(aim for {TITLE_MAX} or fewer): {page['title']}")
        if len(page["description"]) > DESCRIPTION_MAX:
            warnings.append(f"{name}: description is {len(page['description'])} characters "
                            f"(aim for {DESCRIPTION_MAX} or fewer)")
        if not page["title"].endswith(SITE["title_suffix"]):
            warnings.append(f"{name}: title doesn't end with '{SITE['title_suffix'].strip()}'")
        if page["title"] in seen_titles:
            errors.append(f"{name}: same title as {seen_titles[page['title']]}: {page['title']}")
        seen_titles.setdefault(page["title"], name)
        if page["url"] in seen_urls:
            errors.append(f"{name}: same address as {seen_urls[page['url']]}")
        seen_urls.setdefault(page["url"], name)

        # Accessibility and SEO basics, read from the finished HTML file.
        if page["file"].exists():
            text = page["file"].read_text(encoding="utf-8")
            text = re.sub(r"<!--.*?-->", "", text, flags=re.S)      # ignore comments
            text = re.sub(r"<script\b.*?</script>", "", text, flags=re.S)
            if '<html lang="en"' not in text:
                errors.append(f"{name}: <html> is missing lang=\"en\"")
            h1s = len(re.findall(r"<h1\b", text))
            if h1s != 1:
                errors.append(f"{name}: has {h1s} <h1> headings (there should be exactly one)")
            for tag in re.findall(r"<img\b[^>]*>", text):
                if not re.search(r"\balt=", tag):
                    errors.append(f"{name}: image without alt text: {tag[:80]}")
            last = 0
            for level in (int(n) for n in re.findall(r"<h([1-6])\b", text)):
                if last and level > last + 1:
                    warnings.append(f"{name}: heading jumps from h{last} to h{level}")
                last = level
    return errors, warnings


def fingerprint(file):
    """A short code that changes whenever the page's content changes."""
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()[:16]


def update_published():
    """Compare every public page with the last build. Pages that changed get
    today's date as their last-changed date (used in sitemap.xml and by
    tools/indexnow.py). Returns (pages with dates, changed urls, removed urls)."""
    old = {}
    if PUBLISHED_FILE.exists():
        old = json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
    today = today_in_orlando().isoformat()

    new, changed = {}, []
    for page in PAGES:
        if not page["sitemap"]:
            continue
        code = fingerprint(page["file"])
        before = old.get(page["url"])
        if before and before["hash"] == code:
            new[page["url"]] = before
        else:
            new[page["url"]] = {"hash": code, "lastmod": today}
            changed.append(page["url"])

    PUBLISHED_FILE.write_text(json.dumps(dict(sorted(new.items())), indent=2) + "\n",
                              encoding="utf-8")
    removed = sorted(set(old) - set(new))
    return new, changed, removed


def write_sitemap(published):
    """Write sitemap.xml: every public page with its last-changed date."""
    rows = "\n".join(
        f"  <url>\n    <loc>{esc(url)}</loc>\n    <lastmod>{info['lastmod']}</lastmod>\n  </url>"
        for url, info in published.items()
    )
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!-- GENERATED FILE: made by tools/build_site.py. Don't edit by hand. -->\n"
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}\n</urlset>\n", encoding="utf-8")


def write_robots():
    """Write robots.txt: crawl everything except the private and source folders."""
    (ROOT / "robots.txt").write_text(
        "# GENERATED FILE: made by tools/build_site.py.\n"
        "# Search engines may crawl the whole site except the private review\n"
        "# page and the folders that only hold source files.\n"
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin.html\n"
        "Disallow: /posts/\n"
        "Disallow: /tools/\n"
        "Disallow: /supabase/\n"
        "Disallow: /seo/\n"
        "\n"
        f"Sitemap: {BASE_URL}sitemap.xml\n", encoding="utf-8")
