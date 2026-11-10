// supabase/functions/approve-event/index.ts
//
// Approves (publishes) a submitted event. Only the reviewer can use it.
// The review dashboard (admin.html) calls it when you press "Approve".
//
// What it does, in order:
//   1. Checks you're logged in AND on the reviewers list.
//   2. Looks up the event's address with Geocodio, so it gets a map pin.
//      (Skipped if there's no Geocodio key; the event still gets approved,
//      it just won't have a pin.)
//   3. Sets the event to "approved". It shows on the website right away.
//
// Secrets it needs (Supabase -> Edge Functions -> Secrets):
//   GEOCODIO_API_KEY   from geocod.io (optional, but needed for map pins)
// Supabase provides SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY by itself.
//
// Leave "Enforce JWT verification" ON for this function.

import { createClient } from "npm:@supabase/supabase-js@2.118.0";

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

// Ask Geocodio where an address is. Returns { lat, lng } or null.
async function geocode(address: string) {
  const key = Deno.env.get("GEOCODIO_API_KEY");
  if (!key) return null;
  const url = "https://api.geocod.io/v1.7/geocode?limit=1&q=" + encodeURIComponent(address) +
    "&api_key=" + encodeURIComponent(key);
  try {
    const result = await fetch(url).then((r) => r.json());
    const best = result.results?.[0];
    // Only trust confident matches (accuracy runs from 0 to 1).
    if (best && best.accuracy >= 0.7) return { lat: best.location.lat, lng: best.location.lng };
  } catch (error) {
    console.error("Geocoding failed:", error);
  }
  return null;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return reply(405, { error: "Use POST." });

  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

  // 1. Who's asking? The dashboard sends the logged-in reviewer's token.
  const token = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
  const { data: who } = await db.auth.getUser(token);
  const email = who?.user?.email?.toLowerCase();
  if (!email) return reply(401, { error: "Please log in again." });
  const { data: reviewer } = await db.from("reviewers").select("email").ilike("email", email).maybeSingle();
  if (!reviewer) return reply(403, { error: "This account isn't a reviewer." });

  const { id } = await req.json().catch(() => ({}));
  if (!id) return reply(400, { error: "Which event? (missing id)" });

  const { data: event, error: findError } = await db.from("events").select("*").eq("id", id).maybeSingle();
  if (findError || !event) return reply(404, { error: "That event wasn't found." });

  // 2. Find it on the map (unless it already has a spot).
  let latitude = event.latitude;
  let longitude = event.longitude;
  let geocoded = false;
  if (latitude == null || longitude == null) {
    const spot = await geocode(event.address);
    if (spot) {
      latitude = spot.lat;
      longitude = spot.lng;
      geocoded = true;
    }
  }

  // 3. Publish.
  const { error } = await db.from("events").update({
    status: "approved",
    reviewed_at: new Date().toISOString(),
    latitude,
    longitude,
  }).eq("id", id);
  if (error) return reply(500, { error: "Couldn't approve it just now. Please try again." });

  return reply(200, { ok: true, geocoded, onMap: latitude != null && longitude != null });
});
