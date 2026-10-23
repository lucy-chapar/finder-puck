"""
Lays out the build guide and prints it to PDF.

    python3 manual/build_manual.py            # -> docs/finder_puck_build_guide.pdf
    python3 manual/build_manual.py --html     # only write build_guide.html (open it in a browser)

Pictures come from render_manual.py (run that first, in FreeCAD).  The layout is plain HTML/CSS
with absolute positions in millimetres on A4 pages; Google Chrome prints it headless.
"""

import html
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manual_steps as ms   # noqa: E402

MANUAL = os.path.dirname(os.path.abspath(__file__))
PUCK = os.path.dirname(MANUAL)
IMG = os.path.join(MANUAL, "img")
OUT_HTML = os.path.join(MANUAL, "build_guide.html")
OUT_PDF = os.path.join(PUCK, "docs", "finder_puck_build_guide.pdf")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAGE_W, PAGE_H = 210.0, 297.0
MARGIN = 15.0
CONTENT_W = PAGE_W - 2 * MARGIN
FOOT_Y = 283.0
TEAL = "#1ba8c9"
INK = "#1d1d1f"
GREY = "#7a7a7e"
RULE = "#c9c9cc"

SCENES = json.load(open(os.path.join(IMG, "scenes.json")))


def esc(s):
    return html.escape(s, quote=True)


def fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


# --- Tool icons (100 x 100 viewBox) -------------------------------------------------------
_S = 'fill="none" stroke="#333" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"'
ICONS = {
    "hexkey": '<path d="M30 20 L30 82 M30 20 L62 20" stroke="#222" stroke-width="11" stroke-linecap="round" fill="none"/>',
    "iron": '<path d="M12 88 L44 56" %s/><rect x="38" y="30" width="22" height="40" rx="6" transform="rotate(45 49 50)" fill="#555" stroke="#222" stroke-width="3"/>'
            '<path d="M62 38 L84 16" stroke="#777" stroke-width="5" stroke-linecap="round"/><circle cx="86" cy="14" r="3" fill="%s"/>' % (_S, TEAL),
    "flux": '<circle cx="36" cy="56" r="24" %s/><circle cx="36" cy="56" r="14" %s/><path d="M60 56 L78 56" %s/>'
            '<rect x="66" y="20" width="22" height="30" rx="4" fill="#e8e8e8" stroke="#333" stroke-width="3"/><path d="M72 20 L72 10 L82 10 L82 20" %s/>' % (_S, _S, _S, _S),
    "tweezers": '<path d="M38 14 L50 86 M62 14 L50 86" stroke="#333" stroke-width="6" stroke-linecap="round" fill="none"/><path d="M38 14 L62 14" stroke="#333" stroke-width="6" stroke-linecap="round"/>',
    "glue": '<path d="M40 40 L60 40 L66 90 L34 90 Z" fill="#e8e8e8" stroke="#333" stroke-width="3" stroke-linejoin="round"/><rect x="44" y="26" width="12" height="14" fill="#333"/><path d="M50 26 L50 10" stroke="#333" stroke-width="4" stroke-linecap="round"/><circle cx="50" cy="8" r="3" fill="%s"/>' % TEAL,
    "loupe": '<circle cx="42" cy="42" r="26" fill="#eef7fa" stroke="#333" stroke-width="5"/><path d="M62 62 L88 88" stroke="#333" stroke-width="9" stroke-linecap="round"/>',
    "meter": '<rect x="22" y="14" width="56" height="72" rx="6" fill="#e8e8e8" stroke="#333" stroke-width="3"/><rect x="30" y="22" width="40" height="18" fill="#cfe9f0"/><circle cx="50" cy="60" r="12" fill="none" stroke="#333" stroke-width="3"/><path d="M50 60 L58 52" stroke="#333" stroke-width="3"/><path d="M34 86 L26 98 M66 86 L74 98" stroke="#d33" stroke-width="4" stroke-linecap="round"/>',
    "ipa": '<path d="M36 36 L64 36 L68 92 L32 92 Z" fill="#e8e8e8" stroke="#333" stroke-width="3" stroke-linejoin="round"/><rect x="42" y="12" width="16" height="24" fill="#555"/><rect x="38" y="52" width="24" height="22" fill="#fff" stroke="#333" stroke-width="2"/>',
    "tape": '<circle cx="50" cy="50" r="34" fill="#e2b04a" stroke="#333" stroke-width="3"/><circle cx="50" cy="50" r="18" fill="#fff" stroke="#333" stroke-width="3"/>',
    "pen": '<path d="M28 86 L36 62 L72 14 L84 22 L48 70 Z" fill="#f08a24" stroke="#333" stroke-width="3" stroke-linejoin="round"/><path d="M36 62 L48 70" stroke="#333" stroke-width="3"/>',
    "usb": '<rect x="34" y="12" width="32" height="26" rx="6" fill="#e8e8e8" stroke="#333" stroke-width="3"/><rect x="42" y="38" width="16" height="12" fill="#555"/>'
           '<path d="M50 50 L50 70 Q50 84 36 84 L14 84" %s/><rect x="40" y="18" width="20" height="8" rx="4" fill="#bbb"/>' % _S,
    "uv": '<rect x="14" y="40" width="44" height="20" rx="4" fill="#555" stroke="#222" stroke-width="3"/><path d="M58 36 L66 36 L66 64 L58 64 Z" fill="#888" stroke="#222" stroke-width="3"/>'
          '<path d="M70 42 L90 30 M70 50 L92 50 M70 58 L90 70" stroke="#7a3cff" stroke-width="5" stroke-linecap="round"/>',
}


