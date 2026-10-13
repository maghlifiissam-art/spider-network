/* Mobile home: Facebook-style Reels strip replaces the auto-playing posts feed.
   Tap a reel card to open the full-screen player; the back button returns to the strip.
   Desktop (min-width:1000px) keeps the existing grid landing. */
(function () {
  var H = document.documentElement;
  var mq = matchMedia("(max-width:999px)");
  var box = null;
  var LBL = { en: "Reels", fr: "Reels", ar: "ريلزات", ary: "ريلزات", es: "Reels", pt: "Reels", de: "Reels", tr: "Reels" };
  function label() { return LBL[localStorage.getItem("lang") || "en"] || LBL.en; }
  function feed() { return document.getElementById("feed"); }
  function cards() {
    var f = feed();
    return f ? [].slice.call(f.querySelectorAll(".card.v")).filter(function (c) { return c.querySelector("video"); }) : [];
  }
  function ensureBox() {
    box = document.getElementById("rlz");
    if (!box) {
      box = document.createElement("div");
      box.id = "rlz";
      var f = feed();
      f.parentNode.insertBefore(box, f);
    }
    return box;
  }
  function openCard(c) {
    H.classList.add("pl");
    if (box) box.style.display = "none";
    var f = feed();
    requestAnimationFrame(function () {
      f.style.scrollSnapType = "none";
      f.scrollTop = c.offsetTop;
      setTimeout(function () {
        f.style.scrollSnapType = "";
        f.dispatchEvent(new Event("scroll"));
      }, 80);
    });
  }
  function head() {
    return '<div class="rhz"><span class="ric">&#127916;</span><b>' + label() + '</b></div>';
  }
  function build() {
    ensureBox();
    if (!mq.matches || H.classList.contains("pl")) { box.style.display = "none"; return; }
    var f = feed();
    var cs = cards();
    if (!cs.length) {
      var em = f ? f.querySelector(".empty") : null;
      if (em && !/loading|chargement|تحميل|كنحم/i.test(em.textContent)) { H.classList.add("pl"); return; }
      box.innerHTML = head() + '<div class="rhr"><i class="rhl"></i><i class="rhl"></i><i class="rhl"></i></div>';
      box.style.display = "block";
      return;
    }
    box.innerHTML = head() + '<div class="rhr"></div>';
    var row = box.querySelector(".rhr");
    cs.forEach(function (c) {
      var v = c.querySelector("video");
      var poster = (v.dataset && v.dataset.poster) || v.getAttribute("poster") || "";
      var t = ((c.querySelector("h2") || {}).textContent || "").trim();
      var a = c.querySelector('a[href^="channel.html"]');
      var h = a ? a.textContent.trim() : "";
      var b = document.createElement("button");
      b.type = "button";
      b.className = "rhc" + (poster ? "" : " np");
      if (poster) {
        var im = document.createElement("img");
        im.src = poster;
        im.alt = "";
        im.loading = "lazy";
        im.decoding = "async";
        b.appendChild(im);
      }
      var ply = document.createElement("span");
      ply.className = "rhp";
      ply.textContent = "\u25B6";
      b.appendChild(ply);
      var bt = document.createElement("span");
      bt.className = "rbt";
      if (t) { var tt = document.createElement("span"); tt.className = "rht"; tt.textContent = t; bt.appendChild(tt); }
      if (h) { var hh = document.createElement("span"); hh.className = "rhh"; hh.textContent = h; bt.appendChild(hh); }
      b.appendChild(bt);
      b.addEventListener("click", function () { openCard(c); });
      row.appendChild(b);
    });
    box.style.display = "block";
  }
  var tm = null;
  function soon() { clearTimeout(tm); tm = setTimeout(build, 200); }
  var f = feed();
  if (f) new MutationObserver(soon).observe(f, { childList: true });
  new MutationObserver(soon).observe(H, { attributes: true, attributeFilter: ["class"] });
  if (mq.addEventListener) mq.addEventListener("change", soon);
  var nav = document.getElementById("nav");
  if (nav) nav.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-k]");
    if (!b) return;
    if (b.dataset.k === "all") H.classList.remove("pl"); else H.classList.add("pl");
    soon();
  });
  if (/post=[\w-]+/.test(location.hash)) H.classList.add("pl");
  soon();
})();
