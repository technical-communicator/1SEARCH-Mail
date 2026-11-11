#!/usr/bin/env python3
"""Build the SCF blog from Markdown.

Each post is a Markdown file in posts/ with a small header ("front matter")
between two --- lines, for example:

    ---
    title: "check your mailbox! | november's mail"
    date: 2026-11-09
    description: "One or two sentences. Shown under the title, on cards and in Google."
    tags: [mail club, featured artist]
    series: Monthly Mail          # optional, one of the SERIES names below
    cover: images/blog/xyz.webp   # optional, path from the site root
    cover_alt: "What the image shows"   # required if there's a cover
    ---

    The post text in Markdown...

Running this script:
  1. writes one page per post to blog/<file name>.html
  2. writes the blog front page, blog.html (all posts)
  3. writes one page per series to blog/series/<series>.html
  4. refreshes the "Past mailers" list in mailclub.html
     (posts whose series is "Monthly Mail")

The output is plain HTML that gets committed, so GitHub Pages still just
serves static files. Needs: pip install markdown pyyaml pillow

Usually you run the whole-site build instead, which runs this too and then
makes the sitemap:  python3 tools/build_site.py

Optional front matter for search results (when the title or description is
too long for Google, which shows about 60 and 155 characters):
    seo_title: "Featured Artist: Xine Hann"    # " | Search Central Florida" is added
    seo_description: "A shorter summary, 155 characters at most."
"""

import datetime
import html
import math
import re
import sys
from pathlib import Path

import markdown
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import og_images                                     # noqa: E402
import seo                                           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
BLOG_DIR = ROOT / "blog"
SERIES_DIR = BLOG_DIR / "series"
SITE_URL = seo.BASE_URL   # set once, in seo/site.json
MAIL_SERIES = "Monthly Mail"
REQUIRED = ["title", "date", "description", "tags"]

# The blog's sections, shown as the coloured tabs along the bottom of every
# blog page. To add a series: add a line here, then use its name as the
# "series:" in a post. Colours are names from style.css (series-<colour>).
SERIES = [
    # (name in posts,     page file name,      tab colour, one-line intro)
    ("Monthly Mail",      "monthly-mail",      "pink",
     "what's waiting in your mailbox each month from SEARCH: a snail mail club."),
    ("Featured Artist",   "featured-artist",   "blue",
     "the central florida artists we spotlight and send to your mailbox."),
    ("Featured Business", "featured-business", "yellow",
     "local businesses giving special perks to our mail club members."),
]
SERIES_BY_NAME = {name: (slug, colour, intro) for name, slug, colour, intro in SERIES}
ALL_INTRO = "local artists, orlando guides and news from Search Central Florida."


def esc(text):
    """Escape text for safe use inside HTML."""
    return html.escape(str(text), quote=True)


def nice_date(date):
    """2026-11-09 -> November 9, 2026"""
    return f"{date:%B} {date.day}, {date.year}"


def short_date(date):
    """2026-11-09 -> Nov 9, 2026"""
    return f"{date:%b} {date.day}, {date.year}"


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
    if meta.get("series") and meta["series"] not in SERIES_BY_NAME:
        sys.exit(f"{path.name}: unknown series '{meta['series']}'. "
                 f"Use one of {list(SERIES_BY_NAME)} or add it to SERIES in this script.")

    # House style: never use em dashes anywhere in site copy.
    for label, value in [("title", meta["title"]), ("description", meta["description"]),
                         ("seo_title", meta.get("seo_title", "")),
                         ("seo_description", meta.get("seo_description", "")), ("body", body_md)]:
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
        "seo_title": str(meta.get("seo_title") or meta["title"]),
        "seo_description": str(meta.get("seo_description") or meta["description"]),
        "file": path,
        "tags": [str(t) for t in meta["tags"]],
        "series": meta.get("series"),
        "cover": meta.get("cover"),
        "cover_alt": meta.get("cover_alt", ""),
        "minutes": max(1, math.ceil(words / 200)),
        "body_html": markdown.markdown(body_md, extensions=["extra", "sane_lists"]),
    }


