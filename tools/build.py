"""Sinh trang web doc sach (site/) va ban in (print/sach.html) tu data/book.json.

Chay: python tools/build.py
"""
import html
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PRINT = ROOT / "print"

BOOK = json.loads((ROOT / "data" / "book.json").read_text(encoding="utf-8"))

HEAD_SCRIPT = """<script>
(function () {
  var d = document.documentElement;
  try {
    var t = localStorage.getItem("tth-theme");
    if (t === "dark" || t === "light") d.dataset.theme = t;
    var s = localStorage.getItem("tth-size");
    if (s) d.dataset.size = s;
  } catch (e) {}
})();
</script>"""


def esc(s):
    return html.escape(s, quote=False)


def slugify(text):
    t = unicodedata.normalize("NFD", text.replace("Đ", "D").replace("đ", "d"))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:60].rstrip("-")


def runs_html(runs, seen_refs, link_notes=True):
    out = []
    for i, r in enumerate(runs):
        if r.get("br"):
            # bo khoang trang dinh vao truoc dong moi
            if out:
                out[-1] = out[-1].rstrip()
            out.append("<br>")
            continue
        if "ref" in r:
            n = r["ref"]
            # so chu thich dinh lien vao chu dung truoc
            if out:
                out[-1] = out[-1].rstrip()
            if not link_notes:
                out.append(f"<sup>{n}</sup>")
                continue
            rid = f' id="ref-{n}"' if n not in seen_refs else ""
            seen_refs.add(n)
            out.append(
                f'<sup><a class="fn" href="#chu-thich-{n}"{rid} data-n="{n}" '
                f'aria-label="Chú thích {n}">{n}</a></sup>')
            continue
        if r.get("sup"):
            out.append(f"<sup>{esc(r['t'])}</sup>")
            continue
        t = r["t"]
        if out and out[-1] == "<br>":
            t = t.lstrip()
        lead = t[: len(t) - len(t.lstrip())]
        trail = t[len(t.rstrip()):]
        core = esc(t.strip())
        if not core:
            out.append(" " if t else "")
            continue
        if r.get("i"):
            core = f"<em>{core}</em>"
        if r.get("b"):
            core = f"<strong>{core}</strong>"
        out.append((" " if lead else "") + core + (" " if trail else ""))
    s = "".join(out)
    s = re.sub(r" {2,}", " ", s)
    s = s.replace("</em> <em>", " ").replace("</strong> <strong>", " ")
    return s.strip()


def page(title, body, slug=None, extra_body_attrs=""):
    slug_attr = f' data-slug="{slug}"' if slug else ""
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">
<title>{esc(title)}</title>
{HEAD_SCRIPT}
<link rel="stylesheet" href="assets/style.css">
</head>
<body{slug_attr}{extra_body_attrs}>
{body}
<script src="assets/reader.js"></script>
</body>
</html>
"""


def bar(show_toc=True, show_size=True):
    left = '<a class="bar-link" href="index.html">Mục lục</a>' if show_toc else "<span></span>"
    size = ('<span class="size" role="group" aria-label="Cỡ chữ">'
            '<button type="button" data-action="smaller" aria-label="Chữ nhỏ hơn">A−</button>'
            '<button type="button" data-action="larger" aria-label="Chữ lớn hơn">A+</button>'
            '</span>') if show_size else ""
    return f"""<header class="bar">
  {left}
  <div class="bar-tools">
    {size}
    <button type="button" class="theme" data-action="theme">Nền đen</button>
  </div>
</header>"""


def render_blocks(ch, seen_refs, link_notes=True, id_prefix=""):
    parts = []
    used_ids = set()
    prev_verse = False
    for bl in ch["blocks"]:
        t = bl["type"]
        if t in ("h2", "h3", "h4"):
            hid = id_prefix + (slugify(bl.get("nav") or bl["text"]) or bl["id"])
            while hid in used_ids:
                hid += "-2"
            used_ids.add(hid)
            bl["_hid"] = hid
            parts.append(f'<{t} id="{hid}">{esc(bl["text"])}</{t}>')
        elif t == "break":
            parts.append('<div class="break" aria-hidden="true"><span>*</span><span>*&#8195;*</span></div>')
        else:
            inner = runs_html(bl["runs"], seen_refs, link_notes)
            first = next((r["t"] for r in bl["runs"] if r.get("t", "").strip()), "")
            if bl.get("verse"):
                lines = [ln.strip() for ln in inner.split("<br>")]
                inner = "".join(f'<span class="line">{ln}</span>' for ln in lines if ln)
                parts.append(f'<p class="verse">{inner}</p>')
            elif prev_verse and re.match(r"^\W*[a-zà-ỹđ]", first):
                # cau van noi tiep ngay sau doan tho
                parts.append(f'<p class="cont">{inner}</p>')
            else:
                parts.append(f"<p>{inner}</p>")
        prev_verse = t == "p" and bool(bl.get("verse"))
    return "\n".join(parts)


def contents_html(ch):
    items = []
    for bl in ch["blocks"]:
        if bl["type"] in ("h2", "h3"):
            label = bl.get("nav") or bl["text"]
            if bl.get("nav"):
                label = f'{bl["text"]}. {bl["nav"]}'
            cls = "sub" if bl["type"] == "h3" else ""
            items.append(f'<li class="{cls}"><a href="#{bl["_hid"]}">{esc(label)}</a></li>')
    if not items:
        return ""
    return ('<details class="contents">\n<summary>Trong chương này</summary>\n<ul>\n'
            + "\n".join(items) + "\n</ul>\n</details>")


def notes_html(ch, link_back=True, id_prefix=""):
    if not ch["notes"]:
        return ""
    lis = []
    for n in ch["notes"]:
        num = n["n"]
        text = runs_html(n["runs"], set())
        if link_back:
            numhtml = f'<a href="#ref-{num}" aria-label="Quay lại đoạn có chú thích {num}">{num}</a>'
        else:
            numhtml = str(num)
        lis.append(f'<li id="{id_prefix}chu-thich-{num}"><span class="note-n">{numhtml}</span>'
                   f'<span class="note-text">{text}</span></li>')
    return ('<section class="notes" aria-labelledby="chu-thich">\n'
            f'<h2 id="{id_prefix}chu-thich">Chú thích</h2>\n<ol>\n' + "\n".join(lis) + "\n</ol>\n</section>")


def opener(ch, tag="h1"):
    label = f'<p class="label">{esc(ch["label"])}</p>' if ch["label"] else ""
    return f'{label}<{tag} class="title">{esc(ch["title"])}</{tag}>'


def build_chapters():
    chs = BOOK["chapters"]
    for i, ch in enumerate(chs):
        seen = set()
        text = render_blocks(ch, seen)
        contents = contents_html(ch)
        notes = notes_html(ch)
        prev_ch = chs[i - 1] if i > 0 else None
        next_ch = chs[i + 1] if i + 1 < len(chs) else None
        nav = []
        if next_ch:
            nav.append(f'<a class="next" href="{next_ch["slug"]}.html" rel="next">'
                       f'<span class="dir">Chương sau</span>'
                       f'<span class="nav-title">{esc(next_ch["title"])}</span></a>')
        else:
            nav.append('<a class="next" href="index.html">'
                       '<span class="dir">Hết sách</span>'
                       '<span class="nav-title">Về mục lục</span></a>')
        if prev_ch:
            nav.append(f'<a class="prev" href="{prev_ch["slug"]}.html" rel="prev">'
                       f'<span class="dir">Chương trước</span>'
                       f'<span class="nav-title">{esc(prev_ch["title"])}</span></a>')
        kind = ' data-kind="list"' if ch["slug"] == "phu-luc" else ""
        body = f"""{bar()}
