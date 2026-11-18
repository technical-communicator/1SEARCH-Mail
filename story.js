// story.js: the "Share to your story" maker for the mail club.
//
// It draws a 1080 x 1920 picture (the size of an Instagram story) about
// THIS MONTH's mail club issue: the artist's print with its two stickers
// and the club's blue stamp, the headline, and the "join by" date.
// Everything comes from BANNER_SETTINGS in banner.js, so it updates on its
// own each month. Visitors pick one of the four brand backgrounds, then
// download the picture or share it straight to an app on their phone.
//
// banner.js loads this file the first time someone taps the button.

(function () {
  const W = 1080, H = 1920;   // Instagram story size, in pixels

  // The four brand backgrounds. "ink" is the text colour that reads well on it.
  const BACKGROUNDS = [
    { id: "red",    name: "Cherry red", image: "images/bg-red.webp",    colour: "#8a0f26", ink: "#ffffff" },
    { id: "pink",   name: "Pink",       image: "images/bg-pink.webp",   colour: "#f3769b", ink: "#1a1a1a" },
    { id: "blue",   name: "Blue",       image: "images/bg-blue.webp",   colour: "#87d1ff", ink: "#1a1a1a" },
    { id: "yellow", name: "Yellow",     image: "images/bg-yellow.webp", colour: "#fdd94c", ink: "#1a1a1a" },
  ];

  const S = BANNER_SETTINGS;   // from banner.js

  // The border styles. Each "under" draws the border and returns how far in
  // (in pixels) the coloured part starts; "over" (optional) draws on top at
  // the end. Pick one with storyFrame in BANNER_SETTINGS (banner.js).
  const INK = "#1a1a1a", CREAM = "#f6f1e7";
  const FRAMES = {
    // A postage stamp: dark backdrop, cream paper with bitten edges.
    stamp: {
      under: function (ctx) {
        const EDGE = 26, HOLE = 13;
        ctx.fillStyle = INK;
        ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = CREAM;
        ctx.fillRect(EDGE, EDGE, W - 2 * EDGE, H - 2 * EDGE);
        ctx.fillStyle = INK;
        const w = W - 2 * EDGE, h = H - 2 * EDGE;
        const across = Math.round(w / 44), down = Math.round(h / 44);
        function bite(x, y) { ctx.beginPath(); ctx.arc(x, y, HOLE, 0, Math.PI * 2); ctx.fill(); }
        for (let i = 0; i <= across; i++) { bite(EDGE + i * w / across, EDGE); bite(EDGE + i * w / across, H - EDGE); }
        for (let i = 0; i <= down; i++) { bite(EDGE, EDGE + i * h / down); bite(W - EDGE, EDGE + i * h / down); }
        return 60;
      },
    },
    // An airmail envelope: red and blue diagonal stripes around the edge.
    airmail: {
      under: function (ctx) {
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, W, H);
        ctx.save();
        ctx.beginPath();
        ctx.rect(0, 0, W, H);
        ctx.rect(44, 44, W - 88, H - 88);
        ctx.clip("evenodd");                       // only the outer band
        const colours = ["#c8102e", "#ffffff", "#1f4e8c", "#ffffff"];
        for (let i = -H, k = 0; i < W + H; i += 44, k++) {
          ctx.fillStyle = colours[k % 4];
          ctx.beginPath();
          ctx.moveTo(i, 0); ctx.lineTo(i + 44, 0); ctx.lineTo(i + 44 - H, H); ctx.lineTo(i - H, H);
          ctx.fill();
        }
        ctx.restore();
        return 62;
      },
    },
    // A clean white border, like the art prints themselves.
    print: {
      under: function (ctx) {
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, W, H);
        return 56;
      },
    },
    // Cream paper with strips of washi tape on the corners.
    tape: {
      under: function (ctx) {
        ctx.fillStyle = CREAM;
        ctx.fillRect(0, 0, W, H);
        return 60;
      },
      over: function (ctx) {
        function strip(x, y, turn, colour) {
          ctx.save();
          ctx.translate(x, y);
          ctx.rotate(turn * Math.PI / 180);
          ctx.fillStyle = colour;
          ctx.fillRect(-170, -42, 340, 84);
          ctx.restore();
        }
        strip(70, 70, -40, "rgba(243, 118, 155, 0.9)");      // pink
        strip(W - 70, 70, 40, "rgba(135, 209, 255, 0.9)");   // blue
        strip(70, H - 70, 40, "rgba(253, 217, 76, 0.92)");   // yellow
        strip(W - 70, H - 70, -40, "rgba(243, 118, 155, 0.9)");
      },
    },
    // A strip of 35mm film: black edges with sprocket holes down each side.
    film: {
      under: function (ctx) {
        ctx.fillStyle = "#111111";
        ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = CREAM;
        for (let y = 24; y < H - 40; y += 70) {
          ctx.beginPath();
          ctx.roundRect(16, y, 34, 44, 6);
          ctx.roundRect(W - 50, y, 34, 44, 6);
          ctx.fill();
        }
        ctx.font = 'bold 22px "Courier Prime", monospace';
        ctx.fillStyle = "#e8a33d";
        ctx.fillText("SEARCH 400", 70, 42);
        ctx.fillText("\u25B6 12A", W - 190, H - 22);
        return 64;
      },
    },
    // Torn paper: the colour sits on cream paper with a ripped edge.
    torn: {
      under: function (ctx) {
        ctx.fillStyle = INK;
        ctx.fillRect(0, 0, W, H);
        // A jagged outline around the edge, the same every time.
        let seed = 7;
        function wobble() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
        ctx.fillStyle = CREAM;
        ctx.beginPath();
        const m = 30, step = 22;
        ctx.moveTo(m, m);
        for (let x = m; x <= W - m; x += step) ctx.lineTo(x, m + wobble() * 18 - 9);
        for (let y = m; y <= H - m; y += step) ctx.lineTo(W - m + wobble() * 18 - 9, y);
        for (let x = W - m; x >= m; x -= step) ctx.lineTo(x, H - m + wobble() * 18 - 9);
        for (let y = H - m; y >= m; y -= step) ctx.lineTo(m + wobble() * 18 - 9, y);
        ctx.closePath();
        ctx.fill();
        return 62;
      },
    },
    // An event ticket: cream with notched corners and a perforated tear line.
    ticket: {
      under: function (ctx) {
        ctx.fillStyle = INK;
        ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = CREAM;
        ctx.fillRect(20, 20, W - 40, H - 40);
        ctx.fillStyle = INK;
        [[20, 20], [W - 20, 20], [20, H - 20], [W - 20, H - 20]].forEach(function (c) {
          ctx.beginPath(); ctx.arc(c[0], c[1], 46, 0, Math.PI * 2); ctx.fill();
        });
        return 60;
      },
      over: function (ctx) {
        ctx.save();
        ctx.setLineDash([14, 12]);
        ctx.strokeStyle = INK;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(60, H - 210);
        ctx.lineTo(W - 60, H - 210);
        ctx.stroke();
        ctx.restore();
      },
    },
    // A kraft paper envelope with a stitched dashed line around it.
    kraft: {
      under: function (ctx) {
        ctx.fillStyle = "#b98a5a";
        ctx.fillRect(0, 0, W, H);
        ctx.save();
        ctx.setLineDash([22, 14]);
        ctx.strokeStyle = CREAM;
        ctx.lineWidth = 5;
        ctx.strokeRect(26, 26, W - 52, H - 52);
        ctx.restore();
        return 60;
      },
    },
    // A postcard: cream border with a round Orlando postmark and wavy
    // cancellation lines in the top-right corner.
    postcard: {
      under: function (ctx) {
        ctx.fillStyle = CREAM;
        ctx.fillRect(0, 0, W, H);
        return 56;
      },
      over: function (ctx) {
        ctx.save();
        ctx.strokeStyle = "rgba(26, 26, 26, 0.75)";
        ctx.fillStyle = "rgba(26, 26, 26, 0.75)";
        ctx.lineWidth = 5;
        const cx = W - 140, cy = 96;
        ctx.beginPath(); ctx.arc(cx, cy, 70, 0, Math.PI * 2); ctx.stroke();
        ctx.beginPath(); ctx.arc(cx, cy, 52, 0, Math.PI * 2); ctx.stroke();
        ctx.font = 'bold 20px "Courier Prime", monospace';
        ctx.textAlign = "center";
        ctx.fillText("ORLANDO", cx, cy - 4);
        ctx.fillText("FL", cx, cy + 22);
        ctx.textAlign = "left";
        for (let i = 0; i < 4; i++) {           // the wavy lines
          ctx.beginPath();
          for (let x = cx - 300; x <= cx - 80; x += 6) {
            const y = cy - 52 + i * 22 + Math.sin(x / 18) * 7;
            if (x === cx - 300) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.stroke();
        }
        ctx.restore();
      },
    },
    // No border: the colour goes right to the edge.
    none: {
      under: function () { return 0; },
    },
  };
  let dialog, canvas, chosen = BACKGROUNDS[0], root = "";
  const pictures = {};         // images, loaded once

  // Load an image and wait for it.
  function load(src) {
    if (!pictures[src]) {
      pictures[src] = new Promise(function (resolve, reject) {
        const img = new Image();
        img.onload = function () { resolve(img); };
        img.onerror = reject;
        img.src = root + src;
      });
    }
    return pictures[src];
  }

  // "december" -> "December"
  function capital(word) { return word.charAt(0).toUpperCase() + word.slice(1); }

  // Split text into lines that fit a width.
  function wrap(ctx, text, maxWidth) {
    const lines = [];
    let line = "";
    text.split(" ").forEach(function (word) {
      const test = line ? line + " " + word : word;
      if (ctx.measureText(test).width > maxWidth && line) { lines.push(line); line = word; }
      else line = test;
    });
    lines.push(line);
    return lines;
  }

  // Draw a picture centred on (x, y), turned by "turn" degrees, with an
  // optional white print border and a soft shadow.
  function place(ctx, img, x, y, width, turn, border) {
    const height = width * img.height / img.width;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(turn * Math.PI / 180);
    ctx.shadowColor = "rgba(0, 0, 0, 0.3)";
    ctx.shadowOffsetX = 8;
    ctx.shadowOffsetY = 10;
    ctx.shadowBlur = 18;
    if (border) {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(-width / 2 - border, -height / 2 - border, width + 2 * border, height + 2 * border);
      ctx.shadowColor = "transparent";
    }
    ctx.drawImage(img, -width / 2, -height / 2, width, height);
    ctx.restore();
    return height;
  }

  async function draw() {
    const ctx = canvas.getContext("2d");
    // Wait for the site's fonts, so the words are in Anton and Courier Prime.
    await Promise.all([
      document.fonts.load('100px "Anton"'),
      document.fonts.load('bold 40px "Courier Prime"'),
    ]).catch(function () {});
    const [bg, print, sticker, sticker2, stamp] = await Promise.all([
      load(chosen.image), load(S.storyPrint), load(S.storySticker),
      load(S.storySticker2), load("images/stamp-blue.webp"),
    ]);

    // 1. The border, then the halftone colour inside it. The border style
    //    is BANNER_SETTINGS.storyFrame in banner.js (see FRAMES below).
    const frame = FRAMES[S.storyFrame] || FRAMES.stamp;
    const inset = frame.under(ctx);
    ctx.save();
    ctx.beginPath();
    ctx.rect(inset, inset, W - 2 * inset, H - 2 * inset);
    ctx.clip();
    ctx.fillStyle = chosen.colour;
    ctx.fillRect(0, 0, W, H);
    for (let y = 0; y < H; y += bg.height) {
      for (let x = 0; x < W; x += bg.width) ctx.drawImage(bg, x, y);
    }
    ctx.restore();
    if (inset > 0) {
      ctx.strokeStyle = "#1a1a1a";
      ctx.lineWidth = 4;
      ctx.strokeRect(inset, inset, W - 2 * inset, H - 2 * inset);
    }

    const LEFT = 120;     // left edge for all the words

    // 2. The small black label at the top.
    ctx.font = 'bold 40px "Courier Prime", monospace';
    const label = "SEARCH: a snail mail club";
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(LEFT, 140, ctx.measureText(label).width + 40, 64);
    ctx.fillStyle = "#ffffff";
    ctx.textBaseline = "middle";
    ctx.fillText(label, LEFT + 20, 173);

    // 3. The headline.
    ctx.fillStyle = chosen.ink;
    ctx.font = '124px "Anton", Impact, sans-serif';
    ctx.textBaseline = "alphabetic";
    let y = 350;
    wrap(ctx, "LOCAL ART IN YOUR MAILBOX!", W - 2 * LEFT).forEach(function (line) {
      ctx.fillText(line, LEFT, y);
      y += 132;
    });

    // The words at the bottom are placed up from the bottom edge, and the
    // print goes in the space between the headline and those words.
    // The bottom ~260px are left empty on purpose, so there's room to add
    // Instagram's Link sticker (pointing to the Patreon page) in the story.
    const bottomTop = H - 720;

    // 4. The print, with a white border, and the stickers and stamp to scale.
    // Landscape prints are drawn wider; portrait (tall) prints narrower,
    // so both fill the same space. Inches stay to scale either way.
    const landscape = S.printWidthInches > 4.5;
    const printWidth = landscape ? 600 : 380;
    const perInch = printWidth / S.printWidthInches;  // pixels per inch of print
    const centreY = (y + bottomTop) / 2 - 42;
    const printHeight = place(ctx, print, W / 2 + 20, centreY, printWidth, 3, 22);
    function stickerWidth(img) {      // the long side is about 2.5 inches
      const long = 2.5 * perInch;
      return img.width >= img.height ? long : long * img.width / img.height;
    }
    place(ctx, sticker2, W / 2 - printWidth / 2 + (landscape ? 50 : -40), centreY - printHeight / 2 + (landscape ? 12 : 60), stickerWidth(sticker2), -12, 0);
    place(ctx, sticker, W / 2 + printWidth / 2 + (landscape ? -10 : 40), centreY + printHeight / 2 - (landscape ? 30 : 110), stickerWidth(sticker), 10, 0);
    place(ctx, stamp, W / 2 + printWidth / 2 - 30, centreY - printHeight / 2 + 10, 1.25 * perInch, -14, 0);

    // 5. The month and artist. The name shrinks to fit on one line.
    ctx.fillStyle = chosen.ink;
    ctx.font = 'bold 48px "Courier Prime", monospace';
    ctx.fillText(capital(S.month) + "'s featured artist", LEFT, H - 640);
    let size = 120;
    do {
      ctx.font = size + 'px "Anton", Impact, sans-serif';
      size -= 4;
    } while (ctx.measureText(S.artist.toUpperCase()).width > W - 2 * LEFT && size > 40);
    ctx.fillText(S.artist.toUpperCase(), LEFT, H - 520);

    // A black "Join by" tag, like the site's buttons (kept small, so the
    // story has room for Instagram's Link sticker underneath).
    ctx.font = 'bold 38px "Courier Prime", monospace';
    const join = "JOIN BY " + S.joinBy.toUpperCase();
    const joinWidth = ctx.measureText(join).width + 50;
    const joinTop = H - 480;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(LEFT + 6, joinTop + 6, joinWidth, 70);
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(LEFT, joinTop, joinWidth, 70);
    ctx.fillStyle = "#ffffff";
    ctx.textBaseline = "middle";
    ctx.fillText(join, LEFT + 25, joinTop + 36);

    // 6. Where to sign up. (No price on the story, the owner's request.)
    ctx.fillStyle = chosen.ink;
    ctx.textBaseline = "alphabetic";
    ctx.font = 'bold 36px "Courier Prime", monospace';
    ctx.fillText("patreon.com/SearchCentralFlorida", LEFT, H - 350);

    // Some borders add a finishing touch on top (like strips of tape).
    if (frame.over) frame.over(ctx);
  }

  // Draw, then show the result in the preview image.
  async function redraw() {
    await draw();
    const preview = dialog.querySelector(".story-preview");
    if (preview.src) URL.revokeObjectURL(preview.src);
    preview.src = URL.createObjectURL(await asBlob());
  }

  // The file's name, e.g. "search-mail-club-december.png".
  function fileName() { return "search-mail-club-" + S.month.toLowerCase() + ".png"; }

  function asBlob() {
    return new Promise(function (resolve) { canvas.toBlob(resolve, "image/png"); });
  }

  async function download() {
    const blob = await asBlob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = fileName();
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 4000);
  }

  // On phones, this opens the share sheet, so people can post it straight
  // to their Instagram story. Other browsers just don't show this button.
  async function share() {
    const file = new File([await asBlob()], fileName(), { type: "image/png" });
    try {
      await navigator.share({ files: [file], title: "SEARCH: a snail mail club" });
    } catch (error) {
      // Closing the share sheet counts as an error; ignore it.
    }
  }

  function build() {
    dialog = document.createElement("dialog");
    dialog.className = "story-dialog";
    dialog.setAttribute("aria-labelledby", "story-title");
    dialog.innerHTML =
      '<div class="story-panel">' +
        '<button type="button" class="story-close" aria-label="Close">&times;</button>' +
        '<h2 id="story-title">Share to your story</h2>' +
        '<p class="story-note">A picture of ' + S.month + "'s mail club, the size of an Instagram story. Pick a colour, then save it or share it. The empty space at the bottom is for Instagram\'s <strong>Link</strong> sticker, so people can tap through to Patreon.</p>" +
        '<div class="story-body">' +
          // The picture is drawn on a hidden canvas, then shown as a normal
          // image, so on phones you can also press and hold it to save it.
          '<canvas class="story-canvas" width="' + W + '" height="' + H + '" hidden></canvas>' +
          '<img class="story-preview" alt="Preview of the story picture">' +
          '<div class="story-controls">' +
            '<fieldset class="story-colours"><legend>Background</legend></fieldset>' +
            '<button type="button" class="button story-save">Download</button>' +
            '<button type="button" class="button button-outline story-share" hidden>Share to Instagram</button>' +
            '<p class="story-tip" hidden>Tip: you can also press and hold the picture, then tap <strong>Save to Photos</strong> (iPhone) or <strong>Download image</strong> (Android).</p>' +
          "</div>" +
        "</div>" +
      "</div>";
    document.body.append(dialog);
    canvas = dialog.querySelector("canvas");

    const colours = dialog.querySelector(".story-colours");
    BACKGROUNDS.forEach(function (option, i) {
      const label = document.createElement("label");
      label.className = "story-swatch";
      label.innerHTML = '<input type="radio" name="story-bg" value="' + option.id + '"' + (i === 0 ? " checked" : "") + ">" +
        '<span class="story-chip" style="background-image: url(' + root + option.image + ')"></span>' + option.name;
      label.querySelector("input").addEventListener("change", function () { chosen = option; redraw(); });
      colours.append(label);
    });

    dialog.querySelector(".story-close").addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });
    // Saving. Phones and computers save files differently:
    //  - iPhone/iPad: a plain download goes to the Files app, not Photos.
    //    The share sheet has "Save Image", which goes straight to Photos,
    //    so there the button opens the share sheet.
    //  - Android: a download lands in Downloads, which shows up in Google
    //    Photos and the Gallery, so a normal download is right.
    //  - Computers: a normal download.
    const isApple = /iPhone|iPad|iPod/.test(navigator.userAgent) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);   // iPads say "Mac"
    const isPhone = window.matchMedia("(pointer: coarse)").matches || navigator.maxTouchPoints > 0;
    const test = new File([""], "test.png", { type: "image/png" });
    const canShareFiles = Boolean(navigator.canShare && navigator.canShare({ files: [test] }));

    const saveButton = dialog.querySelector(".story-save");
    if (isPhone) {
      saveButton.textContent = "Save to Photos";
      dialog.querySelector(".story-tip").hidden = false;
    }
    saveButton.addEventListener("click", function () {
      if (isApple && canShareFiles) share();   // then tap "Save Image"
      else download();
    });

    // A separate Share button where the phone can share pictures (to post
    // straight to an Instagram story). On iPhones the Save button already
    // opens the same share sheet, so it's only shown on other phones.
    const shareButton = dialog.querySelector(".story-share");
    if (canShareFiles && !isApple) {
      shareButton.hidden = false;
      shareButton.addEventListener("click", share);
    }
  }

  window.openStoryMaker = function (siteRoot) {
    root = siteRoot || "";
    if (!dialog) build();
    dialog.showModal();
    redraw();
  };
})();
