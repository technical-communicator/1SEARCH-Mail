#!/usr/bin/env python3
"""Build the SCF blog from Markdown.

Each post is a Markdown file in posts/ with a small header ("front matter")
between two --- lines, for example:

    ---
    title: "check your mailbox! | november's mail"
    date: 2026-11-09
    description: "One or two sentences for Google and link previews."
    tags: [mail club, featured artist]
    series: Monthly Mail          # optional
    cover: images/blog/xyz.webp   # optional, path from the site root
    cover_alt: "What the image shows"   # required if there's a cover
    ---

    The post text in Markdown...

Running this script:
  1. writes one page per post to blog/<file name>.html
  2. rebuilds the post list in blog.html
  3. refreshes the "Past mailers" list in mailclub.html
     (posts whose series is "Monthly Mail")

The output is plain HTML that gets committed, so GitHub Pages still just
serves static files. Needs: pip install markdown pyyaml

Usage (from the repo root):  python3 tools/build_blog.py
"""

import datetime
import html
import json
import math
import re
import sys
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
BLOG_DIR = ROOT / "blog"
SITE_URL = "https://technical-communicator.github.io/SEARCH-Mail/"
MAIL_SERIES = "Monthly Mail"
REQUIRED = ["title", "date", "description", "tags"]


def esc(text):
    """Escape text for safe use inside HTML."""
    return html.escape(str(text), quote=True)


def nice_date(date):
    """2026-11-09 -> November 9, 2026"""
    return f"{date:%B} {date.day}, {date.year}"


def load_post(path):
    """Read one Markdown file and return its details as a dict."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        sys.exit(f"{path.name}: missing the --- front matter block at the top")
    meta = yaml.safe_load(match.group(1)) or {}
    body_md = match.group(2)

    for field in REQUIRED:
        if not meta.get(field):
            sys.exit(f"{path.name}: front matter is missing '{field}'")
    if meta.get("cover") and not meta.get("cover_alt"):
        sys.exit(f"{path.name}: has a cover image but no cover_alt text")

    # House style: never use em dashes anywhere in site copy.
    for label, value in [("title", meta["title"]), ("description", meta["description"]), ("body", body_md)]:
        if "—" in str(value):
            sys.exit(f"{path.name}: the {label} contains an em dash (—). Rewrite it without one.")

    date = meta["date"]
    if isinstance(date, str):
        date = datetime.date.fromisoformat(date)

    words = len(re.findall(r"\w+", body_md))
    return {
        "slug": path.stem,
        "title": str(meta["title"]),
        "date": date,
        "description": str(meta["description"]),
        "tags": [str(t) for t in meta["tags"]],
        "series": meta.get("series"),
        "cover": meta.get("cover"),
        "cover_alt": meta.get("cover_alt", ""),
        "minutes": max(1, math.ceil(words / 200)),
        "body_html": markdown.markdown(body_md, extensions=["extra", "sane_lists"]),
    }


def header(prefix, current):
    """The site header. prefix is "" for root pages, "../" for pages in blog/."""
    links = [("events.html", "Events"), ("mailclub.html", "Mail Club"),
             ("blog.html", "Blog"), ("about.html", "About")]
    nav = "\n".join(
        f'      <a href="{prefix}{href}"{" aria-current=\"page\"" if label == current else ""}>{label}</a>'
        for href, label in links
    )
    return f"""  <header class="site-header">
    <!-- The logo (mascot head + name) links back to the home page. -->
    <a class="logo" href="{prefix}index.html">
      <!-- alt="" because the words next to it already name the link. -->
      <img src="{prefix}images/mascot-head-white.webp" alt="" width="178" height="200">
      <span class="logo-text">
        <span class="logo-name">SEARCH</span>
        <span class="logo-sub">Central Florida</span>
      </span>
    </a>
    <nav>
{nav}
    </nav>
  </header>"""


def head(prefix, title, description, url, og_type, extra=""):
    """Everything inside <head>: titles, link preview tags, fonts, CSS."""
    return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{url}">

  <!-- Open Graph tags control how links look when shared on social media. -->
  <meta property="og:type" content="{og_type}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE_URL}images/mascot.webp">

  <link rel="icon" type="image/png" href="{prefix}images/favicon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Rubik+Dirt&display=swap">
  <link rel="stylesheet" href="{prefix}style.css">{extra}
</head>"""


def footer(prefix):
    return f"""  <footer class="site-footer">
    <img src="{prefix}images/stamp.png" alt="" width="600" height="600">
    <p>Follow us on Instagram: <a href="https://www.instagram.com/searchcentralfl/">@searchcentralfl</a></p>
  </footer>"""


def tag_list(tags):
    items = "".join(f"<li>{esc(t)}</li>" for t in tags)
    return f'<ul class="tag-list" aria-label="Tags">{items}</ul>'