def icon_svg(name, size_mm):
    return '<svg viewBox="0 0 100 100" style="width:%smm;height:%smm">%s</svg>' % (fmt(size_mm), fmt(size_mm), ICONS[name])


# --- Page helpers ---------------------------------------------------------------------------

def box(x, y, w, h, content, cls="", style=""):
    return '<div class="abs %s" style="left:%smm;top:%smm;width:%smm;height:%smm;%s">%s</div>' % (
        cls, fmt(x), fmt(y), fmt(w), fmt(h), style, content)


def text(x, y, w, content, cls="", style=""):
    return '<div class="abs %s" style="left:%smm;top:%smm;width:%smm;%s">%s</div>' % (cls, fmt(x), fmt(y), fmt(w), style, content)


def logo(x, y, h, wordmark=True, cls=""):
    out = '<img class="abs" src="%s" style="left:%smm;top:%smm;height:%smm">' % (ms.BRAND["logo"], fmt(x), fmt(y), fmt(h))
    if wordmark:
        out += text(x + h * 1.08, y + h * 0.2, 90, esc(ms.BRAND["name"]), "wordmark " + cls,
                    "font-size:%spt;line-height:%smm" % (fmt(h * 1.05), fmt(h * 0.6)))
    return out


def footer(page_no):
    return (text(MARGIN, FOOT_Y, 90, "%s %s &nbsp;&middot;&nbsp; v%s" % (esc(ms.TITLE), esc(ms.SUBTITLE), ms.VERSION), "foot")
            + text(0, FOOT_Y - 1.2, PAGE_W, str(page_no), "pageno")
            + logo(PAGE_W - MARGIN - 36, FOOT_Y - 0.6, 5.2, cls="small"))


def heading(y, title):
    return text(MARGIN, y, CONTENT_W, esc(title), "h1")


def group_rule(y, title):
    w = 4.1 * len(title) + 2
    return (text(MARGIN, y, CONTENT_W, esc(title), "h2")
            + box(MARGIN + w + 4, y + 4.6, CONTENT_W - w - 4, 0.4, "", "", "background:%s" % RULE))


def picture(scene, x, y, w, h):
    """Place a render inside the box (contain); return the HTML and a px->mm mapper."""
    sc = SCENES[scene]
    iw, ih = sc["W"], sc["H"]
    s = min(w / iw, h / ih)
    dw, dh = iw * s, ih * s
    ox, oy = x + (w - dw) / 2, y + (h - dh) / 2
    img = '<img class="abs" src="img/%s" style="left:%smm;top:%smm;width:%smm;height:%smm">' % (sc["file"], fmt(ox), fmt(oy), fmt(dw), fmt(dh))

    def to_mm(px):
        return ox + px[0] * s, oy + px[1] * s
    return img, to_mm, (ox, oy, dw, dh)


# --- SVG overlay: arrows and magnifiers -----------------------------------------------------

