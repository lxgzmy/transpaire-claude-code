r"""How wide a typed value prints, and the largest size at which it fits a slot. Stdlib only.

    python font_fit.py "SAMPLE HOLDINGS No.2 PTY LTD ... ACN: 600 000 000" --font Arial --size 24 --width 7000

A company or trust owner's name carries its ACN on the contract (feedback
sheet 5 Nov 2026, rows 9, 12, 13, 16: "scale down font for long company
names, as ACN must be included with company name"). The fillers type it into
a slot of known width - a value cell, the span between two tab stops - and
need the size at which it stays on one line. Word cannot be asked (the
inclusions signature lines sit in text boxes Word does not measure, and the
build contract has no layout pass), so the width is read from the font's own
advance widths: the TrueType file's hmtx table through its cmap, the way a
renderer lays a line out (no kerning - it only narrows a line).

Fonts are looked up in the Windows font folder by family and weight
(read-only). A font that is not there (a dev clone off the server) falls
back to a conservative average of 0.62 em per character, and the result says
"estimated" so the report can flag it.
"""
import argparse
import os
import struct
import sys
from functools import lru_cache
from pathlib import Path

FONT_DIRS = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
# family (lower case) -> (regular file, bold file or None for synthetic bold)
FAMILY_FILES = {
    "arial": ("arial.ttf", "arialbd.ttf"),
    "arial mt": ("arial.ttf", "arialbd.ttf"),
    "calibri": ("calibri.ttf", "calibrib.ttf"),
    "calibri light": ("calibril.ttf", None),
    "segoe ui": ("segoeui.ttf", "segoeuib.ttf"),
    "segoe ui light": ("segoeuil.ttf", None),
    "segoe ui semilight": ("segoeuisl.ttf", None),
    "tahoma": ("tahoma.ttf", "tahomabd.ttf"),
}
SYNTHETIC_BOLD = 1.03     # Word widens a face it has to embolden itself
FALLBACK_EM = 0.62        # average advance per character when the font file is missing
SAFETY = 0.97             # a line is called "fitting" only with 3% to spare


class Font:
    def __init__(self, path):
        data = Path(path).read_bytes()
        n = struct.unpack_from(">H", data, 4)[0]
        tables = {}
        for i in range(n):
            tag, _, off, ln = struct.unpack_from(">4sIII", data, 12 + 16 * i)
            tables[tag.decode("latin-1")] = (off, ln)
        self.upem = struct.unpack_from(">H", data, tables["head"][0] + 18)[0]
        n_hm = struct.unpack_from(">H", data, tables["hhea"][0] + 34)[0]
        off = tables["hmtx"][0]
        self.adv = [struct.unpack_from(">H", data, off + 4 * i)[0] for i in range(n_hm)]
        self.cmap = self._cmap(data, tables["cmap"][0])

    @staticmethod
    def _cmap(data, base):
        n = struct.unpack_from(">H", data, base + 2)[0]
        subs = []
        for i in range(n):
            pid, eid, off = struct.unpack_from(">HHI", data, base + 4 + 8 * i)
            fmt = struct.unpack_from(">H", data, base + off)[0]
            subs.append((fmt, pid, eid, base + off))
        # prefer a full Unicode table (format 12), then the BMP one (format 4)
        for want in (12, 4):
            for fmt, pid, eid, at in subs:
                if fmt == want and (pid, eid) in ((3, 10), (0, 4), (3, 1), (0, 3), (0, 6)):
                    return Font._read12(data, at) if fmt == 12 else Font._read4(data, at)
        raise ValueError("no usable cmap")

    @staticmethod
    def _read4(data, at):
        seg2 = struct.unpack_from(">H", data, at + 6)[0]
        segs = seg2 // 2
        ends = struct.unpack_from(f">{segs}H", data, at + 14)
        starts = struct.unpack_from(f">{segs}H", data, at + 16 + seg2)
        deltas = struct.unpack_from(f">{segs}h", data, at + 16 + 2 * seg2)
        ro_at = at + 16 + 3 * seg2
        ros = struct.unpack_from(f">{segs}H", data, ro_at)
        out = {}
        for k in range(segs):
            for c in range(starts[k], ends[k] + 1):
                if c == 0xFFFF:
                    continue
                if ros[k] == 0:
                    g = (c + deltas[k]) & 0xFFFF
                else:
                    g_at = ro_at + 2 * k + ros[k] + 2 * (c - starts[k])
                    g = struct.unpack_from(">H", data, g_at)[0]
                    if g:
                        g = (g + deltas[k]) & 0xFFFF
                out[c] = g
        return out

    @staticmethod
    def _read12(data, at):
        n = struct.unpack_from(">I", data, at + 12)[0]
        out = {}
        for k in range(n):
            s, e, g = struct.unpack_from(">III", data, at + 16 + 12 * k)
            if e - s > 0x3000:      # skip huge CJK ranges - names here are Latin
                continue
            for c in range(s, e + 1):
                out[c] = g + (c - s)
        return out

    def width_em(self, text):
        total = 0
        for ch in text:
            g = self.cmap.get(ord(ch), 0)
            total += self.adv[g] if g < len(self.adv) else self.adv[-1]
        return total / self.upem