def build_post_page(post):
    url = f"{SITE_URL}blog/{post['slug']}.html"

    # Structured data so Google understands this page is a blog post.
    json_ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"],
        "description": post["description"],
        "datePublished": post["date"].isoformat(),
        "url": url,
        "image": SITE_URL + (post["cover"] or "images/mascot.webp"),
        "author": {"@type": "Organization", "name": "Search Central Florida"},
        "publisher": {"@type": "Organization", "name": "Search Central Florida",
                      "url": SITE_URL},
    }
    extra = ('\n  <script type="application/ld+json">\n  '
             + json.dumps(json_ld, ensure_ascii=False).replace("</", "<\\/")
             + "\n  </script>")

    cover = ""
    if post["cover"]:
        cover = (f'\n      <img class="post-cover" src="../{esc(post["cover"])}" '
                 f'alt="{esc(post["cover_alt"])}">')

    series = ""
    if post["series"]:
        series = f'<p class="post-series">{esc(post["series"])}</p>\n      '

    return f"""<!DOCTYPE html>
<!-- GENERATED FILE: made by tools/build_blog.py from posts/{post['slug']}.md.
     Edit the .md file and run the script; changes made here get overwritten. -->
<html lang="en">
{head("../", post["title"] + " | SEARCH Central Florida blog", post["description"], url, "article", extra)}
<body>
{header("../", "Blog")}

  <main class="post-main">
    <p><a class="back-link" href="../blog.html">&larr; All posts</a></p>

    <article class="post">
      {series}<h1>{esc(post["title"])}</h1>
      <p class="post-meta">
        <time datetime="{post["date"].isoformat()}">{nice_date(post["date"])}</time>
        &middot; {post["minutes"]} min read
      </p>
      {tag_list(post["tags"])}{cover}

      <div class="panel prose">
{post["body_html"]}
      </div>
    </article>

    <!-- Every post ends with a nudge toward the mail club. -->
    <aside class="post-cta panel">
      <p><strong>Want local art in your mailbox?</strong> Every month, SEARCH: a snail mail club sends you work from a different Central Florida artist, plus perks from local businesses.</p>
      <a class="button" href="../mailclub.html">Join the mail club</a>
    </aside>
  </main>

{footer("../")}
</body>
</html>
"""


def post_card(post, prefix):
    """A card for one post, used on blog.html."""
    cover = ""
    if post["cover"]:
        cover = f'<img class="post-card-cover" src="{prefix}{esc(post["cover"])}" alt="{esc(post["cover_alt"])}">'
    series = f'<span class="post-series">{esc(post["series"])}</span>' if post["series"] else ""
    return f"""      <article class="post-card">
        {cover}{series}
        <h2><a href="{prefix}blog/{post["slug"]}.html">{esc(post["title"])}</a></h2>
        <p class="post-meta"><time datetime="{post["date"].isoformat()}">{nice_date(post["date"])}</time> &middot; {post["minutes"]} min read</p>
        <p>{esc(post["description"])}</p>
        {tag_list(post["tags"])}
      </article>"""


def build_index(posts):
    url = f"{SITE_URL}blog.html"
    if posts:
        cards = "\n".join(post_card(p, "") for p in posts)
    else:
        cards = '      <p class="panel">The first posts are coming soon!</p>'
    return f"""<!DOCTYPE html>
<!-- GENERATED FILE: made by tools/build_blog.py. Edit posts/*.md and run the script. -->
<html lang="en">
{head("", "Blog | Orlando local art, events and mail club news | SEARCH Central Florida",
      "Guides, local artist spotlights and snail mail club news from Search Central Florida, your hyperlocal Orlando arts and culture guide.",
      url, "website")}
<body>
{header("", "Blog")}

  <main>
    <h1>Blog</h1>
    <p class="lede">Local artists, Orlando guides and news from the mail club.</p>

    <div class="post-list">
{cards}
    </div>
  </main>

{footer("")}
</body>
</html>
"""


def update_mailclub(posts):
    """Refresh the list between the PAST-MAILERS markers in mailclub.html."""
    path = ROOT / "mailclub.html"
    page = path.read_text(encoding="utf-8")
    start, end = "<!-- PAST-MAILERS:START -->", "<!-- PAST-MAILERS:END -->"
    if start not in page or end not in page:
        print("mailclub.html has no PAST-MAILERS markers; skipped")
        return
    mailers = [p for p in posts if p["series"] == MAIL_SERIES]
    if mailers:
        items = "\n".join(
            f'          <li><a href="blog/{p["slug"]}.html">{esc(p["title"])}</a> '
            f'<span class="post-meta">{p["date"]:%B %Y}</span></li>'
            for p in mailers
        )
        inner = f'\n        <ul class="mailer-list">\n{items}\n        </ul>\n        '
    else:
        inner = "\n        <p>Our first mailer recap is coming soon.</p>\n        "
    before, rest = page.split(start, 1)
    _, after = rest.split(end, 1)
    path.write_text(before + start + inner + end + after, encoding="utf-8")


def main():
    posts = [load_post(p) for p in sorted(POSTS_DIR.glob("*.md"))]
    posts.sort(key=lambda p: p["date"], reverse=True)  # newest first

    BLOG_DIR.mkdir(exist_ok=True)
    for post in posts:
        (BLOG_DIR / f"{post['slug']}.html").write_text(build_post_page(post), encoding="utf-8")
        print(f"built blog/{post['slug']}.html")

    (ROOT / "blog.html").write_text(build_index(posts), encoding="utf-8")
    print(f"built blog.html ({len(posts)} post{'' if len(posts) == 1 else 's'})")
    update_mailclub(posts)


if __name__ == "__main__":
    main()
