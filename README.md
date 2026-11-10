# Search Central Florida website

The website for Search Central Florida (SCF): the Orlando events calendar,
SEARCH: a snail mail club, and the blog.

It's a plain website (HTML, CSS and JavaScript) hosted free on GitHub Pages.
Every time a change is saved to the `main` branch, GitHub publishes it
within a minute or two.

---

## Turning on event submissions (one-time setup, about 30 minutes)

Visitors can send in events at **submit.html** without making an account.
Each one waits for you to review it at **admin.html**. Once you approve it,
it appears on the calendar and the map straight away.

To make that work, the site needs three free services:

| Service | What it does | Cost |
| --- | --- | --- |
| **Supabase** | Stores submitted events and your reviewer login | Free plan |
| **Cloudflare Turnstile** | The "I'm not a robot" spam check on the form | Free |
| **Geocodio** | Finds each approved address on the map | Free up to 2,500 a day |

Until you finish these steps, the calendar keeps working from
`events.json`, and the submit form shows a friendly "not open yet" message.

### Step 1: Create the Supabase project

1. Go to [supabase.com](https://supabase.com), sign up and click **New project**.
   Name it something like `search-central-florida` and pick the US East region.
   Save the database password somewhere safe (you won't need it day to day).
2. When it's ready, open **SQL Editor**, click **New query**, and paste in
   everything from [`supabase/schema.sql`](supabase/schema.sql).
3. Near the bottom of what you pasted, change `your-email@example.com` to the
   email you'll log in with. Then click **Run**. You should see "Success".

### Step 2: Create your reviewer login

1. In Supabase, go to **Authentication → Users → Add user → Create new user**.
2. Use the **same email** as in Step 1, choose a strong password, and tick
   **Auto Confirm User**.
3. Go to **Authentication → Sign In / Providers** (sometimes called
   "Providers" or "Settings") and turn **off** "Allow new users to sign up".
   This way, nobody else can make an account. (Even if they could, only the
   email from Step 1 can review events.)

### Step 3: Set up the spam check (Cloudflare Turnstile)

1. Sign up at [cloudflare.com](https://dash.cloudflare.com/sign-up) (free) and
   open **Turnstile** in the menu. Click **Add widget**.
2. Name it `SCF submit form`. Under hostnames, add
   `technical-communicator.github.io` (and `localhost` if you want to test
   on your own computer). Leave the widget mode as **Managed**.
3. You'll get two keys:
   - a **Site Key** (public: it goes in `config.js` in Step 7)
   - a **Secret Key** (private: it goes in Supabase in Step 6)

### Step 4: Get a Geocodio key (for map pins)

1. Sign up at [geocod.io](https://www.geocod.io) (free).
2. Under **API Keys**, create a key and copy it. It's private: it goes in
   Supabase in Step 6.

(You can skip this. Approved events will still show on the calendar, just
without a map pin. You can also type a pin's latitude and longitude in by
hand on the review page.)

### Step 5: Add the two server functions

These small programs run on Supabase's servers, where secret keys are safe.

1. In Supabase, open **Edge Functions → Deploy a new function → Via Editor**.
2. Name it exactly `submit-event`. Delete the sample code, paste in everything
   from [`supabase/functions/submit-event/index.ts`](supabase/functions/submit-event/index.ts),
   and click **Deploy**.
3. Open the function's **Details** (or settings) and turn **off**
   **Enforce JWT verification** ("Verify JWT"). This one must be off, because
   people submitting events don't log in.
4. Do the same for a second function named exactly `approve-event`, pasting in
   [`supabase/functions/approve-event/index.ts`](supabase/functions/approve-event/index.ts).
   For this one, leave **Enforce JWT verification ON**.

(If you're comfortable with the command line, `supabase functions deploy`
does the same thing using [`supabase/config.toml`](supabase/config.toml).)

### Step 6: Add the secret keys to Supabase

In **Edge Functions → Secrets**, add:

| Name | Value |
| --- | --- |
| `TURNSTILE_SECRET_KEY` | the Turnstile **Secret Key** from Step 3 |
| `GEOCODIO_API_KEY` | your Geocodio key from Step 4 |
| `ALLOWED_ORIGIN` | `https://technical-communicator.github.io` (optional: only lets your own site use the functions) |

**These keys never go in the website's files.**

### Step 7: Connect the website (`config.js`)

1. In Supabase, go to **Project Settings → API** (or **API Keys**). Copy:
   - the **Project URL** (looks like `https://abcdefgh.supabase.co`)
   - the **anon** key (or the **publishable** key, starting `sb_publishable_`)
2. On GitHub, open `config.js`, click the pencil (Edit) icon, and fill in:

   ```js
   window.SCF_CONFIG = {
     supabaseUrl: "https://abcdefgh.supabase.co",
     supabaseAnonKey: "your anon or publishable key",
     turnstileSiteKey: "your Turnstile Site Key",
   };
   ```

3. Click **Commit changes**. These three are *meant* to be public, so it's
   fine for them to be in the website. Never paste the `service_role` /
   secret key, the Turnstile secret or the Geocodio key here.

### Step 8: Try it

1. Wait a minute or two for GitHub to publish, then open the site's
   **submit.html**, fill in a test event for a date this week, and send it.
2. Open **admin.html** (it isn't linked from the site, so bookmark it), log in,
   and you'll see it under **Pending**. Click **Approve & publish**.
3. Open the events page: your test event is on the calendar and the map.
   Back on admin.html you can **Unpublish** it when you're done.

---

## Day to day

**Reviewing submissions.** Go to `admin.html` and log in. Under **Pending**,
each submission shows its card next to all of its details.

- Fix anything you like (typos, a better description) and the card updates as you type.
- **Approve & publish** saves your edits, finds the address on the map, and puts it on the calendar.
- **Reject** hides it. You can still find it under **Rejected** and approve it later.
- **Unpublish** takes an approved event back off the calendar.

The submitter's email (if they gave one) only ever shows here, never on the site.

**Adding events yourself.** You can still add events straight to
`events.json` (or send your weekly slides to Claude to do it). Both kinds
show on the calendar together.

**Publishing a blog post.** Send the article (and any pictures) to Claude,
which turns it into a page and publishes it.

**If a GitHub deploy fails** with "No artifacts named github-pages", it's a
temporary GitHub problem. Go to the **Actions** tab, open the failed run,
and click **Re-run all jobs** (or just save any new change).

---

## How the files fit together

| File | What it is |
| --- | --- |
| `index.html`, `events.html`, `mailclub.html`, `about.html` | The main pages |
| `submit.html` | The public "submit an event" form |
| `admin.html` | Your private review dashboard |
| `events.json` | Events you add by hand |
| `events-common.js` | Shared event code: the event card, and loading events from `events.json` plus approved submissions |
| `config.js` | The three public connection settings (Step 7) |
| `banner.js` | The mail club banner at the bottom of each page (update it monthly) |
| `mailers.json` | Past mail club features (artist + business by month) |
| `style.css` | All the styles, in numbered sections |
| `posts/`, `tools/build_blog.py` | Blog posts and the script that builds the blog pages |
| `supabase/` | The database setup and the two server functions |
| `vendor/` | Copies of the map library (Leaflet) and the Supabase library |