def arrow(p0, p1, curved=False):
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return ""
    ux, uy = dx / L, dy / L
    head = 3.4
    # shorten at the tip so the head's point lands on the target
    bx, by = x1 - ux * head, y1 - uy * head
    nx, ny = -uy, ux
    if curved:
        cx, cy = (x0 + x1) / 2 + nx * L * 0.35, (y0 + y1) / 2 + ny * L * 0.35
        path = "M%s %s Q%s %s %s %s" % (fmt(x0), fmt(y0), fmt(cx), fmt(cy), fmt(bx), fmt(by))
        # head direction from the control point
        hx, hy = bx - cx, by - cy
        hl = math.hypot(hx, hy)
        ux, uy = hx / hl, hy / hl
        nx, ny = -uy, ux
        x1, y1 = bx + ux * head, by + uy * head
    else:
        path = "M%s %s L%s %s" % (fmt(x0), fmt(y0), fmt(bx), fmt(by))
    tri = "%s,%s %s,%s %s,%s" % (fmt(x1), fmt(y1), fmt(bx + nx * 2.0), fmt(by + ny * 2.0), fmt(bx - nx * 2.0), fmt(by - ny * 2.0))
    return ('<path d="%s" class="halo"/><path d="%s" class="arrow"/>'
            '<polygon points="%s" class="halo-fill"/><polygon points="%s" class="arrow-fill"/>' % (path, path, tri, tri))


def magnifier(zoom_scene, target, corner, label, area):
    """A round call-out at a corner of the picture area, joined to the target point."""
    ax, ay, aw, ah = area
    r = 23.0
    cx = ax + r + 1 if corner[1] == "l" else ax + aw - r - 1
    cy = ay + r + 1 if corner[0] == "t" else ay + ah - r - 1
    sc = SCENES[zoom_scene]
    cid = "clip_%s" % zoom_scene
    # connector from the circle edge toward the target
    dx, dy = target[0] - cx, target[1] - cy
    L = math.hypot(dx, dy) or 1.0
    ex, ey = cx + dx / L * r, cy + dy / L * r
    out = '<line x1="%s" y1="%s" x2="%s" y2="%s" class="lead"/><circle cx="%s" cy="%s" r="1.3" class="lead-dot"/>' % (
        fmt(ex), fmt(ey), fmt(target[0]), fmt(target[1]), fmt(target[0]), fmt(target[1]))
    out += '<defs><clipPath id="%s"><circle cx="%s" cy="%s" r="%s"/></clipPath></defs>' % (cid, fmt(cx), fmt(cy), fmt(r - 0.3))
    out += '<image href="img/%s" x="%s" y="%s" width="%s" height="%s" clip-path="url(#%s)" preserveAspectRatio="xMidYMid slice"/>' % (
        sc["file"], fmt(cx - r), fmt(cy - r), fmt(2 * r), fmt(2 * r), cid)
    out += '<circle cx="%s" cy="%s" r="%s" class="mag"/>' % (fmt(cx), fmt(cy), fmt(r))
    if label:
        out += '<text x="%s" y="%s" class="maglabel">%s</text>' % (fmt(cx), fmt(cy - r + 7.5), esc(label))
    return out


# --- Pages --------------------------------------------------------------------------------

def page(content, cls=""):
    return '<section class="page %s">%s</section>' % (cls, content)


def cover_page():
    c = text(MARGIN, 14, 150, esc(ms.TITLE), "title")
    c += text(MARGIN, 34, 150, esc(ms.SUBTITLE), "subtitle")
    c += text(MARGIN, 48, 160, "%s &nbsp;&middot;&nbsp; Version %s" % (esc(ms.VARIANT), ms.VERSION), "variant")
    c += logo(PAGE_W - MARGIN - 62, 14, 10)
    img, _, _ = picture("cover", MARGIN - 6, 64, CONTENT_W + 12, 172)
    c += img
    c += box(MARGIN, 243, CONTENT_W, 0.4, "", "", "background:%s" % RULE)
    c += contact_block(MARGIN, 250)
    return page(c, "cover")


def contact_block(x, y):
    b = ms.BRAND
    qr = ""
    tx = x
    if b.get("docs_url") and os.path.exists(os.path.join(MANUAL, "img", "qr.png")):
        qr = '<img class="abs" src="img/qr.png" style="left:%smm;top:%smm;width:22mm;height:22mm">' % (fmt(x), fmt(y))
        tx = x + 28
    out = qr
    out += text(tx, y, 120, esc(b["support_label"]), "label")
    out += text(tx, y + 4.6, 120, esc(b["support"]), "link")
    docs = b["docs_url"] or b["docs"]
    out += text(tx, y + 12.4, 150, esc(b["docs_label"]), "label")
    out += text(tx, y + 17.0, 150, esc(docs), "link" if b["docs_url"] else "link plain")
    return out


