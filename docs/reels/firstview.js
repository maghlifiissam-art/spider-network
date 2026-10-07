/* First-view fix: landscape posters use contain (no dark crop) and an unstarted reel shows a play hint. */
(function () {
  var s = document.createElement("style");
  s.textContent = ".card .fvp{position:absolute;left:50%;top:42%;transform:translate(-50%,-50%);width:72px;height:72px;border-radius:50%;background:#070714b8;border:2px solid #d4a017;color:#d4a017;font:700 30px/68px system-ui;text-align:center;z-index:6;pointer-events:none}";
  document.head.appendChild(s);
  function prep(v) {
    if (v.dataset.fv) return;
    v.dataset.fv = "1";
    var p = v.getAttribute("poster");
    if (p) {
      var im = new Image();
      im.onload = function () { if (im.naturalWidth > im.naturalHeight) { v.classList.add("landscape"); v.style.background = "#000"; } };
      im.src = p;
    }
    var c = v.closest(".card");
    if (!c || c.querySelector(".fvp")) return;
    var b = document.createElement("div");
    b.className = "fvp";
    b.textContent = "\u25B6";
    c.appendChild(b);
    var done = function () { b.remove(); };
    v.addEventListener("playing", done, { once: true });
  }
  function scan() { document.querySelectorAll(".card video").forEach(prep); }
  scan();
  var f = document.getElementById("feed");
  if (f) new MutationObserver(scan).observe(f, { childList: true, subtree: true });
})();
