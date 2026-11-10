# Search Central Florida Website: Project Brief

You are building the website for Search Central Florida (SCF), a hyperlocal Orlando arts, culture and small business platform (Instagram: @searchcentralfl). The audience is mostly women aged 18 to 35 who love cool local events. SCF's brand is anti-digital and physical-first: the site should push people out the door, not keep them scrolling.

Read this whole brief before writing code. Build in the phases listed at the end, and stop after each phase so I can review.

## Goals

1. **Events calendar.** A curated, public calendar of approved local events. Instagram features four events per day; this site is where additional good events go, and where SCF sends anyone asking "can you post my event?"
2. **Event submissions.** Anyone can submit an event anonymously. Nothing goes public until I approve it.
3. **Mail club page.** One page that converts visitors into Patreon supporters of the SEARCH snail mail club.
4. **Blog.** Regular guides and curated series for SEO on Google and AI search tools, cross-linked with events and the mail club.

Top priorities: easy to use, looks great, and turns messy form data into polished, consistent event cards.

## Tech stack

- **Astro** for the site (static output, fast, SEO-friendly). Blog posts are Markdown files in an Astro content collection.
- **Supabase** for the events database, the submission inbox and the reviewer login.
- **GitHub Pages** for hosting, deployed with GitHub Actions.
- **Cloudflare Turnstile** to block bot submissions.
- **Geocodio** to turn approved event addresses into coordinates (stored now for a future map; no map is shown yet).
- Plain CSS or a light utility approach. Avoid heavy UI frameworks.

### How the pieces connect

- GitHub Pages only serves static files, so all secret-key work runs in **Supabase Edge Functions**:
  - `submit-event`: verifies the Turnstile token, validates every field against the rules below, and inserts the event with status `pending`.
  - `approve-event`: callable only by the reviewer. Geocodes the address with Geocodio, sets status `approved`, then triggers a site rebuild through GitHub's `repository_dispatch` API.
- Secrets (Geocodio key, Turnstile secret, GitHub token) live only in Supabase secrets and GitHub Actions secrets, never in front-end code.
- The site rebuilds when an event is approved **and** on a daily schedule shortly after midnight Eastern, so "Today" is always correct.
- Each approved event gets its own static page generated at build time, so search engines can index it.

### Database

Table `events`:

| Field | Type | Notes |
|---|---|---|
| id | uuid | primary key |
| status | text | `pending`, `approved` or `rejected` |
| title | text | required, max 60 characters |
| venue_name | text | required, max 60 characters |
| address | text | required, full street address |
| date | date | required, cannot be in the past |
| start_time | time | required |
| end_time | time | optional |
| category | text | required, one of the 8 categories below |
| short_description | text | required, max 200 characters |
| long_description | text | optional, max 1,000 characters |
| link | text | required, valid URL (tickets or more info) |
| instagram_handle | text | optional |
| submitter_email | text | optional, private, never shown publicly |
| latitude, longitude | numeric | filled in on approval |
| slug | text | generated from title and date |
| created_at, reviewed_at | timestamptz | |

Row-level security:
- Anonymous visitors cannot read or write the table directly; submissions only go through `submit-event`.
- The public build reads approved events only.
- The single reviewer account has full access.

## Categories

Eight fixed categories, each with its own colour used on cards and tags:

Music, Art, Markets, Food and Drink, Film, Comedy, Community, Workshops

Pick a palette that fits the zine look, with enough contrast for accessible text.

## Pages

### Events page (the heart of the site)

Inspired by cinema showtime sites:

- A horizontal **day strip** across the top: "Today" plus the next six days (seven total), showing weekday and date.
- Tapping a day slides the list below to that day's events.
- Desktop: all seven days visible. Mobile: about four visible, swipe for the rest. Design mobile first.
- Events listed by start time.
- Friendly empty state when a day has nothing yet, with a link to submit an event.
- Days are linkable (for example `/events?day=2026-11-14`) so I can share them.

**Event cards** (text only, no images, to keep things consistent):
- Category tag in its colour (the colour also accents the card)
- Title
- Venue name
- Time
- Short description

The whole card links to the event page.

### Event page

Keep it simple:
- Everything from the card, plus the full address, long description if provided, and the Instagram handle linked
- A clear button to the outside link (tickets or more info)
- Links to any blog posts that feature this event
- No add-to-calendar button
- Past events stay online, labelled as past