# ---------------------------------------------------------------------------
# Shared page parts
# ---------------------------------------------------------------------------

def header(prefix, current):
    """The site header. prefix is how to get back to the site root from this
    page: "" for root pages, "../" for blog/, "../../" for blog/series/."""
    links = [("events.html", "Events"), ("mailclub.html", "Mail Club"),
             ("blog.html", "Blog"), ("about.html", "About")]
    nav = "\n".join(
        f'      <a href="{prefix}{href}"{" aria-current=\"page\"" if label == current else ""}>{label}</a>'
        for href, label in links
    )
    return f"""  <header class="site-header" id="top">
    <!-- The logo (mascot head + name) links back to the home page. -->
    <a class="logo" href="{prefix}index.html">
      <!-- alt="" because the words next to it already name the link. -->
      <img src="{prefix}images/mascot-head-color.webp" alt="" width="213" height="240">
      <span class="logo-text">
        <span class="logo-name">SEARCH</span>
        <span class="logo-sub">Central Florida</span>
      </span>
    </a>
    <nav>
{nav}
    </nav>
  </header>"""


def head(prefix, path, file, title, description, og_type, json_ld=(),
         image=None, image_alt=None, extra_meta=()):
    """Everything inside <head>. The search and sharing tags come from
    seo.render_head() (tools/seo.py), the same as on every other page.
    path is the page's address from the site root, file is where it's saved."""
    tags = seo.render_head(path=path, file=file, title=title, description=description,
                           og_type=og_type, image=image, image_alt=image_alt,
                           json_ld=json_ld, extra_meta=extra_meta)
    return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
{tags}

  <link rel="icon" type="image/png" href="{prefix}images/favicon.png">
  <!-- Fonts: Anton for headlines, Courier Prime (typewriter) for text,
       Yellowtail (handwriting) for small accents. Same on every page. -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&family=Courier+Prime:ital,wght@0,400;0,700;1,400&family=Yellowtail&display=swap">
  <link rel="stylesheet" href="{prefix}style.css">
