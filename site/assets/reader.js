(function () {
  "use strict";

  var root = document.documentElement;
  var body = document.body;
  var KEY_THEME = "tth-theme";
  var KEY_SIZE = "tth-size";
  var KEY_POS = "tth-pos";
  var SIZES = 4;
  var DEFAULT_SIZE = 1;

  function load(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }

  /* ---------- nen trang / nen den */

  var themeBtn = document.querySelector('[data-action="theme"]');
  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function currentTheme() {
    return root.dataset.theme || (darkQuery.matches ? "dark" : "light");
  }
  function paintThemeButton() {
    if (themeBtn) themeBtn.textContent = currentTheme() === "dark" ? "Nền trắng" : "Nền đen";
  }
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      save(KEY_THEME, next);
      paintThemeButton();
    });
    darkQuery.addEventListener("change", paintThemeButton);
    paintThemeButton();
  }

  /* ---------- doan dang doc */

  var text = document.querySelector(".text");

  function textBlocks() {
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
  document.querySelectorAll('[data-action="smaller"], [data-action="larger"]').forEach(function (btn) {
    btn.addEventListener("click", function () {
      setSize(currentSize() + (btn.dataset.action === "larger" ? 1 : -1));
    });
  });
  paintSizeButtons();

  /* ---------- nho cho dang doc */

  var slug = body.dataset.slug;

  function readPos() {
    try { return JSON.parse(load(KEY_POS) || "null"); } catch (e) { return null; }
  }

  if (slug && text) {
    var saved = readPos();
    if (saved && saved.slug === slug && !location.hash && saved.index > 0) {
      var restore = function () {
        var target = textBlocks()[saved.index];
        if (target) target.scrollIntoView({ block: "start", behavior: "instant" });
      };
      restore();
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(restore);
    }

    var timer = null;
    window.addEventListener("scroll", function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        var anchor = readingAnchor();
        save(KEY_POS, JSON.stringify({
          slug: slug,
          title: body.dataset.title,
          index: anchor ? anchor.index : 0
        }));
      }, 300);
    }, { passive: true });
  }

  var resume = document.querySelector(".resume");
  if (resume) {
    var pos = readPos();
    if (pos && pos.slug && pos.title) {
      var link = resume.querySelector("a");
      link.href = pos.slug + ".html";
      link.textContent = "Đọc tiếp: " + pos.title;
      resume.hidden = false;
    }
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

  /* ---------- phim mui ten de chuyen chuong */

  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.target.closest("input, textarea, select, [contenteditable]")) return;
    var rel = e.key === "ArrowRight" ? "next" : e.key === "ArrowLeft" ? "prev" : null;
    if (!rel) return;
    var link = document.querySelector('.chapter-nav a[rel="' + rel + '"]');
    if (link) location.href = link.href;
  });
})();