### Submit an event

- Opens with a short, friendly explanation in SCF's voice: we curate for the vibe of our audience, every event is reviewed by a person, and if it fits, we approve it. No guarantee of approval or of an Instagram feature.
- Form uses pickers and dropdowns wherever possible: date picker, time pickers, category dropdown.
- Required fields are clearly marked. Hard character limits with live counters.
- **Live preview:** as they type, they see exactly how their card will look on the site, updating in real time.
- Inline validation with plain-language error messages.
- Turnstile check before submit.
- A confirmation screen after submitting that explains what happens next.

### Reviewer dashboard

- Private route, protected by Supabase login. One reviewer account only, no roles needed.
- List of pending submissions, newest first, each shown as the card preview plus all fields.
- I can edit any field, then approve or reject.
- Approving runs `approve-event` (geocode, publish, rebuild).
- Simple tabs for pending, approved and rejected.
- Must work well on my phone.
- Keep this route out of search engines.

### Mail club page

One page whose job is converting visitors into Patreon supporters:
- **Hero** with a big sign-up call to action linking to Patreon.
- **Tabs** breaking down each subscriber tier, styled like stamped envelopes or postcards. Use placeholder tier content I will fill in.
- **Past mailers** strip linking to related blog posts.
- **FAQ** at the end (what's in a mailer, cost, when it arrives, shipping area, how to cancel). Placeholder answers I will fill in.
- Write headings and copy around phrases people search for, like "Orlando subscription box" and "snail mail club."

### Blog

- Markdown posts in a content collection with title, date, description, tags, series and cover image fields.
- Index page plus series pages so I can run recurring curated series.
- Posts can reference events by slug and show those event cards inline, so roundup posts like "This weekend in Orlando" pull in approved events and link to their pages.
- Mail club recap posts link back to the mail club page, and the mail club page links to them.
- Include one sample post and one sample series so I can see the pattern.

### Home page

A simple front door: a short intro to SCF, today's events preview, a mail club call to action, the latest blog posts and a link to submit an event.

## Look and feel

- Zine and grunge aesthetic matching SCF's Instagram: ransom-note style lettering for big headings, paper textures, a cut-and-paste feel.
- Keep body text clean and highly readable. The grunge lives in headings, accents and backgrounds, never in the listings.
- Room for the SEARCH mascot in the header or hero (I will supply artwork; leave a placeholder).
- Fast and lightweight. Good accessibility: colour contrast, keyboard navigation, alt text, labelled form fields.
- **Copy style: never use em dashes** anywhere in site copy.

## SEO

- Unique titles and meta descriptions on every page.
- JSON-LD structured data: `Event` on event pages, `BlogPosting` on posts, `FAQPage` on the mail club page, `Organization` site-wide.
- Sitemap and robots.txt (excluding the dashboard).
- Open Graph tags for nice link previews.
- Clean URLs such as `/events/2026-11-14-jazz-night-at-the-venue`.

## Build phases

Stop after each phase so I can review it.

1. **Setup:** Astro project, folder structure, design tokens (colours, fonts, category palette), base layout, GitHub Pages deploy working.
2. **Events, read side:** Supabase schema and security rules, seed data with sample events across all eight categories and the next seven days, events page with day strip, cards and event pages.
3. **Submissions:** submit page with live preview, Turnstile and the `submit-event` function.
4. **Reviewer dashboard:** login, review list, edit, approve and reject, `approve-event` function with geocoding and the rebuild trigger, plus the daily scheduled rebuild.
5. **Mail club page.**
6. **Blog:** content collection, index, series pages, event embeds, sample post.
7. **Home page and SEO pass:** structured data, sitemap, meta tags, final accessibility and mobile check.

Also write a short README explaining how to set up Supabase, add secrets, deploy, approve events and publish a blog post, written for someone who is not a full-time developer.

## Out of scope for now

- The interactive map (planned later as a separate, standalone browsing tool; just store coordinates)
- Event images
- An "SCF Pick" badge for Instagram-featured events
- Category filters
- An online store
- Multiple reviewer accounts

## Things I will provide

- Patreon link and tier details
- FAQ answers
- SEARCH mascot artwork and logo files
- Supabase, Geocodio and Cloudflare accounts and keys
- A custom domain later (start on the default GitHub Pages address)
