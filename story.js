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

    // 1. The halftone background, repeated to fill the picture.
    ctx.fillStyle = chosen.colour;
    ctx.fillRect(0, 0, W, H);
    for (let y = 0; y < H; y += bg.height) {
      for (let x = 0; x < W; x += bg.width) ctx.drawImage(bg, x, y);
    }

    // 2. The small black label at the top.
    ctx.font = 'bold 40px "Courier Prime", monospace';
    const label = "SEARCH: a snail mail club";
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(90, 130, ctx.measureText(label).width + 40, 64);
    ctx.fillStyle = "#ffffff";
    ctx.textBaseline = "middle";
    ctx.fillText(label, 110, 163);

    // 3. The headline.
    ctx.fillStyle = chosen.ink;
    ctx.font = '140px "Anton", Impact, sans-serif';
    ctx.textBaseline = "alphabetic";
    let y = 360;
    wrap(ctx, "LOCAL ART IN YOUR MAILBOX!", W - 180).forEach(function (line) {
      ctx.fillText(line, 90, y);
      y += 150;
    });

    // The words at the bottom are placed up from the bottom edge, and the
    // print goes in the space between the headline and those words.
    const bottomTop = H - 560;

    // 4. The print, with a white border, and the stickers and stamp to scale.
    const printWidth = 720;
    const perInch = printWidth / S.printWidthInches;  // pixels per inch of print
    const centreY = (y + bottomTop) / 2;
    const printHeight = place(ctx, print, W / 2 + 20, centreY, printWidth, 3, 22);
    function stickerWidth(img) {      // the long side is about 2.5 inches
      const long = 2.5 * perInch;
      return img.width >= img.height ? long : long * img.width / img.height;
    }
    place(ctx, sticker2, W / 2 - printWidth / 2 + 50, centreY - printHeight / 2 - 10, stickerWidth(sticker2), -12, 0);
    place(ctx, sticker, W / 2 + printWidth / 2 - 10, centreY + printHeight / 2 - 30, stickerWidth(sticker), 10, 0);
    place(ctx, stamp, W / 2 + printWidth / 2 - 30, centreY - printHeight / 2 + 10, 1.25 * perInch, -14, 0);

    // 5. The month and artist. The name shrinks to fit on one line.
    ctx.fillStyle = chosen.ink;
    ctx.font = 'bold 48px "Courier Prime", monospace';
    ctx.fillText(capital(S.month) + "'s featured artist", 90, H - 470);
    let size = 120;
    do {
      ctx.font = size + 'px "Anton", Impact, sans-serif';
      size -= 4;
    } while (ctx.measureText(S.artist.toUpperCase()).width > W - 180 && size > 40);
    ctx.fillText(S.artist.toUpperCase(), 90, H - 345);

    // A black "Join by" tag, like the site's buttons.
    ctx.font = 'bold 54px "Courier Prime", monospace';
    const join = "JOIN BY " + S.joinBy.toUpperCase();
    const joinWidth = ctx.measureText(join).width + 70;
    const joinTop = H - 300;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(98, joinTop + 8, joinWidth, 100);
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(90, joinTop, joinWidth, 100);
    ctx.fillStyle = "#ffffff";
    ctx.textBaseline = "middle";
    ctx.fillText(join, 125, joinTop + 51);

    // 6. Where to sign up.
    ctx.fillStyle = chosen.ink;
    ctx.textBaseline = "alphabetic";
    ctx.font = 'bold 40px "Courier Prime", monospace';
    ctx.fillText("starting at $6.99/month", 90, H - 120);
    ctx.fillText("searchcentralfl.com/mailclub", 90, H - 65);
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
      await navigator.share({ files: [file] });
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
        '<p class="story-note">A picture of ' + S.month + "'s mail club, the size of an Instagram story. Pick a colour, then save it or share it.</p>" +
        '<div class="story-body">' +
          '<canvas class="story-canvas" width="' + W + '" height="' + H + '" role="img" aria-label="Preview of the story picture"></canvas>' +
          '<div class="story-controls">' +
            '<fieldset class="story-colours"><legend>Background</legend></fieldset>' +
            '<button type="button" class="button story-download">Download</button>' +
            '<button type="button" class="button button-outline story-share" hidden>Share</button>' +
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
      label.querySelector("input").addEventListener("change", function () { chosen = option; draw(); });
      colours.append(label);
    });

    dialog.querySelector(".story-close").addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });
    dialog.querySelector(".story-download").addEventListener("click", download);

    // Only offer "Share" where the browser can share pictures (mostly phones).
    const shareButton = dialog.querySelector(".story-share");
    const test = new File([""], "test.png", { type: "image/png" });
    if (navigator.canShare && navigator.canShare({ files: [test] })) {
      shareButton.hidden = false;
      shareButton.addEventListener("click", share);
    }
  }

  window.openStoryMaker = function (siteRoot) {
    root = siteRoot || "";
    if (!dialog) build();
    dialog.showModal();
    draw();
  };
})();