<main class="page">
<header class="opener">
{opener(ch)}
</header>
{contents}
<article class="text"{kind}>
{text}
</article>
{notes}
<nav class="chapter-nav" aria-label="Chuyển chương">
{chr(10).join(nav)}
</nav>
</main>"""
        title = (f'{ch["label"]}: {ch["title"]}' if ch["label"] else ch["title"]) + " | Tôi tự học"
        attrs = f' data-title="{html.escape(ch["title"])}"'
        (SITE / f'{ch["slug"]}.html').write_text(page(title, body, ch["slug"], attrs), encoding="utf-8")


def build_index():
    items = []
    for ch in BOOK["chapters"]:
        label = f'<span class="toc-label">{esc(ch["label"])}</span>' if ch["label"] else ""
        items.append(f'<li><a href="{ch["slug"]}.html" data-slug="{ch["slug"]}">{label}'
                     f'<span class="toc-title">{esc(ch["title"])}</span></a></li>')
    body = f"""{bar(show_toc=False, show_size=False)}
<main class="page">
<header class="cover">
<h1>{esc(BOOK["title"])}</h1>
<p class="author">{esc(BOOK["author"])}</p>
<p class="edition">{esc(BOOK["publisher"])}, {BOOK["year"]}</p>
</header>
<p class="resume" hidden><a href="#"></a></p>
<nav aria-label="Mục lục">
<ul class="toc">
{chr(10).join(items)}
</ul>
</nav>
<footer class="credits">
<p>{esc(BOOK["credits"])}</p>
</footer>
</main>"""
    (SITE / "index.html").write_text(page(BOOK["title"], body), encoding="utf-8")


def build_print():
    """Mot file HTML chua ca cuon sach, dung de in ra PDF kho A5."""
    parts = []
    toc = []
    for ch in BOOK["chapters"]:
        pre = ch["slug"] + "-"
        text = render_blocks(ch, set(), link_notes=False, id_prefix=pre)
        notes = notes_html(ch, link_back=False, id_prefix=pre)
        parts.append(f'<section class="chapter" id="{ch["slug"]}">\n'
                     f'<header class="opener">{opener(ch, "h1")}</header>\n'
                     f'<div class="text"{" data-kind=\"list\"" if ch["slug"] == "phu-luc" else ""}>\n{text}\n</div>\n{notes}\n</section>')
        label = f'<span class="toc-label">{esc(ch["label"])}</span>' if ch["label"] else ""
        toc.append(f'<li><a href="#{ch["slug"]}">{label}<span class="toc-title">{esc(ch["title"])}</span></a></li>')
    doc = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{esc(BOOK["title"])}</title>
<meta name="author" content="{esc(BOOK["author"])}">
<link rel="stylesheet" href="fonts/fonts.css">
<link rel="stylesheet" href="print.css">
</head>
<body>
<section class="cover">
<h1>{esc(BOOK["title"])}</h1>
<p class="author">{esc(BOOK["author"])}</p>
<p class="edition">{esc(BOOK["publisher"])}, {BOOK["year"]}</p>
<p class="credits">{esc(BOOK["credits"])}</p>
</section>
<nav class="toc-page">
<h2>Mục lục</h2>
<ul class="toc">
{chr(10).join(toc)}
</ul>
</nav>
{chr(10).join(parts)}
</body>
</html>
"""
    PRINT.mkdir(exist_ok=True)
    (PRINT / "sach.html").write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    SITE.mkdir(exist_ok=True)
    build_chapters()
    build_index()
    build_print()
    print("Da sinh", len(BOOK["chapters"]), "chuong vao", SITE, "va ban in vao", PRINT)
