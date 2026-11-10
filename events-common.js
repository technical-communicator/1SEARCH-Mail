// events-common.js: event code shared by several pages.
//
//  - the events page (events.html)
//  - the home page's "Today in Orlando" (index.html)
//  - the submit form's live preview (submit.html)
//  - the review dashboard (admin.html)
//
// It has three jobs:
//  1. Small helpers for dates and times.
//  2. buildEventCard(): makes ONE event card. Every page uses it, so the
//     cards always look the same everywhere.
//  3. loadEvents(): loads the events from events.json AND the approved
//     submissions from Supabase, and puts them in one list.

// The eight main categories, in order.
const CATEGORIES = ["Music", "Art", "Markets", "Food and Drink", "Film", "Comedy", "Community", "Workshops"];

// ---------- 1. Date and time helpers ----------

// Today's date in Orlando, as "YYYY-MM-DD".
// We ask for Eastern time on purpose, so "Today" is right even if
// someone in another time zone visits. ("en-CA" formats dates as YYYY-MM-DD.)
function todayInOrlando() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
}

// Turn "YYYY-MM-DD" into a Date object at noon UTC. Using noon (and UTC)
// means daylight saving time can never nudge it into the wrong day.
function toDate(isoDate) {
  return new Date(isoDate + "T12:00:00Z");
}

// Add some number of days to a "YYYY-MM-DD" date.
function addDays(isoDate, days) {
  const date = toDate(isoDate);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10); // back to "YYYY-MM-DD"
}

// Format a "YYYY-MM-DD" date in different ways, e.g.
// { weekday: "short" } gives "Sat", { day: "numeric" } gives "14".
function formatDate(isoDate, options) {
  return toDate(isoDate).toLocaleDateString("en-US", { timeZone: "UTC", ...options });
}

// Turn "19:30" (24-hour time) into "7:30 PM".
function formatTime(timeText) {
  const [hours, minutes] = timeText.split(":").map(Number);
  const suffix = hours >= 12 ? "PM" : "AM";
  const hours12 = hours % 12 || 12; // 0 becomes 12, 13 becomes 1, and so on
  return hours12 + ":" + String(minutes).padStart(2, "0") + " " + suffix;
}

// Small helper: make an element with a class and some text.
// We always use textContent (never innerHTML) so text from events.json
// or from a submitted form is shown as plain text and can never break
// the page.
function make(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

// "Food and Drink" becomes "cat-food-and-drink", the CSS class that
// colours the card (see the category colours in style.css).
function categoryClass(category) {
  return "cat-" + String(category || "").toLowerCase().replace(/\s+/g, "-");
}

// ---------- 2. The event card ----------

// The time "chips", like showtime buttons: "8:00 PM" and "until 11:00 PM".
function makeTimes(event) {
  const times = make("div", "times");
  if (event.start_time) times.append(make("span", "time-chip", formatTime(event.start_time)));
  if (event.end_time) {
    times.append(make("span", "time-until", "until " + formatTime(event.end_time)));
  }
  return times;
}

// Each event can have a "link": its Instagram, ticket page or website.
// This picks a short button label from the address.
function linkLabel(url) {
  if (url.includes("instagram.com")) return "Instagram";
  if (url.includes("eventbrite.") || url.includes("ticket")) return "Tickets";
  return "Website";
}

// Make the link button, or return null if the event has no link.
// target="_blank" opens it in a new tab so the calendar stays open.
// rel="noopener" is a standard safety setting for links to other sites.
function makeLink(event, className) {
  if (!event.link) return null;
  const link = make("a", className, linkLabel(event.link) + " ↗"); // ↗ is the ↗ arrow
  link.href = event.link;
  link.target = "_blank";
  link.rel = "noopener";
  // Screen readers hear the full meaning, e.g. "Tasty Takeover: Instagram, opens in a new tab".
  link.setAttribute("aria-label", event.title + ": " + linkLabel(event.link) + ", opens in a new tab");
  return link;
}

// Build one event card.
//   event: an event object (title, venue, category, description, times, link)
//   onOpen: optional. If given, the title becomes a button that calls
//           onOpen(button) when clicked (the events page uses this to open
//           the big pop-up). CSS stretches that button over the whole card.
function buildEventCard(event, onOpen) {
  const card = make("article", "event-card " + categoryClass(event.category));

  // Top half: coloured band with category, title and venue.
  const top = make("div", "card-top");
  const title = make("h3");
  if (onOpen) {
    const openButton = make("button", "card-open", event.title);
    openButton.type = "button";
    openButton.addEventListener("click", function () { onOpen(openButton); });
    title.append(openButton);
  } else {
    title.textContent = event.title;
  }
  top.append(make("span", "event-category", event.category), title, make("p", "event-venue", event.venue));

  // Bottom half: short description, time chips, then a row with the
  // event's link (if it has one) and a "Details" hint.
  const footer = make("div", "card-footer");
  const link = makeLink(event, "event-link");
  if (link) footer.append(link);
  if (onOpen) footer.append(make("span", "card-details", "Details"));

  const bottom = make("div", "card-bottom");
  bottom.append(make("p", "event-description", event.description), makeTimes(event), footer);

  card.append(top, bottom);
  return card;
}

// ---------- 3. Loading the events ----------

// Is Supabase set up in config.js?
function supabaseIsSetUp() {
  const config = window.SCF_CONFIG || {};
  return Boolean(config.supabaseUrl && config.supabaseAnonKey);
}

// Approved submissions use the database's field names. This turns one
// into the same shape as the events in events.json.
function fromDatabase(row) {
  return {
    id: row.id,
    title: row.title,
    date: row.date,
    start_time: String(row.start_time).slice(0, 5),   // "18:30:00" -> "18:30"
    end_time: row.end_time ? String(row.end_time).slice(0, 5) : undefined,
    venue: row.venue_name,
    address: row.address,
    category: row.category,
    description: row.short_description,
    long_description: row.long_description || undefined,
    link: row.link,
    instagram: row.instagram_handle || undefined,
    lat: row.latitude != null ? Number(row.latitude) : undefined,
    lng: row.longitude != null ? Number(row.longitude) : undefined,
  };
}

// Load every event: the ones in events.json, plus approved submissions
// from Supabase (if it's set up). If Supabase can't be reached, the
// calendar still shows the events.json ones.
async function loadEvents(root) {
  root = root || "";
  const response = await fetch(root + "events.json");
  if (!response.ok) throw new Error("Could not load events.json (status " + response.status + ")");
  const events = await response.json();

  if (supabaseIsSetUp()) {
    try {
      const config = window.SCF_CONFIG;
      // "public_events" only ever contains approved events, and never the
      // submitter's private email (see supabase/schema.sql).
      const result = await fetch(config.supabaseUrl + "/rest/v1/public_events?select=*", {
        headers: { apikey: config.supabaseAnonKey },
      });
      if (result.ok) {
        const rows = await result.json();
        rows.forEach(function (row) { events.push(fromDatabase(row)); });
      } else {
        console.warn("Couldn't load submitted events (status " + result.status + ")");
      }
    } catch (error) {
      console.warn("Couldn't load submitted events:", error);
    }
  }
  return events;
}
