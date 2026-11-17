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

    // 1. The border: the picture looks like a postage stamp. A dark
    //    backdrop, a cream stamp with perforated (bitten) edges, and the
    //    chosen halftone colour inside it with a thin ink line around it.
    const STAMP = 26;     // backdrop showing around the stamp
    const PAPER = 34;     // cream paper between the perforations and the colour
    const HOLE = 13;      // size of each perforation bite
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#f6f1e7";
    ctx.fillRect(STAMP, STAMP, W - 2 * STAMP, H - 2 * STAMP);
    ctx.fillStyle = "#1a1a1a";
    function bite(x, y) { ctx.beginPath(); ctx.arc(x, y, HOLE, 0, Math.PI * 2); ctx.fill(); }
    const stampW = W - 2 * STAMP, stampH = H - 2 * STAMP;
    const across = Math.round(stampW / 44), down = Math.round(stampH / 44);
    for (let i = 0; i <= across; i++) {
      bite(STAMP + i * stampW / across, STAMP);
      bite(STAMP + i * stampW / across, H - STAMP);
    }
    for (let i = 0; i <= down; i++) {
      bite(STAMP, STAMP + i * stampH / down);
      bite(W - STAMP, STAMP + i * stampH / down);
    }

    // The halftone colour, repeated to fill the inside of the stamp.
    const inset = STAMP + PAPER;
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
    ctx.strokeStyle = "#1a1a1a";
    ctx.lineWidth = 4;
    ctx.strokeRect(inset, inset, W - 2 * inset, H - 2 * inset);

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
    ctx.font = '140px "Anton", Impact, sans-serif';
    ctx.textBaseline = "alphabetic";
    let y = 370;
    wrap(ctx, "LOCAL ART IN YOUR MAILBOX!", W - 2 * LEFT).forEach(function (line) {
      ctx.fillText(line, LEFT, y);
      y += 150;
    });

    // The words at the bottom are placed up from the bottom edge, and the
    // print goes in the space between the headline and those words.
    const bottomTop = H - 590;

    // 4. The print, with a white border, and the stickers and stamp to scale.
    // Landscape prints are drawn wider; portrait (tall) prints narrower,
    // so both fill the same space. Inches stay to scale either way.
    const landscape = S.printWidthInches > 4.5;
    const printWidth = landscape ? 640 : 420;
    const perInch = printWidth / S.printWidthInches;  // pixels per inch of print
    const centreY = (y + bottomTop) / 2 - 30;
    const printHeight = place(ctx, print, W / 2 + 20, centreY, printWidth, 3, 22);
    function stickerWidth(img) {      // the long side is about 2.5 inches
      const long = 2.5 * perInch;
      return img.width >= img.height ? long : long * img.width / img.height;
    }
    place(ctx, sticker2, W / 2 - printWidth / 2 + (landscape ? 50 : -40), centreY - printHeight / 2 + (landscape ? -10 : 60), stickerWidth(sticker2), -12, 0);
    place(ctx, sticker, W / 2 + printWidth / 2 + (landscape ? -10 : 40), centreY + printHeight / 2 - (landscape ? 30 : 110), stickerWidth(sticker), 10, 0);
    place(ctx, stamp, W / 2 + printWidth / 2 - 30, centreY - printHeight / 2 + 10, 1.25 * perInch, -14, 0);

    // 5. The month and artist. The name shrinks to fit on one line.
    ctx.fillStyle = chosen.ink;
    ctx.font = 'bold 48px "Courier Prime", monospace';
    ctx.fillText(capital(S.month) + "'s featured artist", LEFT, H - 500);
    let size = 120;
    do {
      ctx.font = size + 'px "Anton", Impact, sans-serif';
      size -= 4;
    } while (ctx.measureText(S.artist.toUpperCase()).width > W - 2 * LEFT && size > 40);
    ctx.fillText(S.artist.toUpperCase(), LEFT, H - 375);

    // A black "Join by" tag, like the site's buttons.
    ctx.font = 'bold 54px "Courier Prime", monospace';
    const join = "JOIN BY " + S.joinBy.toUpperCase();
    const joinWidth = ctx.measureText(join).width + 70;
    const joinTop = H - 330;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(LEFT + 8, joinTop + 8, joinWidth, 100);
    ctx.fillStyle = "#1a1a1a";
    ctx.fillRect(LEFT, joinTop, joinWidth, 100);
    ctx.fillStyle = "#ffffff";
    ctx.textBaseline = "middle";
    ctx.fillText(join, LEFT + 35, joinTop + 51);

    // 6. Where to sign up. (No price on the story, the owner's request.)
    ctx.fillStyle = chosen.ink;
    ctx.textBaseline = "alphabetic";
    ctx.font = 'bold 40px "Courier Prime", monospace';
    ctx.fillText("searchcentralfl.com/mailclub", LEFT, H - 140);
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
        '<p class="story-note">A picture of ' + S.month + "'s mail club, the size of an Instagram story. Pick a colour, then save it or share it.</p>" +
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