def card(x, y, w, h, pic, qty, name, detail, icon=None):
    c = '<div class="card"></div>'
    inner = ""
    if icon:
        inner += '<div class="abs" style="left:%smm;top:%smm;width:%smm;text-align:center">%s</div>' % (fmt(x + 2), fmt(y + 3), fmt(w - 4), icon_svg(icon, min(w - 10, h - 20)))
    else:
        ph = h - 17 if qty is not None else h - 12
        sc = SCENES[pic]
        inner += '<img class="abs" src="img/%s" style="left:%smm;top:%smm;width:%smm;height:%smm;object-fit:contain">' % (
            sc["file"], fmt(x + 3), fmt(y + 2), fmt(w - 6), fmt(ph - 2))
    ty = y + h - 15.5 if qty is not None else y + h - 11
    if qty is not None:
        inner += text(x, ty, w, "%d&times;" % qty, "qty")
        ty += 7.2
    inner += text(x + 1.5, ty, w - 3, esc(name) + ('<br><span class="detail">%s</span>' % esc(detail) if detail else ""), "cardname")
    return box(x, y, w, h, c) + inner


def grid_pages(title, groups, items_of, per_row, card_w, card_h, gap, with_qty, icon=False, start_page=2):
    """Pages of card grids, one group heading per group; returns (html pages, next page number)."""
    pages, page_no = [], start_page
    y = 36.0
    content = heading(14, title)
    max_y = FOOT_Y - 10
    for key, label in groups:
        items = items_of(key)
        if not items:
            continue
        rows = math.ceil(len(items) / per_row)
        need = 11 + rows * (card_h + gap)
        if y + need > max_y and y > 36.0:
            pages.append(page(content + footer(page_no)))
            page_no += 1
            content, y = heading(14, title + " (continued)"), 36.0
        content += group_rule(y, label)
        y += 11
        total_w = per_row * card_w + (per_row - 1) * gap
        x0 = MARGIN + (CONTENT_W - total_w) / 2
        for i, it in enumerate(items):
            r, cidx = divmod(i, per_row)
            n_in_row = min(per_row, len(items) - r * per_row)
            row_w = n_in_row * card_w + (n_in_row - 1) * gap
            xr = MARGIN + (CONTENT_W - row_w) / 2
            cx = xr + cidx * (card_w + gap)
            cy = y + r * (card_h + gap)
            if icon:
                content += card(cx, cy, card_w, card_h, None, None, it[1], "", icon=it[2])
            else:
                g, name, qty, detail, pic = it
                content += card(cx, cy, card_w, card_h, pic, qty if with_qty else None, name, detail)
        y += rows * (card_h + gap) + 6
    pages.append(page(content + footer(page_no)))
    return pages, page_no + 1


def step_page(idx, step, page_no):
    sc = step["scene"]
    c = text(MARGIN - 1, 10, 40, str(idx), "stepno")
    # Parts box.
    parts = step["parts"]
    if parts:
        bw = min(CONTENT_W - 40, 24 + 34 * len(parts))
        bx = PAGE_W - MARGIN - bw
        c += box(bx, 14, bw, 46, '<div class="card"></div>')
        slot = (bw - 8) / len(parts)
        for i, (key, qty) in enumerate(parts):
            g, name, q, detail, pic = ms.PARTS[key]
            x = bx + 4 + i * slot
            c += '<img class="abs" src="img/%s" style="left:%smm;top:17mm;width:%smm;height:24mm;object-fit:contain">' % (SCENES[pic]["file"], fmt(x), fmt(slot))
            c += text(x, 42.5, slot, "%d&times;" % qty, "qty")
            c += text(x, 50.5, slot, esc(name), "cardname")
    # Picture with overlays.
    area_y = 66.0 if parts else 40.0
    area_h = FOOT_Y - 20 - area_y
    img, to_mm, area = picture(sc, MARGIN, area_y, CONTENT_W, area_h)
    c += img
    anchors = {k: to_mm(v) for k, v in SCENES[sc]["anchors"].items()}
    svg = ""
    for a, b, style in step.get("arrows", []):
        if a in anchors and b in anchors:
            svg += arrow(anchors[a], anchors[b], curved=(style == "curved"))
        else:
            print("step %d: arrow %s -> %s has no anchor in scene %s" % (idx, a, b, sc))
    for zoom, target, corner, label in step.get("mags", []):
        if zoom in SCENES and target in anchors:
            svg += magnifier(zoom, anchors[target], corner, label, area)
        else:
            print("step %d: magnifier %s at %s is missing (scene or anchor)" % (idx, zoom, target))
    c += '<svg class="overlay" viewBox="0 0 %s %s">%s</svg>' % (fmt(PAGE_W), fmt(PAGE_H), svg)
    # Note.
    if step.get("note"):
        nx = MARGIN
        if step.get("tool"):
            c += box(MARGIN, FOOT_Y - 17.5, 11, 11, icon_svg(step["tool"], 10))
            nx = MARGIN + 13
        c += text(nx, FOOT_Y - 16.5, PAGE_W - MARGIN - nx, esc(step["note"]), "note")
    return page(c + footer(page_no))


