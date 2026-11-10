# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

`SCF_WEBSITE_BRIEF.md` is the full project brief for the Search Central Florida (SCF) website. It is the source of truth for the schema, page specs and validation rules. This file only summarizes it.

### Starter site (what exists today)

The owner asked for a simple interim starter site and set the brief's build phases aside for now. It is plain HTML, CSS and JS with **no build step**, served by GitHub Pages from `main` at the repo root (`.nojekyll` turns off Jekyll processing).

- Brand artwork lives in `images/` (resized web copies of the owner's files). The palette tokens at the top of `style.css` come from it: cherry red, yellow, pink and blue halftone, hood purple, cream paper and black ink. Each page picks its halftone background with a `<body>` class (`page-blue`, `page-pink`; yellow is the default).
- `index.html`, `about.html` and `events.html` share one `style.css` and repeat the same header, nav and footer markup by hand. If you change the nav, change it in all three files.
- `events.html` has an inline script that `fetch`es `events.json`, sorts by `date` + `start_time` (string compare on `YYYY-MM-DD` / `HH:MM`), and builds the cards with `textContent`. Each event's `category` becomes a CSS class (`"Food and Drink"` → `.cat-food-and-drink`) that sets `--cat-colour` in `style.css`.
- The `events.json` fields are `title`, `date`, `start_time`, optional `end_time`, `venue`, `category` and `description`. The owner edits this file by hand.
- The owner is learning from this code. Keep it simple and well commented.
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
