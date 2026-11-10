// supabase/functions/submit-event/index.ts
//
// Receives an event from the website's submit form and saves it as
// "pending" for review. It runs on Supabase's servers, so it can safely
// use secret keys.
//
// What it does, in order:
//   1. Checks the Cloudflare Turnstile spam test.
//   2. Checks every field (the same rules as the form).
//   3. Saves the event with status "pending".
//
// Secrets it needs (Supabase -> Edge Functions -> Secrets):
//   TURNSTILE_SECRET_KEY   from Cloudflare Turnstile
// Supabase provides SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY by itself.
//
// IMPORTANT: turn OFF "Enforce JWT verification" (verify JWT) for this
// function, because people submitting events don't log in.

import { createClient } from "npm:@supabase/supabase-js@2.118.0";

const CATEGORIES = ["Music", "Art", "Markets", "Food and Drink", "Film", "Comedy", "Community", "Workshops"];

// Lets the website (on a different address) call this function.
const CORS = {
  "Access-Control-Allow-Origin": Deno.env.get("ALLOWED_ORIGIN") ?? "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function reply(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

// Today's date in Orlando, "YYYY-MM-DD".
function todayInOrlando() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
}

// "Jazz Night at the Venue!" -> "jazz-night-at-the-venue"
function slugify(text: string) {
  return text.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
}

// Trim a value to text (or "" if it's missing).
function clean(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

// Check every field. Returns { field: "plain-language problem" }.
function validate(e: Record<string, string>) {
  const errors: Record<string, string> = {};
  const need = (field: string, label: string) => { if (!e[field]) errors[field] = `Please add ${label}.`; };
  const max = (field: string, limit: number) => {
    if (e[field] && e[field].length > limit) errors[field] = `Please keep this under ${limit} characters.`;
  };

  need("title", "the event's name");
  max("title", 60);
  need("venue_name", "the venue's name");
  max("venue_name", 60);
  need("address", "the full street address");
  if (e.address && e.address.length < 5) errors.address = "Please add the full street address.";
  max("address", 200);

  if (!/^\d{4}-\d{2}-\d{2}$/.test(e.date)) errors.date = "Please pick a date.";
  else if (e.date < todayInOrlando()) errors.date = "This date has already passed.";

  if (!/^\d{2}:\d{2}$/.test(e.start_time)) errors.start_time = "Please pick a start time.";
  if (e.end_time && !/^\d{2}:\d{2}$/.test(e.end_time)) errors.end_time = "Please pick a valid end time.";

  if (!CATEGORIES.includes(e.category)) errors.category = "Please choose a category.";

  need("short_description", "a short description");
  max("short_description", 200);
  max("long_description", 1000);

  if (!/^https?:\/\/[^\s.]+\.[^\s]+$/i.test(e.link)) errors.link = "Please add a full web address, starting with https://";
  max("link", 500);

  if (e.instagram_handle && !/^@?[A-Za-z0-9._]{1,30}$/.test(e.instagram_handle)) {
    errors.instagram_handle = "Instagram handles use letters, numbers, dots and underscores.";
  }
  if (e.submitter_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.submitter_email)) {
    errors.submitter_email = "That email address doesn't look right.";
  }
  return errors;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return reply(405, { error: "Use POST." });

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return reply(400, { error: "Something went wrong sending the form. Please try again." });
  }

  // A hidden "website" field that people never see. Bots fill it in.
  // Pretend it worked, so the bot doesn't learn anything.
  if (clean(body.website)) return reply(200, { ok: true });

  // 1. The spam test.
  const secret = Deno.env.get("TURNSTILE_SECRET_KEY");
  if (!secret) return reply(500, { error: "Submissions aren't set up yet (missing spam check key)." });
  const check = new FormData();
  check.append("secret", secret);
  check.append("response", clean(body.turnstileToken));
  const ip = req.headers.get("CF-Connecting-IP") ?? req.headers.get("x-forwarded-for");
  if (ip) check.append("remoteip", ip.split(",")[0].trim());
  const verdict = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    body: check,
  }).then((r) => r.json()).catch(() => ({ success: false }));
  if (!verdict.success) {
    return reply(400, { error: "The spam check didn't go through. Please try it again." });
  }

  // 2. Check the fields.
  const event: Record<string, string> = {
    title: clean(body.title),
    venue_name: clean(body.venue_name),
    address: clean(body.address),
    date: clean(body.date),
    start_time: clean(body.start_time).slice(0, 5),
    end_time: clean(body.end_time).slice(0, 5),
    category: clean(body.category),
    short_description: clean(body.short_description),
    long_description: clean(body.long_description),
    link: clean(body.link),
    instagram_handle: clean(body.instagram_handle).replace(/^@/, ""),
    submitter_email: clean(body.submitter_email),
  };
  const errors = validate(event);
  if (Object.keys(errors).length) return reply(400, { errors });

  // 3. Save it as pending. The service role key lets this function write
  // to the table even though the public can't.
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { error } = await db.from("events").insert({
    ...event,
    end_time: event.end_time || null,
    long_description: event.long_description || null,
    instagram_handle: event.instagram_handle || null,
    submitter_email: event.submitter_email || null,
    status: "pending",
    // e.g. "2026-11-14-jazz-night-at-the-venue-k3f9"
    slug: `${event.date}-${slugify(event.title)}-${crypto.randomUUID().slice(0, 4)}`,
  });
  if (error) {
    console.error(error);
    return reply(500, { error: "We couldn't save your event just now. Please try again in a few minutes." });
  }
  return reply(200, { ok: true });
});
