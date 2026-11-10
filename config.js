// config.js: the site's connection settings.
//
// Fill these in once, after setting up Supabase and Cloudflare Turnstile
// (the README explains where to find each one). Until they're filled in,
// the calendar still works from events.json, and the submit form shows a
// friendly "not open yet" message instead of sending.
//
// These three values are PUBLIC on purpose: they're meant to be in the
// web page, and they can't be used to read private data or approve events.
// NEVER put the "service_role" / "secret" key, the Turnstile secret key or
// the Geocodio key in this file. Those go in Supabase's secret settings.

window.SCF_CONFIG = {
  // Supabase: Project Settings -> API (or "API Keys").
  supabaseUrl: "",       // looks like "https://abcdefgh.supabase.co"
  supabaseAnonKey: "",   // the "anon" / "publishable" key

  // Cloudflare Turnstile (the spam check): your widget's "Site Key".
  turnstileSiteKey: "",
};
