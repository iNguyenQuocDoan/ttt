"""Doc PDF goc "Toi Tu Hoc" va xuat noi dung sach thanh data/book.json.

PDF goc tron font Times New Roman nhung (Identity-H) voi font khong nhung
(WinAnsi), nen cac doan chu cua mot dong co the bi tach thanh nhieu "line"
lech vi tri. Vi vay o day gom theo hang (baseline) chu khong tin vao block.

Chay: python tools/extract.py "<duong-dan-pdf>"
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
FIRST_PAGE = 3          # trang 1-2 la muc luc cua ban ebook
PARA_GAP = 17.5         # khoang cach baseline lon hon muc nay => doan moi
FULL_LINE_X1 = 536      # dong cham le phai => doan con tiep o trang sau

CH8_SECTIONS = [
    "Nguyên tắc thứ nhất: Đi từ dễ đến khó",
    "Nguyên tắc thứ hai: Làm việc đều đều không gián đoạn",
    "Nguyên tắc thứ ba: Khởi đầu bằng những yếu tố đầu tiên",
    "Nguyên tắc thứ tư: Biết lựa chọn",
    "Nguyên tắc thứ năm: Quý thời giờ làm việc và đặt cho nó thành một kỉ luật",
    "Nguyên tắc thứ sáu: Biết dùng thời giờ làm việc và tiết kiệm từng phút một",
    "Nguyên tắc thứ bảy: Làm việc gì thì làm cho hoàn tất",
    "Nguyên tắc thứ tám: Có một sức khỏe dồi dào",
]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def style_of(span):
    f = span["font"]
    return {"b": "Bold" in f, "i": "Ital" in f}


def is_blank(t):
    return t.strip() == ""


# ---------------------------------------------------------------- page rows

def page_rows(page):
    """Tra ve (body_rows, note_rows). Moi row: dict(base, x0, x1, spans)."""
    lines = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for ln in b["lines"]:
            spans = [s for s in ln["spans"] if s["text"] != ""]
            if not spans or all(is_blank(s["text"]) for s in spans):
                continue
            sizes = [round(s["size"], 1) for s in spans if not is_blank(s["text"])]
            big = [s for s in spans if s["size"] >= 9.5]
            base = max(s["origin"][1] for s in (big or spans))
            kind = "body"
            if max(sizes) < 11.5 and any(9.5 <= z <= 10.5 for z in sizes):
                kind = "note"
            elif all(7.9 <= z <= 9.1 for z in sizes) and not any(9.5 <= z <= 10.5 for z in sizes):
                kind = "sup"
            lines.append({
                "kind": kind, "base": base,
                "x0": min(s["bbox"][0] for s in spans if not is_blank(s["text"])),
                "x1": max(s["bbox"][2] for s in spans if not is_blank(s["text"])),
                "spans": spans,
            })

    def cluster(ls):
        rows = []
        for ln in sorted(ls, key=lambda l: l["base"]):
            if rows and abs(ln["base"] - rows[-1]["base"]) <= 3:
                rows[-1]["lines"].append(ln)
            else:
                rows.append({"base": ln["base"], "lines": [ln]})
        return rows

    body = cluster([l for l in lines if l["kind"] == "body"])
    notes = cluster([l for l in lines if l["kind"] == "note"])

    # so chu thich nho dung rieng mot block: gan vao hang ngay ben duoi no
    for sup in [l for l in lines if l["kind"] == "sup"]:
        best = None
        for r in body:
            d = r["base"] - sup["base"]
            if -1 <= d <= 9 and (best is None or d < best[0]):
                best = (d, r)
        if best:
            best[1]["lines"].append(sup)

    def finish(r):
        r["lines"].sort(key=lambda l: (l["x0"] + l["x1"]) / 2)
        r["spans"] = [s for l in r["lines"] for s in l["spans"]]
        r["x0"] = min(l["x0"] for l in r["lines"])
        r["x1"] = max(l["x1"] for l in r["lines"])
        r["text"] = "".join(s["text"] for s in r["spans"])
        return r

    return [finish(r) for r in body], [finish(r) for r in notes]


# ---------------------------------------------------------------- runs

def spans_to_runs(spans, notes_mode=False):
    runs = []
    for s in spans:
        t = s["text"]
        z = round(s["size"], 1)
        st = style_of(s)
        if not notes_mode and 7.9 <= z <= 9.1 and not is_blank(t):
            t = t.strip()
            if t.isdigit():
                runs.append({"t": t, "ref": int(t)})
            else:
                runs.append({"t": t, "sup": True})
            continue
        if is_blank(t):
            st = {"b": False, "i": False}
        runs.append({"t": t, "b": st["b"], "i": st["i"]})
    return runs


def merge_runs(runs):
    out = []
    for r in runs:
        plain = lambda x: "t" in x and "ref" not in x and "sup" not in x
        if out and plain(r) and plain(out[-1]):
            prev = out[-1]
            if prev["b"] == r["b"] and prev["i"] == r["i"]:
                prev["t"] += r["t"]
                continue
            # khoang trang dung giua hai run cung kieu -> gop vao run truoc
            if is_blank(r["t"]):
                prev["t"] += r["t"]
                continue
        out.append(dict(r))
    return out


# ---------------------------------------------------------------- headings

def heading_kind(row):
    real = [s for s in row["spans"] if not is_blank(s["text"])]
    arial = any("Arial" in s["font"] for s in real)
    size = max(s["size"] for s in real)
    bold = all("Bold" in s["font"] for s in real)
    ital = all("Ital" in s["font"] for s in real)
    if arial:
        if size >= 15.5:
            return "title"
        if size >= 13.5 and ital:
            return "h2"
        if size >= 13.5:
            txt = row["text"].strip()
            if txt in ROMAN:
                return "h2"
            return "label"
        return "h3"
    if size >= 13.5 and bold:
        return "h4" if ital else "h3"
    return None


def sentence_case(text):
    text = re.sub(r"\s+", " ", text).strip()
    if text in ROMAN:
        return text
    m = re.match(r"^((?:[A-ZĐ]|\d+)\.\s*)?(.*)$", text)
    prefix, rest = m.group(1) or "", m.group(2)
    if rest.upper() != rest:          # da co chu thuong -> giu nguyen
        return prefix + rest
    rest = rest.lower()
    rest = re.sub(r"^([“\"«(]*)(\w)", lambda k: k.group(1) + k.group(2).upper(), rest)
    return prefix + rest


# ---------------------------------------------------------------- text fixes

def tidy(text):
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +([,.;])", r"\1", text)
    text = re.sub(r"“ +", "“", text)
    text = re.sub(r" +”", "”", text)
    text = re.sub(r"\( +", "(", text)
    text = re.sub(r" +\)", ")", text)
    return text


def load_fixes():
    path = ROOT / "tools" / "fixes.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


# ---------------------------------------------------------------- main

def main(pdf_path):
    doc = pymupdf.open(pdf_path)
    items = []   # luong phan tu theo thu tu doc
    notes = {}   # so chu thich -> runs
    last_note = None

    for pno in range(FIRST_PAGE - 1, doc.page_count):
        body, note_rows = page_rows(doc[pno])
        for r in note_rows:
            runs = spans_to_runs(r["spans"], notes_mode=True)
            first = next((s for s in r["spans"] if not is_blank(s["text"])), None)
            if first and first["size"] < 9.3 and first["text"].strip().isdigit():
                # mot hang co the chua nhieu chu thich: tach theo so nho
                cur = None
                for s in r["spans"]:
                    if s["size"] < 9.3 and s["text"].strip().isdigit():
                        cur = int(s["text"].strip())
                        notes[cur] = []
                        last_note = cur
                        continue
                    if cur is not None:
                        notes[cur].extend(spans_to_runs([s], notes_mode=True))
            elif last_note is not None:
                notes[last_note].append({"t": " ", "b": False, "i": False})
                notes[last_note].extend(runs)

        for r in body:
            txt = r["text"].strip()
            if txt.replace("*", "").strip() == "":
                items.append({"type": "break", "page": pno + 1})
                continue
            if pno + 1 == 112 and txt == "II":
                continue
            if pno + 1 == 112 and txt == "GHI CHÚ":
                items.append({"type": "h2", "text": "Ghi chú", "page": pno + 1})
                continue
            hk = heading_kind(r)
            if hk:
                items.append({"type": hk, "text": r["text"], "page": pno + 1})
                continue
            items.append({
                "type": "row", "page": pno + 1, "base": r["base"],
                "x0": r["x0"], "x1": r["x1"], "text": r["text"],
                "runs": spans_to_runs(r["spans"]),
            })

    # gop tieu de nhieu dong
    merged = []
    for it in items:
        if merged and it["type"] in ("title", "h2", "h3", "h4", "label") \
                and merged[-1]["type"] == it["type"] and merged[-1]["text"].strip() not in ROMAN \
                and it["text"].strip() not in ROMAN:
            merged[-1]["text"] = merged[-1]["text"].rstrip() + " " + it["text"].strip()
            continue
        merged.append(dict(it))
    items = merged

    # dung doan van
    blocks = []
    para = None
    prev_row = None

    def close():
        nonlocal para
        if para:
            blocks.append(para)
        para = None

    for it in items:
        if it["type"] != "row":
            close()
            prev_row = None
            if it["type"] == "break" and blocks and blocks[-1]["type"] == "break":
                continue
            blocks.append(it)
            continue
        new_para = True
        line_break = False
        if para and prev_row:
            if it["page"] == prev_row["page"]:
                gap = it["base"] - prev_row["base"]
                new_para = gap > PARA_GAP
            else:
                starts_lower = bool(re.match(r"^\W*[a-zà-ỹđ]", it["text"].strip()))
                new_para = not (prev_row["x1"] >= FULL_LINE_X1 or starts_lower)
            if not new_para:
                indented = it["x0"] > 80 or re.match(r"^ {3,}", it["text"])
                line_break = bool(indented) or (prev_row["x1"] < 470 and it["page"] == prev_row["page"])
        if new_para:
            close()
            para = {"type": "p", "runs": [], "page": it["page"],
                    "indent": it["x0"] > 80}
        else:
            if line_break:
                para["runs"].append({"br": True})
            else:
                para["runs"].append({"t": " ", "b": False, "i": False})
        runs = [dict(r) for r in it["runs"]]
        if runs and "t" in runs[0] and "ref" not in runs[0]:
            runs[0]["t"] = runs[0]["t"].lstrip()
        para["runs"].extend(runs)
        prev_row = it
    close()

    # chia chuong
    chapters = []
    pending_label = None
    for bl in blocks:
        t = bl["type"]
        if t == "label":
            pending_label = sentence_case(bl["text"])
            continue
        if t == "title":
            title = sentence_case(bl["text"])
            chapters.append({"label": pending_label, "title": title,
                             "page": bl["page"], "blocks": []})
            pending_label = None
            continue
        if not chapters:
            continue
        chapters[-1]["blocks"].append(bl)

    fixes = load_fixes()
    slugs = ["tua", "chuong-1", "chuong-2", "chuong-3", "chuong-4", "chuong-5",
             "chuong-6", "chuong-7", "chuong-8", "ket-luan", "phu-luc"]
    out = []
    for idx, ch in enumerate(chapters):
        ch_blocks = []
        roman_i = 0
        sec_i = 0
        note_ids = []
        for bl in ch["blocks"]:
            if bl["type"] in ("h2", "h3", "h4"):
                txt = sentence_case(bl["text"])
                sec_i += 1
                nav = None
                if txt in ROMAN and ch["label"] == "Chương thứ tám":
                    nav = CH8_SECTIONS[roman_i]
                    roman_i += 1
                ch_blocks.append({"type": bl["type"], "text": txt, "id": f"m{sec_i}",
                                  **({"nav": nav} if nav else {})})
            elif bl["type"] == "break":
                ch_blocks.append({"type": "break"})
            else:
                runs = merge_runs(bl["runs"])
                for r in runs:
                    if "t" in r and "ref" not in r:
                        r["t"] = tidy(r["t"])
                    if "ref" in r:
                        note_ids.append(r["ref"])
                # bo khoang trang dau/cuoi doan
                while runs and "t" in runs[0] and is_blank(runs[0]["t"]) and "ref" not in runs[0]:
                    runs.pop(0)
                while runs and "t" in runs[-1] and is_blank(runs[-1]["t"]) and "ref" not in runs[-1]:
                    runs.pop()
                if runs and "t" in runs[0]:
                    runs[0]["t"] = runs[0]["t"].lstrip()
                if runs and "t" in runs[-1] and "ref" not in runs[-1]:
                    runs[-1]["t"] = runs[-1]["t"].rstrip()
                ch_blocks.append({"type": "p", "runs": runs,
                                  **({"verse": True} if bl.get("indent") else {})})
        ch_notes = []
        for n in note_ids:
            if n in notes:
                rr = merge_runs(notes[n])
                for r in rr:
                    if "t" in r:
                        r["t"] = tidy(r["t"])
                if rr:
                    rr[0]["t"] = rr[0]["t"].lstrip()
                    rr[-1]["t"] = rr[-1]["t"].rstrip()
                ch_notes.append({"n": n, "runs": rr})
        out.append({"slug": slugs[idx], "label": ch["label"], "title": ch["title"],
                    "blocks": ch_blocks, "notes": ch_notes})

    # ap dung danh sach sua loi chu (fixes.json): [{"from": "...", "to": "..."}]
    applied = {f["from"]: 0 for f in fixes}
    for ch in out:
        for bl in ch["blocks"] + [{"runs": n["runs"]} for n in ch["notes"]]:
            for r in bl.get("runs", []):
                if "t" in r and "ref" not in r and "sup" not in r:
                    for f in fixes:
                        if f["from"] in r["t"]:
                            applied[f["from"]] += r["t"].count(f["from"])
                            r["t"] = r["t"].replace(f["from"], f["to"])
    missing = [k for k, v in applied.items() if v == 0]
    if missing:
        print("fixes khong khop:", missing, file=sys.stderr)

    book = {
        "title": "Tôi tự học",
        "author": "Thu Giang Nguyễn Duy Cần",
        "publisher": "Khai Trí",
        "year": 1971,
        "credits": "Đánh máy: Chanquangtu, Readman. Sửa lỗi và bổ sung: Goldfish, Tuanz.",
        "chapters": out,
    }
    for ch in book["chapters"]:
        for bl in ch["blocks"]:
            for r in bl.get("runs", []):
                if "t" in r:
                    r["t"] = unicodedata.normalize("NFC", r["t"])
    dest = ROOT / "data" / "book.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(out)} phan, {sum(len(c['blocks']) for c in out)} khoi, "
          f"{len(notes)} chu thich -> {dest}")


if __name__ == "__main__":
    main(sys.argv[1])