@lru_cache(maxsize=None)
def _load(filename):
    for d in FONT_DIRS:
        p = d / filename
        if p.is_file():
            try:
                return Font(p)
            except (ValueError, struct.error, KeyError):
                return None
    return None


def text_width_pt(text, family, half_points, bold=False):
    """(width in points, exact) - exact False when the font file was not found."""
    fam = (family or "").strip().lower()
    regular, bold_file = FAMILY_FILES.get(fam, (None, None))
    font, factor = None, 1.0
    if bold and bold_file:
        font = _load(bold_file)
    if font is None and regular:
        font = _load(regular)
        factor = SYNTHETIC_BOLD if bold else 1.0
    size = half_points / 2
    if font is None:
        return len(text) * FALLBACK_EM * size * (SYNTHETIC_BOLD if bold else 1.0), False
    return font.width_em(text) * size * factor, True


def fit_size(text, family, max_half_points, width_twips, bold=False, min_half_points=14):
    """(half-points, fits, exact): the largest size, in half-point steps from
    max_half_points down to min_half_points, at which text prints within
    width_twips with SAFETY to spare. Not fitting even at the floor returns the
    floor and fits=False - the value then wraps, and the report says so."""
    room = width_twips / 20 * SAFETY
    exact = True
    for hp in range(int(max_half_points), int(min_half_points) - 1, -1):
        w, exact = text_width_pt(text, family, hp, bold)
        if w <= room:
            return hp, True, exact
    return int(min_half_points), False, exact


TEXTBOX_INSETS = 288     # twips: Word's default 0.1" left + right text-box inset
CELL_PADDING = 230       # twips: Word's default 0.08" left + right cell padding


def container_width(xml, pos):
    """Twips a line has at pos in a document.xml: the table cell it sits in, else
    the text box (DrawingML extent or VML width), else the page less margins."""
    import re
    tc_open = max((m.start() for m in re.finditer(r"<w:tc[ >]", xml[:pos])), default=-1)
    if tc_open > xml.rfind("</w:tc>", 0, pos):
        m = re.search(r'<w:tcW w:w="(\d+)" w:type="dxa"', xml[tc_open:tc_open + 600])
        if m:
            return int(m.group(1)) - CELL_PADDING
    box = xml.rfind("<w:txbxContent", 0, pos)
    if box > xml.rfind("</w:txbxContent>", 0, pos):
        wsp = xml.rfind("<wps:wsp>", 0, box)
        drawing = xml.rfind("<w:drawing>", 0, box)
        m = re.search(r'<a:ext cx="(\d+)"', xml[wsp:box]) if wsp > drawing >= 0 else None
        if not m and drawing >= 0:
            m = re.search(r'<wp:extent cx="(\d+)"', xml[drawing:box])
        if m:
            return int(m.group(1)) // 635 - TEXTBOX_INSETS
        shape = max(xml.rfind("<v:shape ", 0, box), xml.rfind("<v:rect ", 0, box))
        m = re.search(r'width:([\d.]+)pt', xml[shape:xml.find(">", shape)]) if shape >= 0 else None
        if m:
            return int(float(m.group(1)) * 20) - TEXTBOX_INSETS
    m = re.search(r"<w:sectPr\b.*?</w:sectPr>", xml[pos:], re.S)
    if m:
        w = re.search(r'<w:pgSz w:w="(\d+)"', m.group(0))
        lr = [re.search(rf'<w:pgMar\b[^>]*w:{k}="(\d+)"', m.group(0)) for k in ("left", "right")]
        if w and all(lr):
            return int(w.group(1)) - int(lr[0].group(1)) - int(lr[1].group(1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--font", default="Arial")
    ap.add_argument("--size", type=int, default=20, help="half-points")
    ap.add_argument("--width", type=int, help="slot width in twips: print the size that fits")
    ap.add_argument("--bold", action="store_true")
    a = ap.parse_args()
    w, exact = text_width_pt(a.text, a.font, a.size, a.bold)
    print(f"width : {w:.1f} pt at {a.size / 2:g} pt ({'font file' if exact else 'estimated'})")
    if a.width:
        hp, fits, _ = fit_size(a.text, a.font, a.size, a.width, a.bold)
        print(f"fit   : {hp / 2:g} pt in {a.width} twips ({a.width / 20:g} pt) - "
              + ("fits on one line" if fits else "does not fit even at the floor; it wraps"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
