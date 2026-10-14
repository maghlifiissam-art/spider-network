/* Home landing (mobile + desktop): Facebook-style Reels strip replaces the auto-playing
   posts feed (mobile) and the old thumbnail grid (desktop), followed inline by the
   Posts feed (Supabase posts) and the latest blog posts. One page: reels -> posts -> blog.
   Tap a reel card to open the full-screen player; the back button returns to the strip. */
(function () {
  var H = document.documentElement;
  var mqWide = matchMedia("(min-width:1000px)");
  var box = null;
  var images = new IntersectionObserver(function(entries){entries.forEach(function(entry){if(!entry.isIntersecting)return;var image=entry.target;if(image.dataset.src&&!image.getAttribute("src"))image.src=image.dataset.src;images.unobserve(image);});},{rootMargin:"120px 0px"});
  function watchImages(container){container.querySelectorAll("img[data-src]").forEach(function(image){images.observe(image);});}
  var LBL = { en: "Reels", fr: "Reels", ar: "ريلزات", ary: "ريلزات", es: "Reels", pt: "Reels", de: "Reels", tr: "Reels" };
  var POSTS = { en: "Posts", fr: "Publications", ar: "المنشورات", ary: "المنشورات", es: "Publicaciones", pt: "Publicações", de: "Beiträge", tr: "Gönderiler" };
  var BLOG = { en: "Blog", fr: "Blog", ar: "التدوينات", ary: "التدوينات", es: "Blog", pt: "Blog", de: "Blog", tr: "Blog" };
  var VIEWALL = { en: "See all", fr: "Tout voir", ar: "عرض الكل", ary: "شوف الكل", es: "Ver todo", pt: "Ver tudo", de: "Alle ansehen", tr: "Tümünü gör" };
  function lg() { return localStorage.getItem("lang") || "en"; }
  function label() { return LBL[lg()] || LBL.en; }
  function esc(t) { return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function feed() { return document.getElementById("feed"); }
  function cards() {
    var f = feed();
    return f ? [].slice.call(f.querySelectorAll(".card.v")).filter(function (c) { return c.querySelector("video"); }) : [];
  }
  function ensureBox() {
    box = document.getElementById("rlz");
    if (!box) { box = document.createElement("div"); box.id = "rlz"; }
    var host = mqWide.matches ? document.getElementById("gmn") : null;
    if (host) {
      var gch = document.getElementById("gch");
      if (box.parentNode !== host) host.insertBefore(box, gch ? gch.nextSibling : null);
    } else {
      var f = feed();
      if (f && box.nextSibling !== f) f.parentNode.insertBefore(box, f);
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
  function secHead(icon, map, href) {
    return '<div class="rsh"><span class="ric">' + icon + '</span><b>' + (map[lg()] || map.en) + '</b><a href="' + href + '">' + (VIEWALL[lg()] || VIEWALL.en) + '</a></div>';
  }
  var secPosts = null, secPosts2 = null, secBlog = null;
  function ensureSections() {
    if (!secPosts) {
      secPosts = document.createElement("div");
      secPosts.className = "rlsc";
      secPosts.innerHTML = secHead("&#128196;", POSTS, "posts.html") + '<div class="rpb"></div>';
      secPosts2 = document.createElement("div");
      secPosts2.className = "rlsc";
      secPosts2.innerHTML = '<div class="rpb"></div>';
      fillPosts(secPosts.querySelector(".rpb"), secPosts, secPosts2);
    }
    if (!secBlog) {
      secBlog = document.createElement("div");
      secBlog.className = "rlsc";
      secBlog.innerHTML = secHead("&#9998;", BLOG, "../") + '<div class="rbb"></div>';
      fillBlog(secBlog.querySelector(".rbb"), secBlog);
    }
  }
  function fillPosts(list, sec, sec2) {
    if (typeof SBC === "undefined" || !SBC) { sec.style.display = "none"; sec2.style.display = "none"; return; }
    SBC.from("posts").select("id,kind,title,body,media_url,poster_url,source_url,source_platform,source_author,topic,is_sponsored,channels(handle,name)").order("created_at", { ascending: false }).limit(12)
      .then(function (r) {
        if (r.error || !r.data || !r.data.length) { sec.style.display = "none"; sec2.style.display = "none"; return; }
        var render = function (p) {
          var h = (p.channels && p.channels.handle) || "";
          var topic = "";
          try { topic = (typeof T === "function") ? T(p.topic || "") : (p.topic || ""); } catch (e) { topic = p.topic || ""; }
          var s = '<div class="rpc"><div class="rph">'
            + (h ? '<a href="channel.html?h=' + encodeURIComponent(h) + '">@' + esc(h) + '</a>' : '')
            + '<span>' + esc(topic) + (p.is_sponsored ? " &middot; Ad" : "") + '</span></div>';
          if (p.title) s += '<a class="rpt" href="posts.html?p=' + p.id + '"><h3>' + esc(p.title) + '</h3></a>';
          if (p.body) s += '<p>' + esc(p.body) + '</p>';
          if (p.kind === "image" && p.media_url) s += '<a href="posts.html?p=' + p.id + '"><img loading="lazy" decoding="async" data-src="' + esc(p.media_url) + '" alt=""></a>';
          if (p.kind === "video" && p.media_url) s += '<a class="rpv" href="posts.html?p=' + p.id + '">' + (p.poster_url ? '<img loading="lazy" decoding="async" data-src="' + esc(p.poster_url) + '" alt="">' : '') + '</a>';
          if (p.source_url) s += '<div class="rps">&#128279; ' + esc(p.source_platform || "web") + (p.source_author ? " &middot; " + esc(p.source_author) : "") + ' <a href="' + esc(p.source_url) + '" target="_blank" rel="noopener noreferrer nofollow">&#8599;</a></div>';
          return s + '</div>';
        };
        list.innerHTML = r.data.slice(0, 4).map(render).join("");
        var rest = r.data.slice(4);
        if (rest.length) { sec2.querySelector(".rpb").innerHTML = rest.map(render).join(""); }
        else { sec2.style.display = "none"; }
        watchImages(sec);watchImages(sec2);
      }).catch(function () { sec.style.display = "none"; sec2.style.display = "none"; });
  }
  function fillBlog(list, sec) {
    fetch("../", { credentials: "omit" }).then(function (r) {
      if (!r.ok) throw 0;
      return r.text();
    }).then(function (html) {
      var doc = new DOMParser().parseFromString(html, "text/html");
      var lis = [].slice.call(doc.querySelectorAll("ul li")).slice(0, 6);
      if (!lis.length) throw 0;
      var out = "";
      lis.forEach(function (li) {
        var a = li.querySelector("a");
        if (!a) return;
        var href = "";
        try { href = new URL(a.getAttribute("href"), location.origin + "/").href; } catch (e) { return; }
        var t = (a.textContent || "").trim();
        var d = (li.textContent || "").replace(a.textContent || "", "").replace(/^[\s\u00b7\u2013\u2014-]+/, "").trim();
        out += '<a class="rba" href="' + esc(href) + '"><span class="rbt2">' + esc(t) + '</span>' + (d ? '<span class="rbd">' + esc(d) + '</span>' : "") + '</a>';
      });
      if (!out) throw 0;
      list.innerHTML = out;
    }).catch(function () { sec.style.display = "none"; });
  }
  function build() {
    ensureBox();
    ensureSections();
    if (H.classList.contains("pl")) { box.style.display = "none"; return; }
    var f = feed();
    var cs = cards();
    if (!cs.length) {
      var em = f ? f.querySelector(".empty") : null;
      if (em && !/loading|chargement|تحميل|كنحم/i.test(em.textContent)) { H.classList.add("pl"); return; }
      box.innerHTML = head() + '<div class="rhr"><i class="rhl"></i><i class="rhl"></i><i class="rhl"></i></div>';
      box.appendChild(secPosts);
      box.appendChild(secPosts2);
      box.appendChild(secBlog);
      box.style.display = "block";
      return;
    }
    box.innerHTML = head() + '<div class="rhr rhr1"></div>';
    var row = box.querySelector(".rhr");
    var btns = [];
    cs.forEach(function (c) {
      var v = c.querySelector("video");
      var poster = (v.dataset && v.dataset.poster) || v.getAttribute("poster") || "";
      var t = ((c.querySelector("h2") || {}).textContent || "").trim();
      var a = c.querySelector('a[href^="channel.html"]');
      var h = "";
      if (a) { var m = a.textContent.match(/@[\w.-]+/); h = m ? m[0] : ""; }
      if (!t || t === h) { t = h; h = ""; }
      var b = document.createElement("button");
      b.type = "button";
      b.className = "rhc" + (poster ? "" : " np");
      if (poster) {
        var im = document.createElement("img");
        im.dataset.src = poster;
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
      btns.push(b);
    });
    var perRow = mqWide.matches ? 5 : (matchMedia("(min-width:700px)").matches ? 3 : 2);
    var row2 = document.createElement("div");
    row2.className = "rhr rhr2";
    btns.forEach(function (b, i) {
      (i < perRow ? row : row2).appendChild(b);
    });
    box.appendChild(secPosts);
    if (row2.childNodes.length) box.appendChild(row2);
    box.appendChild(secPosts2);
    box.appendChild(secBlog);
    box.style.display = "block";
    watchImages(box);
  }
  var tm = null;
  function soon() { clearTimeout(tm); tm = setTimeout(build, 200); }
  var f = feed();
  if (f) new MutationObserver(soon).observe(f, { childList: true });
  new MutationObserver(soon).observe(H, { attributes: true, attributeFilter: ["class"] });
  if (mqWide.addEventListener) mqWide.addEventListener("change", soon);
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
