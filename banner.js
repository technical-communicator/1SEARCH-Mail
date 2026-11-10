// banner.js: the full-width SEARCH snail mail club banner.
//
// Its pictures use loading="lazy", so phones only download them when the
// visitor scrolls near the banner.
//
// It appears near the bottom of every page, like a shop's promo banner:
//   1. a black ticker strip with scrolling news
//   2. a big pink banner with a headline, a Join button and this month's artist
//   3. a row of colour tiles, one per tier
//
// EACH MONTH, update the settings just below (the month, artist, post and
// picture). Every page on the site uses this one file, so that's the only
// place you need to change.
//
// HOW IT GETS ONTO A PAGE: the page has an empty
//   <div data-mailclub-banner data-root=""></div>
// and loads this file. The script fills that div in. "data-root" says how
// to get back to the site's main folder: "" for pages in the main folder,
// "../" for blog posts, "../../" for blog section pages.

const BANNER_SETTINGS = {
  month: "november",
  artist: "Xine Hann",
  artistPost: "blog/featured-artist-xine-hann.html",
  artistImage: "images/blog/xine-hann-collage.webp",
  // The artwork shown big on the banner: this month's print and a sticker.
  // (Small copies, about 460px and 280px wide, so phones load them fast.)
  printImage: "images/mailer/xine-print-small.webp",
  // The small card on the banner shows this month's local business perk.
  perk: "Florida Coffee Fest",
  perkPost: "blog/featured-business-florida-coffee-festival.html",
  perkImage: "images/mailer/coffee-fest-thumb.webp",  // a small copy, it shows tiny
  stickerImage: "images/mailer/xine-sticker-flowers-small.webp",
};

// The ticker's words. They're written twice so the loop has no gap.
const TICKER_TEXT =
  "NEW! " + BANNER_SETTINGS.month.toUpperCase() + " MAILER FT. " + BANNER_SETTINGS.artist.toUpperCase() +
  " ★ ART IN YOUR MAILBOX ★ FROM $6.99/MONTH ★ $450 GIVEN TO LOCAL ARTISTS ★ ";
// (★ is a ★ star.   is a space that doesn't disappear at the end.)

// The three tiers, shown as colour tiles. "id" matches the envelope tabs on
// mailclub.html, so a tile opens the mail club page with that tier chosen.
const TIERS = [
  { id: "sticker", name: "Sticker supporter", price: "$6.99/mo", colour: "pink" },
  { id: "print", name: "Print collector", price: "$8.99/mo", colour: "blue" },
  { id: "curator", name: "Print & sticker curator", price: "$12.99/mo", colour: "yellow" },
];

function buildMailclubBanner(spot) {
  const root = spot.dataset.root || "";

  // Each tier tile is a link to the mail club page, e.g.
  // mailclub.html?tier=print#tiers  ("#tiers" scrolls to the envelopes).
  const tiles = TIERS.map(function (tier) {
    return (
      '<a class="mcb-tile series-' + tier.colour + '" href="' + root + "mailclub.html?tier=" + tier.id + '#tiers">' +
        '<span class="mcb-tile-name">' + tier.name + "</span>" +
        '<span class="mcb-tile-price">' + tier.price + "</span>" +
      "</a>"
    );
  }).join("");

  // All the text here is written by us (not typed in by visitors),
  // so it's safe to build the banner as one piece of HTML.
  spot.innerHTML =
    '<section class="mcb" aria-label="SEARCH: a snail mail club">' +
      '<div class="mcb-ticker" aria-hidden="true">' +
        '<div class="mcb-ticker-track"><span>' + TICKER_TEXT + "</span><span>" + TICKER_TEXT + "</span></div>" +
      "</div>" +

      '<div class="mcb-main">' +
        '<div class="mcb-inner">' +
          '<div class="mcb-text">' +
            '<p class="mcb-eyebrow">SEARCH: a snail mail club</p>' +
            '<h2 class="mcb-title">Art in your mailbox, every month.</h2>' +
            '<p class="mcb-sub">a new central florida artist every month, plus perks from local businesses. from $6.99 a month.</p>' +
            '<a class="button mcb-button" href="' + root + 'mailclub.html#tiers">Join the club</a>' +
          "</div>" +

          '<div class="mcb-visual">' +
            '<span class="mcb-sparkle mcb-sparkle-1" aria-hidden="true">✦</span>' +
            '<span class="mcb-sparkle mcb-sparkle-2" aria-hidden="true">✦</span>' +
            '<a href="' + root + BANNER_SETTINGS.artistPost + '" aria-label="' + BANNER_SETTINGS.month + "'s artist: " + BANNER_SETTINGS.artist + '">' +
              '<img loading="lazy" decoding="async" class="mcb-print" src="' + root + BANNER_SETTINGS.printImage + '" alt="" width="700" height="990">' +
            "</a>" +
            '<img loading="lazy" decoding="async" class="mcb-sticker" src="' + root + BANNER_SETTINGS.stickerImage + '" alt="" width="400" height="474">' +
            // The small "this month's perk" card, like a product card on a shop banner.
            '<a class="mcb-card" href="' + root + BANNER_SETTINGS.perkPost + '">' +
              '<img loading="lazy" decoding="async" src="' + root + BANNER_SETTINGS.perkImage + '" alt="">' +
              '<span class="mcb-card-label">' + BANNER_SETTINGS.month + "'s perk</span>" +
              '<span class="mcb-card-name">' + BANNER_SETTINGS.perk + " &rarr;</span>" +
            "</a>" +
          "</div>" +
        "</div>" +
      "</div>" +

      '<nav class="mcb-tiles" aria-label="Mail club tiers">' + tiles + "</nav>" +
    "</section>";
}

// Fill in every banner spot on the page (there's normally just one).
document.querySelectorAll("[data-mailclub-banner]").forEach(buildMailclubBanner);
