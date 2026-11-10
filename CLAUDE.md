# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

`SCF_WEBSITE_BRIEF.md` is the full project brief for the Search Central Florida (SCF) website. It is the source of truth for the schema, page specs and validation rules. This file only summarizes it.

### Starter site (what exists today)

The owner asked for a simple interim starter site and set the brief's build phases aside for now. It is plain HTML, CSS and JS with **no build step**, served by GitHub Pages from `main` at the repo root (`.nojekyll` turns off Jekyll processing).

- The header logo is the white mascot head (`images/mascot-head-white.webp`) with the name typed in Courier Prime. The owner prefers the mascot over the cut-out-letter wordmark.
- **Design system** (the owner asked for the blog's look across the whole site; `style.css` is organized into 14 numbered sections, with a contents list at the top): plain paper background (`--paper`, no full-page halftone); Anton for headlines and Courier Prime (typewriter) for all body text, labels and buttons; Yellowtail script only for small accents such as the signature, the marquee and "hi friend!". Use thin rules instead of heavy boxes and shadows. Every page opens with a `.masthead` (a `.section-chip` label, a giant `h1` and `.masthead-intro`), and later sections start with `h2.section-head`. Each section has a colour set by a `<body>` class: `page-events` blue, `page-mailclub` pink, `page-about` yellow, and blog/home red (the default). This sets `--section` and `--section-text`. Cards (`.post-grid`/`.post-card`, used on home, blog and listings) have an image, an Anton title with a `.card-arrow`, a dashed-rule summary and a meta line; the whole card is clickable. Halftone dots and cut-and-paste touches (event card bands, the polka-dot envelope, washi `.taped` strips) are accents only. Brand artwork lives in `images/` as resized web copies of the owner's files.
- `index.html`, `events.html`, `mailclub.html`, `about.html` (hand-written) and the generated blog pages share one `style.css` and repeat the same header, nav and footer markup by hand. If you change the nav, change it in all four files.
- `mailclub.html` is the SEARCH snail mail club page. Its copy comes from the owners (Halley and Zach) and is deliberately lowercase; keep that voice. The FAQ uses `<details>`, so it needs no JS. The page uses the shared system plus cutesy mail touches: a scrolling script banner (`aria-hidden`), a red polka-dot envelope (`clip-path` flap) with a CSS collage of mail, taped notes, envelope **tabs** for the tiers (`role=tablist`; the inline script handles clicks and arrow keys), and lined-paper letters. Opening it with `?tier=sticker|print|curator` opens that envelope. Every Join button has `data-patreon`, and its address comes from the single `PATREON_URL` constant in the page's script. That constant is still a placeholder until the owner sends the real Patreon URL.
- **Mail club banner** (`banner.js`): a full-width, Shopify-style promo near the bottom of every page, outside `<main>`. It has a black ticker, a pink halftone banner (headline, black Join button, mascot print, "this month's artist" card) and three tier tiles linking to `mailclub.html?tier=…#tiers`. Pages include `<div data-mailclub-banner data-root="…"></div>` plus `<script src="…banner.js">`, where `data-root` is `""`, `"../"` or `"../../"`. The build script's `footer()` adds it to blog pages. **Each month, update `BANNER_SETTINGS` in `banner.js`** (month, artist, post, image). It replaced the per-page single mail club buttons and the blog's end-of-post box. Styles are in section 15 of `style.css`.
- `events.html` is laid out like a cinema showtimes page. Its inline script `fetch`es `events.json` and builds a 7-day strip (today plus the next six days). "Today" is computed in `America/New_York`, and dates are handled as `YYYY-MM-DD` strings at noon UTC so DST can't shift them. The chosen day is kept in `?day=YYYY-MM-DD` via `history.replaceState`. Cards are built with `textContent`. The card title is a `<button>` whose `::after` stretches over the whole card, and it opens a `<dialog>` with the enlarged card. Each event's `category` becomes a CSS class (`"Food and Drink"` → `.cat-food-and-drink`) that sets `--cat-colour` in `style.css`. Events outside the 7-day window are not shown.
- The `events.json` fields are `title`, `date`, `start_time`, optional `end_time`, `venue`, `category`, `description` and optional `link`. The link is the event's Instagram, ticket page or website. The card button label is chosen from the URL (Instagram / Tickets / Website); the link opens in a new tab and sits above the card's stretched button via `z-index`. The owner edits this file by hand or sends their weekly "events this week" Instagram slides for Claude to add. When adding events from slides, research each one for its own event page; if there is none, link the host's or venue's Instagram and tell the owner which events got venue links.
- The owner is learning from this code. Keep it simple and well commented.
- **Blog** (the owner chose "paste and I build": they send articles in chat and Claude publishes them):
  - Sources are `posts/<slug>.md`, Markdown with YAML front matter: `title`, `date`, `description`, `tags`, optional `series`, optional `cover` + `cover_alt`.
  - Run `python3 tools/build_blog.py` (needs `pip install markdown pyyaml`). It generates `blog/<slug>.html`, `blog.html` and one page per series in `blog/series/`. It also refreshes the list between the `PAST-MAILERS` markers in `mailclub.html` from posts with `series: Monthly Mail`.
  - Series are defined in the `SERIES` list at the top of the script, each with a name, file slug, colour and one-line intro. A post's `series` must be one of them. They are shown as the coloured tabs fixed to the bottom of every blog page.
  - Blog design (the model for the whole site): list pages show the newest post as a lead story, then a 1/2/3-column grid of cards. Post pages have a centred headline, a summary line, a byline rule, a hero image, a narrow reading column, a Share button and "More from the blog". Coloured series tabs are fixed to the bottom. Blog-only styles are in section 10 of `style.css`. Never hand-edit the generated files; change the `.md` or the script. The script fails on em dashes.
  - When the owner pastes an article, keep their wording and lowercase voice. You may add links, short `##` subheadings and a `<p class="event-callout">` for event details; tell them what you added. If the post mentions a dated event, offer to add it to `events.json`. Deleting a `.md` does not delete its old `blog/*.html`; remove that by hand.
  - The nav (Events, Mail Club, Blog, About) is duplicated in the four hand-written pages *and* in `header()` in the build script. Keep them in sync.
- To preview locally, run `python3 -m http.server` from the repo root. `fetch` does not work over `file://`.

The Astro plan below has not started yet. Once it does, add the real build, dev, lint and test commands here.

## Workflow rules from the brief

- Build in the seven phases listed at the end of the brief, in order: setup, events read side, submissions, reviewer dashboard, mail club, blog, home + SEO pass. **Stop after each phase for the owner to review.** Do not start the next phase without being asked.
- The owner is not a full-time developer. The README must explain Supabase setup, secrets, deploy, approving events and publishing a blog post in plain language.
- Respect the "Out of scope" list: no map UI (but store coordinates), event images, "SCF Pick" badge, category filters, store or multiple reviewers.

## Planned architecture

- **Astro, static output**, hosted on **GitHub Pages** and deployed with GitHub Actions. There is no server, so anything that needs a secret runs in **Supabase Edge Functions**:
  - `submit-event` verifies the Cloudflare Turnstile token, validates every field (the limits are in the brief's `events` table), and inserts the row with `status = 'pending'`.
  - `approve-event` is reviewer only. It geocodes the address with Geocodio, sets `status = 'approved'`, and triggers a rebuild through GitHub `repository_dispatch`.
- **The data flow is build-time.** The public site reads approved events from Supabase while it builds, and generates one static page per event at `/events/<date>-<slug>`. Content changes only after a rebuild. Rebuilds happen when an event is approved **and** on a daily cron shortly after midnight Eastern, so "Today" in the day strip stays correct. Keep both triggers in the deploy workflow.
- **Supabase RLS:** anonymous users have no direct table access. Submissions only go through `submit-event`. The build reads approved rows only, and the single reviewer account has full access. `submitter_email` must never reach any public page or build output.
- **Secrets** (Geocodio key, Turnstile secret, GitHub token) live only in Supabase secrets and GitHub Actions secrets, never in front-end code.
- **Blog** is a Markdown content collection (title, date, description, tags, series, cover image). Posts can embed event cards by slug. Event pages link back to the posts that feature them, so both directions need to resolve at build time.
- The **reviewer dashboard** is a client-side route protected by Supabase auth. Exclude it from the sitemap and robots, and mark it noindex.

## Conventions

- Eight fixed categories, each with its own accessible colour: Music, Art, Markets, Food and Drink, Film, Comedy, Community, Workshops. Define the palette once as design tokens and reuse it everywhere.
- Event cards are text only and must look the same on the events page, the submit form's live preview, the reviewer dashboard and blog embeds. Build them as one shared component.
- Day links use `/events?day=YYYY-MM-DD`. Dates are in Eastern time.
- Zine and grunge styling goes in headings, accents and backgrounds only. Body text and listings stay clean and readable.
- **Never use em dashes in site copy.**
- SEO: every page gets a unique title, meta description and Open Graph tags. JSON-LD uses `Event`, `BlogPosting`, `FAQPage` (mail club) and site-wide `Organization`.
- Placeholders are expected for content the owner will supply later: mascot and logo art, Patreon link and tiers, and FAQ answers.