</head>"""


def footer(prefix):
    """The mail club banner (filled in by banner.js) and the site footer."""
    return f"""  <!-- The full-width mail club banner. banner.js fills in this empty spot. -->
  <div data-mailclub-banner data-root="{prefix}"></div>
  <script src="{prefix}banner.js"></script>

  <!-- The site footer. It's the same on every page: if you change it,
       change it in index.html, events.html, mailclub.html, about.html
       AND in footer() in tools/build_blog.py (for the blog pages). -->
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <a class="footer-logo" href="{prefix}index.html">
          <img loading="lazy" decoding="async" src="{prefix}images/mascot-head-color.webp" alt="" width="213" height="240">
          <span><strong>SEARCH</strong> Central Florida</span>
        </a>
        <p>A hyperlocal guide to Orlando arts, culture and small businesses. Find something good, close the app and go.</p>
      </div>

      <nav class="footer-col" aria-label="Explore">
        <h2>Explore</h2>
        <ul>
          <li><a href="{prefix}events.html">Events this week</a></li>
          <li><a href="{prefix}mailclub.html">Snail mail club</a></li>
          <li><a href="{prefix}blog.html">Blog</a></li>
          <li><a href="{prefix}about.html">About us</a></li>
          <li><a href="{prefix}submit.html">Submit an event</a></li>
        </ul>
      </nav>

      <!-- footer-col-mail is hidden on phones to keep the footer short. -->
      <nav class="footer-col footer-col-mail" aria-label="Mail club">
        <h2>Mail club</h2>
        <ul>
          <li><a href="{prefix}mailclub.html?tier=sticker#tiers">Sticker supporter</a></li>
          <li><a href="{prefix}mailclub.html?tier=print#tiers">Print collector</a></li>
          <li><a href="{prefix}mailclub.html?tier=curator#tiers">Print &amp; sticker curator</a></li>
          <li><a href="{prefix}mailclub.html#past-mailers">Past mailers</a></li>
        </ul>
      </nav>

      <div class="footer-col">
        <h2>Say hi</h2>
        <ul>
          <li><a href="https://www.instagram.com/searchcentralfl/">Instagram</a></li>
          <li><a href="mailto:searchcentralflorida@gmail.com">Email us</a></li>
          <li class="footer-note">Have an event? <a href="{prefix}submit.html">Submit it here</a>.</li>
        </ul>
      </div>
    </div>

    <div class="footer-bottom">
      <p>&copy; 2026 Search Central Florida. Made in Orlando.</p>
      <!-- For Search Central Florida's admins. The page asks for a login. -->
      <a href="{prefix}admin.html" class="footer-top">Admin login</a>
      <a href="#top" class="footer-top">Back to top &uarr;</a>
    </div>
  </footer>"""


def series_tabs(prefix, current):
    """The coloured section tabs fixed along the bottom of every blog page.
    current is a series name, "All" for blog.html, or None on a post page."""
    tabs = [("All posts", f"{prefix}blog.html", "red", current == "All")]
    for name, slug, colour, _ in SERIES:
        tabs.append((name, f"{prefix}blog/series/{slug}.html", colour, current == name))
    links = "\n".join(
        f'    <a class="series-{colour}" href="{href}"{" aria-current=\"page\"" if active else ""}>{esc(name)}</a>'
        for name, href, colour, active in tabs
    )
    return f"""  <!-- Section tabs: each one opens a page with just that kind of post. -->
  <nav class="series-tabs" aria-label="Blog sections">
{links}
  </nav>
  <script>
    // On small phones the tabs scroll sideways. Slide the current tab into view.
    const currentTab = document.querySelector(".series-tabs [aria-current]");
    if (currentTab) currentTab.scrollIntoView({{ block: "nearest", inline: "nearest" }});
  </script>"""


def series_label(post, prefix):
    """A small coloured link to the post's series page (or nothing)."""
    if not post["series"]:
        return ""
    slug, colour, _ = SERIES_BY_NAME[post["series"]]
    return (f'<a class="series-label series-{colour}" '
            f'href="{prefix}blog/series/{slug}.html">{esc(post["series"])}</a>')


def card_image(post, prefix, loading="lazy"):
    """The post's cover image. Posts without one get a block in their series
    colour with the mail club stamp on it, so every card has a picture."""
    if post["cover"]:
        return (f'<img class="card-image" src="{prefix}{esc(post["cover"])}" '
                f'alt="{esc(post["cover_alt"])}" loading="{loading}">')
    colour = SERIES_BY_NAME[post["series"]][1] if post["series"] else "red"
    return (f'<div class="card-image card-image-blank series-{colour}">'
            f'<img src="{prefix}images/stamp.webp" alt=""></div>')


def post_card(post, prefix):
    """One post in the grid: image, headline with arrow, summary, details."""
    return f"""      <article class="post-card">
        {card_image(post, prefix)}
        <h3 class="card-title">
          <!-- The link's ::after layer (in style.css) makes the whole card clickable. -->
          <a href="{prefix}blog/{post["slug"]}.html">{esc(post["title"])}</a>
          <span class="card-arrow" aria-hidden="true">&rarr;</span>
        </h3>
        <p class="card-summary">{esc(post["description"])}</p>
        <p class="card-meta">
          {series_label(post, prefix)}
          <time datetime="{post["date"].isoformat()}">{short_date(post["date"])}</time>
        </p>
      </article>"""