def before_page(page_no):
    c = heading(14, "Before you start")
    y = 36.0
    for title, body in ms.BEFORE:
        c += text(MARGIN, y, 34, esc(title), "h3")
        c += text(MARGIN + 36, y + 0.4, CONTENT_W - 36, esc(body), "body")
        y += 9 + 5.2 * (1 + len(body) // 95)
    return page(c + footer(page_no))


def done_page(page_no):
    c = heading(14, "Done")
    img, _, _ = picture("face", MARGIN + 20, 30, CONTENT_W - 40, 100)
    c += img
    c += text(MARGIN, 136, CONTENT_W, esc(ms.DONE_TEXT), "body")
    y = 158.0
    c += group_rule(y, "The button")
    y += 12
    for title, body in ms.DONE:
        c += text(MARGIN, y, 44, esc(title), "h3")
        c += text(MARGIN + 46, y + 0.4, CONTENT_W - 46, esc(body), "body")
        y += 10
    return page(c + footer(page_no))


def back_page(page_no):
    c = logo(PAGE_W / 2 - 55, 70, 20)
    c += text(0, 118, PAGE_W, "%s %s" % (esc(ms.TITLE), esc(ms.SUBTITLE)), "backtitle")
    c += text(0, 132, PAGE_W, "%s &nbsp;&middot;&nbsp; Version %s" % (esc(ms.VARIANT), ms.VERSION), "variant center")
    c += contact_block(PAGE_W / 2 - 50, 160)
    c += text(MARGIN, 215, CONTENT_W, esc("Open hardware. The design files (KiCad board, FreeCAD case, this guide) are generated "
                                           "from scripts; see the README before changing anything by hand."), "fine")
    return page(c + footer(page_no))


CSS = """
@page { size: A4; margin: 0; }
@font-face { font-family: 'DejaVu Sans'; src: url('assets/fonts/DejaVuSans.ttf'); font-weight: normal; }
@font-face { font-family: 'DejaVu Sans'; src: url('assets/fonts/DejaVuSans-Bold.ttf'); font-weight: bold; }
html, body { margin: 0; padding: 0; background: #fff; }
body { font-family: 'DejaVu Sans', sans-serif; color: %(ink)s; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { position: relative; width: 210mm; height: 297mm; overflow: hidden; page-break-after: always; break-after: page; }
.page:last-child { page-break-after: auto; }
.abs { position: absolute; }
.title { font-size: 44pt; font-weight: bold; line-height: 1; letter-spacing: -0.5pt; white-space: nowrap; }
.subtitle { font-size: 26pt; font-weight: bold; line-height: 1.1; white-space: nowrap; }
.variant { font-size: 13pt; color: %(grey)s; }
.center { text-align: center; }
.wordmark { font-weight: bold; color: #5c5c60; letter-spacing: 1.2pt; white-space: nowrap; }
.wordmark.small { letter-spacing: 0.6pt; }
.h1 { font-size: 30pt; font-weight: bold; line-height: 1; }
.h2 { font-size: 17pt; font-weight: bold; line-height: 1; }
.h3 { font-size: 10.5pt; font-weight: bold; line-height: 1.3; }
.body { font-size: 9.5pt; line-height: 1.4; color: #333; }
.card { position: absolute; left: 0; top: 0; width: 100%%; height: 100%%; box-sizing: border-box; border: 0.35mm solid #bfbfc3; border-radius: 3mm; background: #fff; }
.qty { font-size: 17pt; font-weight: bold; text-align: center; line-height: 1; }
.cardname { font-size: 8.5pt; text-align: center; line-height: 1.25; }
.detail { font-size: 7pt; color: %(grey)s; }
.stepno { font-size: 64pt; font-weight: bold; line-height: 1; }
.note { font-size: 9.5pt; line-height: 1.35; color: #333; }
.foot { font-size: 8.5pt; color: %(grey)s; }
.pageno { font-size: 12pt; font-weight: bold; color: #6a6a6e; text-align: center; }
.label { font-size: 9pt; color: %(grey)s; }
.link { font-size: 11.5pt; font-weight: bold; color: %(teal)s; }
.link.plain { font-weight: normal; color: #444; font-size: 10pt; }
.backtitle { font-size: 24pt; font-weight: bold; text-align: center; }
.fine { font-size: 8pt; color: %(grey)s; text-align: center; line-height: 1.4; }
.overlay { position: absolute; left: 0; top: 0; width: 210mm; height: 297mm; }
.arrow { fill: none; stroke: %(teal)s; stroke-width: 1.6; stroke-linecap: round; }
.halo { fill: none; stroke: #fff; stroke-width: 3.0; stroke-linecap: round; }
.arrow-fill { fill: %(teal)s; stroke: #0d6f86; stroke-width: 0.35; stroke-linejoin: round; }
.halo-fill { fill: #fff; stroke: #fff; stroke-width: 1.8; stroke-linejoin: round; }
.lead { stroke: #333; stroke-width: 0.35; }
.lead-dot { fill: #333; }
.mag { fill: none; stroke: #222; stroke-width: 0.7; }
.maglabel { font-family: 'DejaVu Sans'; font-weight: bold; font-size: 5.2px; text-anchor: middle; fill: #1d1d1f;
            paint-order: stroke; stroke: #fff; stroke-width: 1.4px; stroke-linejoin: round; }
""" % dict(ink=INK, grey=GREY, teal=TEAL)


def make_qr():
    url = ms.BRAND.get("docs_url")
    if not url:
        return
    src = os.path.join(MANUAL, "qr.swift")
    out = os.path.join(IMG, "qr.png")
    if os.path.exists(src):
        subprocess.run(["swift", src, url, out], check=False)


def main():
    make_qr()
    pages = [cover_page()]
    page_no = 2

    def parts_of(group):
        return [(g, name, qty, detail, pic) for key, (g, name, qty, detail, pic) in ms.PARTS.items() if g == group]
    p, page_no = grid_pages("Parts", ms.PART_GROUPS, parts_of, 4, 40.5, 46, 3, True, start_page=page_no)
    pages += p

    def tools_of(group):
        return [t for t in ms.TOOLS if t[0] == group]
    p, page_no = grid_pages("Tools", ms.TOOL_GROUPS, tools_of, 4, 40.5, 46, 3, False, icon=True, start_page=page_no)
    pages += p
    pages.append(before_page(page_no))
    page_no += 1
    for i, step in enumerate(ms.STEPS, 1):
        pages.append(step_page(i, step, page_no))
        page_no += 1
    pages.append(done_page(page_no))
    page_no += 1
    pages.append(back_page(page_no))
    doc = ('<!doctype html><html><head><meta charset="utf-8"><title>%s %s</title><style>%s</style></head><body>%s</body></html>'
           % (esc(ms.TITLE), esc(ms.SUBTITLE), CSS, "\n".join(pages)))
    with open(OUT_HTML, "w") as f:
        f.write(doc)
    print("wrote", OUT_HTML, "(%d pages)" % len(pages))
    if "--html" in sys.argv:
        return
    os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=8000",
           "--print-to-pdf=" + OUT_PDF, "file://" + OUT_HTML]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(OUT_PDF):
        sys.exit("Chrome did not write the PDF:\n" + r.stderr[-2000:])
    print("wrote", OUT_PDF, "%.1f MB" % (os.path.getsize(OUT_PDF) / 1e6))


if __name__ == "__main__":
    main()
