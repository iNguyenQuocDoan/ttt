(function () {
  "use strict";

  var root = document.documentElement;
  var KEY_THEME = "tth-theme";
  var KEY_SIZE = "tth-size";
  var KEY_PROGRESS = "tth-progress";
  var SIZES = 4;
  var DEFAULT_SIZE = 1;
  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function load(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }
  function forget(key) {
    try { localStorage.removeItem(key); } catch (e) {}
  }

  /* ---------- tien do doc: { slug: { index, done, at } } */

  function readProgress() {
    var p = null;
    try { p = JSON.parse(load(KEY_PROGRESS) || "null"); } catch (e) {}
    return p && typeof p === "object" ? p : {};
  }

  function updateProgress(slug, patch) {
    var p = readProgress();
    var entry = p[slug] || { index: 0, done: false, at: 0 };
    for (var k in patch) entry[k] = patch[k];
    entry.at = Date.now();
    p[slug] = entry;
    save(KEY_PROGRESS, JSON.stringify(p));
  }

  // ban truoc chi nho mot vi tri o "tth-pos"
  (function migrate() {
    var old = null;
    try { old = JSON.parse(load("tth-pos") || "null"); } catch (e) {}
    if (old && old.slug && !readProgress()[old.slug]) {
      updateProgress(old.slug, { index: old.index || 0, done: false });
    }
    forget("tth-pos");
  })();

  /* ---------- trang hien tai */

  function currentSlug() {
    return document.body.dataset.slug || null;
  }

  function textBlocks() {
    var text = document.querySelector(".text");
    return text ? text.querySelectorAll(":scope > :not(.note-pop)") : [];
  }

  function readingAnchor() {
    var nodes = textBlocks();
    if (!nodes.length) return null;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].getBoundingClientRect().bottom > 8) return { el: nodes[i], index: i };
    }
    return { el: nodes[nodes.length - 1], index: nodes.length - 1 };
  }

  function endReached() {
    var text = document.querySelector(".text");
    return !!text && text.getBoundingClientRect().bottom <= window.innerHeight + 4;
  }

  /* ---------- nen trang / nen den */

  function currentTheme() {
    return root.dataset.theme || (darkQuery.matches ? "dark" : "light");
  }
  function paintThemeButton() {
    var btn = document.querySelector('[data-action="theme"]');
    if (btn) btn.textContent = currentTheme() === "dark" ? "Nền trắng" : "Nền đen";
  }
  darkQuery.addEventListener("change", paintThemeButton);

  /* ---------- co chu */

  function currentSize() {
    var s = parseInt(root.dataset.size, 10);
    return isNaN(s) ? DEFAULT_SIZE : s;
  }
  function setSize(s) {
    s = Math.max(0, Math.min(SIZES - 1, s));
    var anchor = readingAnchor();
    var offset = anchor ? anchor.el.getBoundingClientRect().top : 0;
    root.dataset.size = String(s);
    save(KEY_SIZE, String(s));
    if (anchor) {
      window.scrollTo({ top: anchor.el.getBoundingClientRect().top + window.scrollY - offset, behavior: "instant" });
    }
    paintSizeButtons();
  }
  function paintSizeButtons() {
    var s = currentSize();
    var smaller = document.querySelector('[data-action="smaller"]');
    var larger = document.querySelector('[data-action="larger"]');
    if (smaller) smaller.disabled = s === 0;
    if (larger) larger.disabled = s === SIZES - 1;
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-action]");
    if (!btn) return;
    var action = btn.dataset.action;
    if (action === "theme") {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      save(KEY_THEME, next);
      paintThemeButton();
    } else if (action === "smaller" || action === "larger") {
      setSize(currentSize() + (action === "larger" ? 1 : -1));
    } else if (action === "speak") {
      if (speech.on) stopSpeaking(); else startSpeaking();
    }
  });

  /* ---------- muc luc: doc tiep, chuong da doc */

  function paintIndex() {
    var links = Array.prototype.slice.call(document.querySelectorAll(".toc a[data-slug]"));
    if (!links.length) return;
    var progress = readProgress();

    links.forEach(function (a) {
      var entry = progress[a.dataset.slug];
      var read = !!(entry && entry.done);
      a.parentNode.classList.toggle("is-read", read);
      var mark = a.querySelector(".toc-read");
      if (read && !mark) {
        var label = a.querySelector(".toc-label");
        mark = document.createElement("span");
        mark.className = "toc-read";
        if (label) {
          mark.textContent = ", đã đọc";
          label.appendChild(mark);
        } else {
          mark.textContent = "Đã đọc";
          mark.classList.add("toc-label");
          a.insertBefore(mark, a.firstChild);
        }
      } else if (!read && mark) {
        mark.remove();
      }
    });

    var resume = document.querySelector(".resume");
    if (!resume) return;
    var last = null;
    links.forEach(function (a, i) {
      var entry = progress[a.dataset.slug];
      if (entry && (!last || entry.at > last.entry.at)) last = { entry: entry, i: i };
    });
    var target = null;
    if (last && !last.entry.done) {
      target = links[last.i];
    } else if (last) {
      for (var j = last.i + 1; j < links.length; j++) {
        var e2 = progress[links[j].dataset.slug];
        if (!e2 || !e2.done) { target = links[j]; break; }
      }
    }
    if (target) {
      var link = resume.querySelector("a");
      link.href = target.getAttribute("href");
      link.textContent = "Đọc tiếp: " + target.querySelector(".toc-title").textContent;
      resume.hidden = false;
    } else {
      resume.hidden = true;
    }
  }

  /* ---------- nho cho dang doc */

  var saveTimer = null;
  window.addEventListener("scroll", function () {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      var slug = currentSlug();
      if (!slug) return;
      var anchor = readingAnchor();
      var patch = { index: anchor ? anchor.index : 0 };
      if (endReached()) patch.done = true;
      updateProgress(slug, patch);
    }, 300);
  }, { passive: true });

  function restorePosition(opts) {
    if (opts.hash) {
      var el = document.getElementById(decodeURIComponent(opts.hash.slice(1)));
      if (el) { el.scrollIntoView({ block: "start", behavior: "instant" }); return; }
    }
    if (typeof opts.scroll === "number") {
      window.scrollTo({ top: opts.scroll, behavior: "instant" });
      return;
    }
    var slug = currentSlug();
    var entry = slug && readProgress()[slug];
    if (entry && !entry.done && entry.index > 0) {
      var target = textBlocks()[entry.index];
      if (target) { target.scrollIntoView({ block: "start", behavior: "instant" }); return; }
    }
    if (!opts.initial) window.scrollTo({ top: 0, behavior: "instant" });
  }

  /* ---------- chuyen trang bang JS */

  var pages = new Map();

  function pageKey(href) {
    var url = new URL(href, location.href);
    url.hash = "";
    return url.href;
  }

  function fetchPage(href) {
    var key = pageKey(href);
    if (!pages.has(key)) {
      var req = fetch(key, { credentials: "same-origin" }).then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.text();
      });
      req.catch(function () { pages.delete(key); });
      pages.set(key, req);
    }
    return pages.get(key);
  }

  function isReaderLink(a) {
    if (!a || a.target || a.hasAttribute("download")) return false;
    var url = new URL(a.href, location.href);
    if (url.origin !== location.origin) return false;
    if (url.pathname === location.pathname && url.search === location.search) return false;
    return /(\.html|\/)$/.test(url.pathname);
  }

  var navToken = 0;

  function go(href, opts) {
    opts = opts || {};
    var url = new URL(href, location.href);
    var token = ++navToken;
    if (opts.push) {
      try { history.replaceState({ scroll: window.scrollY }, ""); } catch (e) {}
    }
    fetchPage(url.href).then(function (html) {
      if (token !== navToken) return;
      var doc = new DOMParser().parseFromString(html, "text/html");
      if (!doc.querySelector("main.page")) throw new Error("not a reader page");
      doc.querySelectorAll("script").forEach(function (s) { s.remove(); });

      var swap = function () {
        document.title = doc.title;
        document.body = document.importNode(doc.body, true);
        if (opts.push) history.pushState({ scroll: 0 }, "", url.href);
        renderedPath = url.pathname;
        initPage({ hash: url.hash, scroll: opts.scroll });
        var h1 = document.querySelector("h1");
        if (h1) {
          h1.setAttribute("tabindex", "-1");
          h1.focus({ preventScroll: true });
        }
      };
      if (document.startViewTransition && !reduceMotion.matches) {
        document.startViewTransition(swap);
      } else {
        swap();
      }
    }).catch(function () {
      location.href = url.href;
    });
  }

  if ("scrollRestoration" in history) history.scrollRestoration = "manual";

  var renderedPath = location.pathname;

  window.addEventListener("popstate", function (e) {
    var scroll = e.state && typeof e.state.scroll === "number" ? e.state.scroll : undefined;
    if (location.pathname === renderedPath) {
      // chi doi #neo trong cung mot trang (muc luc chuong, chu thich)
      restorePosition({ hash: location.hash, scroll: scroll, initial: true });
      return;
    }
    go(location.href, { push: false, scroll: scroll });
  });

  function prefetchNeighbours() {
    var links = document.querySelectorAll('.chapter-nav a[rel="next"], .resume:not([hidden]) a');
    var run = function () {
      links.forEach(function (a) { if (isReaderLink(a)) fetchPage(a.href).catch(function () {}); });
    };
    if ("requestIdleCallback" in window) requestIdleCallback(run, { timeout: 3000 });
    else setTimeout(run, 1200);
  }

  /* ---------- chu thich mo ngay duoi doan van */

  document.addEventListener("click", function (e) {
    var a = e.target.closest("a.fn");
    if (!a) return;
    var n = a.dataset.n;
    var source = document.getElementById("chu-thich-" + n);
    var block = a.closest(".text > *");
    if (!source || !block) return;
    e.preventDefault();

    var next = block.nextElementSibling;
    while (next && next.classList.contains("note-pop")) {
      if (next.dataset.n === n) {
        next.remove();
        a.setAttribute("aria-expanded", "false");
        return;
      }
      next = next.nextElementSibling;
    }

    var box = document.createElement("div");
    box.className = "note-pop";
    box.dataset.n = n;
    box.setAttribute("role", "note");
    box.innerHTML = '<span class="note-n">' + n + "</span>" +
      source.querySelector(".note-text").innerHTML;
    var after = block;
    while (after.nextElementSibling && after.nextElementSibling.classList.contains("note-pop")) {
      after = after.nextElementSibling;
    }
    after.after(box);
    a.setAttribute("aria-expanded", "true");
  });

  // dang ky sau listener chu thich de link chu thich khong bi bat nham
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest("a[href]");
    if (!isReaderLink(a)) return;
    e.preventDefault();
    go(a.href, { push: true });
  });

  document.addEventListener("pointerover", function (e) {
    var a = e.target.closest && e.target.closest("a[href]");
    if (isReaderLink(a)) fetchPage(a.href).catch(function () {});
  });

  /* ---------- phim mui ten va vuot ngang de chuyen chuong */

  function goChapter(rel) {
    var link = document.querySelector('.chapter-nav a[rel="' + rel + '"]');
    if (link) go(link.href, { push: true });
  }

  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.key === "ArrowRight") goChapter("next");
    else if (e.key === "ArrowLeft") goChapter("prev");
  });

  var touch = null;
  var EDGE = 28;

  document.addEventListener("touchstart", function (e) {
    touch = null;
    if (e.touches.length !== 1 || !currentSlug()) return;
    if (window.visualViewport && window.visualViewport.scale > 1.05) return;
    var t = e.touches[0];
    // mep man hinh danh cho cu chi quay lai cua he dieu hanh
    if (t.clientX < EDGE || t.clientX > window.innerWidth - EDGE) return;
    touch = { x: t.clientX, y: t.clientY, time: Date.now() };
  }, { passive: true });

  document.addEventListener("touchcancel", function () { touch = null; }, { passive: true });

  document.addEventListener("touchend", function (e) {
    if (!touch) return;
    var t = e.changedTouches[0];
    var dx = t.clientX - touch.x;
    var dy = t.clientY - touch.y;
    var dt = Date.now() - touch.time;
    touch = null;
    if (dt > 700 || Math.abs(dx) < 80 || Math.abs(dy) > Math.abs(dx) * 0.5) return;
    var selection = window.getSelection();
    if (selection && !selection.isCollapsed) return;
    goChapter(dx < 0 ? "next" : "prev");
  }, { passive: true });

  /* ---------- nghe doc: giong tieng Viet co san tren may (Web Speech API) */

  var synth = window.speechSynthesis;
  var speech = { on: false, token: 0, queue: [], el: null, utter: null, follow: false, lock: null };

  function viVoice() {
    var vi = synth.getVoices().filter(function (v) { return /^vi/i.test(v.lang); });
    // giong "Natural"/"Online" (Edge) nghe tu nhien hon giong cai san
    return vi.filter(function (v) { return /natural|online|neural/i.test(v.name); })[0] || vi[0] || null;
  }

  function spokenText(el) {
    var c = el.cloneNode(true);
    c.querySelectorAll("sup").forEach(function (s) { s.remove(); });
    c.querySelectorAll("br, .line").forEach(function (b) { b.after(" "); });
    // "(12)" trong bai la so chu thich, khong doc
    return c.textContent.replace(/\(\d+\)/g, "").replace(/\s+/g, " ").trim();
  }

  function sentences(text) {
    // doc tung cau: Chrome hay cat ngang mot lan doc qua dai (~15 giay)
    return text.match(/[^.!?…;:]+[.!?…;:]*[”"’»)]*\s*/g) || [];
  }

  function startSpeaking() {
    if (synth.getVoices().length && !viVoice()) {
      alert("Máy này chưa có giọng đọc tiếng Việt. Hãy tải giọng tiếng Việt trong phần cài đặt giọng nói của máy " +
        "(Android: Chuyển văn bản thành giọng nói; iPhone: Trợ năng > Nội dung được đọc; Windows: Giọng nói), " +
        "hoặc mở trang bằng Microsoft Edge.");
      return;
    }
    stopSpeaking();
    var anchor = readingAnchor();
    if (!anchor) return;
    var els = Array.prototype.slice.call(textBlocks(), anchor.index);
    if (anchor.index === 0) els = Array.prototype.slice.call(document.querySelectorAll(".opener > *")).concat(els);
    els.forEach(function (el) {
      if (el.getAttribute("aria-hidden") === "true") return;
      var text = spokenText(el);
      if (/^[IVXLC]+\.?$/.test(text)) return; // tieu de chi la so La Ma
      sentences(text).forEach(function (s) { speech.queue.push({ el: el, text: s }); });
    });
    speech.on = true;
    keepAwake(true);
    paintSpeakButton();
    speakNext(speech.token);
  }

  function speakNext(token) {
    if (token !== speech.token) return;
    var item = speech.queue.shift();
    if (!item) {
      stopSpeaking();
      updateProgress(currentSlug(), { done: true });
      // het chuong: sang chuong sau va doc tiep
      if (document.querySelector('.chapter-nav a[rel="next"]')) {
        speech.follow = true;
        goChapter("next");
      }
      return;
    }
    markSpeaking(item.el);
    var u = new SpeechSynthesisUtterance(item.text);
    u.lang = "vi-VN";
    u.voice = viVoice();
    u.onend = function () { speakNext(token); };
    u.onerror = function () { if (token === speech.token) stopSpeaking(); };
    speech.utter = u; // giu tham chieu: Chrome co the don rac utterance truoc khi onend chay
    synth.speak(u);
  }

  function stopSpeaking() {
    speech.token++;
    speech.on = false;
    speech.queue = [];
    if (synth && (synth.speaking || synth.pending)) synth.cancel();
    markSpeaking(null);
    keepAwake(false);
    paintSpeakButton();
  }

  function markSpeaking(el) {
    if (speech.el === el) return;
    if (speech.el) speech.el.classList.remove("is-speaking");
    speech.el = el;
    if (!el) return;
    el.classList.add("is-speaking");
    var top = el.getBoundingClientRect().top;
    if (top < 0 || top > window.innerHeight * 0.6) {
      el.scrollIntoView({ block: "start", behavior: reduceMotion.matches ? "instant" : "smooth" });
    }
  }

  // man hinh tat thi trinh duyet ngung doc, nen giu man hinh sang khi dang doc
  function keepAwake(on) {
    if (!("wakeLock" in navigator)) return;
    if (!on) {
      if (speech.lock) speech.lock.release();
      speech.lock = null;
      return;
    }
    if (speech.lock) return;
    navigator.wakeLock.request("screen").then(function (lock) {
      if (!speech.on || speech.lock) { lock.release(); return; }
      speech.lock = lock;
      lock.addEventListener("release", function () { if (speech.lock === lock) speech.lock = null; });
    }).catch(function () {});
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && speech.on) keepAwake(true);
  });

  // Chrome van doc tiep sau khi tai lai hoac roi trang
  window.addEventListener("pagehide", function () { if (synth) synth.cancel(); });

  function paintSpeakButton() {
    if (!synth || !currentSlug()) return;
    // nut noi co dinh: bam duoc o bat cu dau trong chuong, doc tu doan dang xem
    var btn = document.querySelector(".speak");
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.className = "speak";
      btn.dataset.action = "speak";
      document.body.appendChild(btn);
    }
    btn.textContent = speech.on ? "Dừng đọc" : "Nghe đọc";
  }

  /* ---------- khoi tao moi trang */

  function initPage(opts) {
    paintThemeButton();
    paintSizeButtons();
    paintIndex();
    var slug = currentSlug();
    if (slug) updateProgress(slug, {});
    restorePosition(opts);
    if (speech.follow) {
      speech.follow = false;
      startSpeaking();
    } else {
      stopSpeaking();
    }
    if (opts.initial && document.fonts && document.fonts.ready) {
      var settled = window.scrollY;
      document.fonts.ready.then(function () {
        // font tai xong lam dich chu; chi can lai neu nguoi doc chua tu cuon
        if (window.scrollY === settled) restorePosition(opts);
      });
    }
    prefetchNeighbours();
  }

  initPage({ initial: true, hash: location.hash });

  /* ---------- luu cac chuong da mo de doc khi mat mang */

  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }
})();