def lead_story(post, prefix):
    """The newest post, shown big at the top: words on the left, picture on the right."""
    return f"""    <article class="lead-story">
      <div class="lead-text">
        <h2 class="lead-title"><a href="{prefix}blog/{post["slug"]}.html">{esc(post["title"])}</a></h2>
        <p class="card-summary">{esc(post["description"])}</p>
        <p class="card-meta">
          {series_label(post, prefix)}
          <time datetime="{post["date"].isoformat()}">{short_date(post["date"])}</time>
          <span>{post["minutes"]} min read</span>
        </p>
      </div>
      {card_image(post, prefix, loading="eager")}
    </article>"""


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def build_post_page(post, all_posts):
    path = f"blog/{post['slug']}.html"
    file = BLOG_DIR / f"{post['slug']}.html"
    url = SITE_URL + path

    # The share picture: the cover cropped to 1200x630, or the site default.
    if post["cover"]:
        image = og_images.post_image(post["cover"], post["slug"]).relative_to(ROOT).as_posix()
        image_alt = post["cover_alt"]
    else:
        image, image_alt = seo.SITE["default_og_image"], None

    # dateModified: when the post's .md file last changed (never before its date).
    modified = max(seo.git_date(post["file"]), post["date"])

    # The trail Google can show above the result: Home > Blog > Series > Post.
    trail = [("Home", ""), ("Blog", "blog.html")]
    if post["series"]:
        trail.append((post["series"], f"blog/series/{SERIES_BY_NAME[post['series']][0]}.html"))
    trail.append((post["title"], path))

    # Structured data so Google understands this page is a blog post.
    images = [SITE_URL + image] + ([SITE_URL + post["cover"]] if post["cover"] else [])
    json_ld = [{
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"][:110],
        "description": post["description"],
        "datePublished": post["date"].isoformat(),
        "dateModified": modified.isoformat(),
        "mainEntityOfPage": url,
        "url": url,
        "image": images,
        "keywords": post["tags"],
        "author": {"@type": "Organization", "name": "Search Central Florida", "url": SITE_URL},
        "publisher": seo.publisher(),
    }, seo.breadcrumbs(trail)]
    if post["series"]:
        json_ld[0]["articleSection"] = post["series"]

    extra_meta = [("article:published_time", post["date"].isoformat()),
                  ("article:modified_time", modified.isoformat())]
    if post["series"]:
        extra_meta.append(("article:section", post["series"]))
    extra_meta += [("article:tag", t) for t in post["tags"]]
    head_html = head("../", path, file, seo.full_title(post["seo_title"]), post["seo_description"],
                     "article", json_ld, image, image_alt, extra_meta)

    hero = ""
    if post["cover"]:
        hero = (f'\n    <img class="post-hero" src="../{esc(post["cover"])}" '
                f'alt="{esc(post["cover_alt"])}">')

    tags = " &middot; ".join(esc(t) for t in post["tags"])

    # Up to three other posts for the "More from the blog" section.
    others = [p for p in all_posts if p["slug"] != post["slug"]][:3]
    more = ""
    if others:
        cards = "\n".join(post_card(p, "../") for p in others)
        more = f"""
    <section class="more-posts">
      <h2>More from the blog</h2>
      <div class="post-grid">
{cards}
      </div>
    </section>
"""

    return f"""<!DOCTYPE html>
<!-- GENERATED FILE: made by tools/build_blog.py from posts/{post['slug']}.md.
     Edit the .md file and run the script; changes made here get overwritten. -->
<html lang="en">
{head_html}
<body class="page-blog">
{header("../", "Blog")}

  <main class="blog-main">
    <article class="post">
      <header class="post-header">
        <h1>{esc(post["title"])}</h1>
        <p class="post-dek">{esc(post["description"])}</p>
        <p class="post-byline">
          <span>{series_label(post, "../") or "SEARCH Central Florida"}</span>
          <span><time datetime="{post["date"].isoformat()}">{nice_date(post["date"])}</time> &middot; {post["minutes"]} min read</span>
        </p>
      </header>
{hero}
      <!-- Tags on the left, Share button on the right. -->
      <div class="post-actions">
        <p class="post-tags">{tags}</p>
        <button class="share-button" type="button">Share</button>
      </div>

      <div class="post-body">
{post["body_html"]}
      </div>

    </article>
{more}  </main>

{footer("../")}
{series_tabs("../", post["series"])}

  <script>
    // The Share button. On phones, navigator.share opens the phone's own
    // share sheet (Messages, Instagram, etc). Browsers without it copy the
    // link instead, and the button says "Link copied!" for two seconds.
    const shareButton = document.querySelector(".share-button");
    shareButton.addEventListener("click", async function () {{
      const page = {{ title: document.title, url: location.href }};
      try {{
        if (navigator.share) {{
          await navigator.share(page);
        }} else {{
          await navigator.clipboard.writeText(page.url);
          shareButton.textContent = "Link copied!";
          setTimeout(function () {{ shareButton.textContent = "Share"; }}, 2000);
        }}
      }} catch (error) {{
        // Closing the share sheet without sharing counts as an error; ignore it.
      }}
    }});
  </script>
</body>
</html>
"""


def ticker(posts):
    """The moving strip under the header on the blog's list pages: the
    newest post titles, like the one on the mail club banner. The words are
    written twice so the loop has no gap. Longer text loops more slowly, so
    it always moves at the same speed."""
    text = "NEW ON THE BLOG \u2605 " + "".join(f"{esc(p['title'])} \u2605 " for p in posts[:5])
    text += "STORIES FROM CENTRAL FLORIDA \u2605 "
    seconds = max(20, round(len(text) / 3.2))
    return f"""  <!-- Moving ticker: the newest posts. Screen readers skip it (aria-hidden),
       since the same posts are listed below. -->
  <div class="ticker" aria-hidden="true">
    <div class="ticker-track" style="animation-duration: {seconds}s"><span>{text}</span><span>{text}</span></div>
  </div>"""


def build_listing(posts, prefix, title_text, intro, current, page_title, description, path, trail,
                  all_posts=()):
    """A list page: blog.html (all posts) or one series page.
    all_posts (newest first) fills the moving ticker.
    path is its address from the site root; trail is its breadcrumb trail."""
    if posts:
        lead = lead_story(posts[0], prefix)
        rest = "\n".join(post_card(p, prefix) for p in posts[1:])
        grid = f'\n    <div class="post-grid">\n{rest}\n    </div>' if rest else ""
        content = lead + grid
    else:
        content = '    <p class="blog-intro">no posts here yet. check back soon!</p>'
    return f"""<!DOCTYPE html>
<!-- GENERATED FILE: made by tools/build_blog.py. Edit posts/*.md and run the script. -->
<html lang="en">
{head(prefix, path, ROOT / path, page_title, description, "website", [seo.breadcrumbs(trail)])}
<body class="page-blog">
{header(prefix, "Blog")}
{ticker(all_posts)}

  <main class="blog-main">
    <h1 class="blog-title">{esc(title_text)}</h1>
    <p class="blog-intro">{esc(intro)}</p>

{content}
  </main>

{footer(prefix)}
{series_tabs(prefix, current)}
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
    SERIES_DIR.mkdir(exist_ok=True)

    for post in posts:
        (BLOG_DIR / f"{post['slug']}.html").write_text(build_post_page(post, posts), encoding="utf-8")
        print(f"built blog/{post['slug']}.html")

    (ROOT / "blog.html").write_text(build_listing(
        posts, "", "Blog", ALL_INTRO, "All",
        seo.full_title("Orlando Art & Culture Blog"),
        "Guides, local artist spotlights and snail mail club news from Search Central Florida, your hyperlocal Orlando arts and culture guide.",
        "blog.html", [("Home", ""), ("Blog", "blog.html")], posts), encoding="utf-8")
    print(f"built blog.html ({len(posts)} post{'' if len(posts) == 1 else 's'})")

    for name, slug, _, intro in SERIES:
        in_series = [p for p in posts if p["series"] == name]
        (SERIES_DIR / f"{slug}.html").write_text(build_listing(
            in_series, "../../", name, intro, name,
            seo.full_title(f"{name}: SEARCH Blog"),
            f"{name} posts from Search Central Florida: {intro}",
            f"blog/series/{slug}.html",
            [("Home", ""), ("Blog", "blog.html"), (name, f"blog/series/{slug}.html")], posts),
            encoding="utf-8")
        print(f"built blog/series/{slug}.html ({len(in_series)})")

    update_mailclub(posts)


if __name__ == "__main__":
    main()
