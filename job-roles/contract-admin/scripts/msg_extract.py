r"""Extract attachments and body text from an Outlook .msg. Pure stdlib.

    python msg_extract.py "<file.msg>" --list
    python msg_extract.py "<file.msg>" -a <outdir>            # save attachments
    python msg_extract.py "<file.msg>" -o <body.txt>          # save body text

Why this exists: the servers this repo runs on do not have the extract_msg
package, installing anything needs approval (org CLAUDE.md), and the job
folders keep the original request emails as .msg files whose attachments -
signed land contracts, EOIs, plans - are the authoritative field sources for
contract drafting. A .msg is an OLE/CFBF compound file; this reads just enough
of MS-CFB + MS-OXMSG to list and pull streams:

  __substg1.0_1000001F                unicode body text
  __attach_version1.0_#NNNNNNNN\      one storage per attachment
      __substg1.0_3707001F            long filename (UTF-16LE)
      __substg1.0_3704001F            short filename (fallback)
      __substg1.0_37010102            the attachment bytes

Read-only on the .msg; writes only where you point it.
"""
import argparse
import struct
import sys
from pathlib import Path

ENDOFCHAIN = 0xFFFFFFFE
FREESECT = 0xFFFFFFFF


class Cfb:
    def __init__(self, data):
        if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise ValueError("not an OLE compound file (bad magic)")
        (self.sec_shift,) = struct.unpack_from("<H", data, 30)
        (self.mini_shift,) = struct.unpack_from("<H", data, 32)
        self.sec = 1 << self.sec_shift
        self.mini = 1 << self.mini_shift
        (self.first_dir,) = struct.unpack_from("<I", data, 48)
        (self.mini_cutoff,) = struct.unpack_from("<I", data, 56)
        (self.first_minifat,) = struct.unpack_from("<I", data, 60)
        (self.n_minifat,) = struct.unpack_from("<I", data, 64)
        (self.first_difat,) = struct.unpack_from("<I", data, 68)
        (self.n_difat,) = struct.unpack_from("<I", data, 72)
        self.data = data

        difat = list(struct.unpack_from("<109I", data, 76))
        nxt = self.first_difat
        for _ in range(self.n_difat):
            if nxt in (ENDOFCHAIN, FREESECT):
                break
            raw = self._sector(nxt)
            ents = struct.unpack(f"<{self.sec // 4}I", raw)
            difat.extend(ents[:-1])
            nxt = ents[-1]
        self.fat = []
        for s in difat:
            if s in (ENDOFCHAIN, FREESECT):
                continue
            self.fat.extend(struct.unpack(f"<{self.sec // 4}I", self._sector(s)))

        self.minifat = []
        for s in self._chain(self.first_minifat):
            self.minifat.extend(struct.unpack(f"<{self.sec // 4}I", self._sector(s)))

        self.dirents = []
        for s in self._chain(self.first_dir):
            raw = self._sector(s)
            for off in range(0, self.sec, 128):
                e = raw[off:off + 128]
                (nlen,) = struct.unpack_from("<H", e, 64)
                name = e[:max(0, nlen - 2)].decode("utf-16-le", "replace") if nlen >= 2 else ""
                typ = e[66]
                child = struct.unpack_from("<I", e, 76)[0]
                start = struct.unpack_from("<I", e, 116)[0]
                size = struct.unpack_from("<Q", e, 120)[0]
                self.dirents.append(
                    {"name": name, "type": typ, "child": child,
                     "left": struct.unpack_from("<I", e, 68)[0],
                     "right": struct.unpack_from("<I", e, 72)[0],
                     "start": start, "size": size})
        root = self.dirents[0]
        self.ministream = self._read_chain(root["start"], root["size"])

    def _sector(self, n):
        off = (n + 1) * self.sec
        return self.data[off:off + self.sec]

    def _chain(self, first):
        seen, out, cur = set(), [], first
        while cur not in (ENDOFCHAIN, FREESECT) and cur < len(self.fat) + 1 and cur not in seen:
            out.append(cur)
            seen.add(cur)
            if cur >= len(self.fat):
                break
            cur = self.fat[cur]
        return out

    def _read_chain(self, first, size):
        return b"".join(self._sector(s) for s in self._chain(first))[:size]

    def read_stream(self, ent):
        if ent["size"] < self.mini_cutoff and ent is not self.dirents[0]:
            out, cur, seen = [], ent["start"], set()
            while cur not in (ENDOFCHAIN, FREESECT) and cur not in seen:
                out.append(self.ministream[cur * self.mini:(cur + 1) * self.mini])
                seen.add(cur)
                if cur >= len(self.minifat):
                    break
                cur = self.minifat[cur]
            return b"".join(out)[:ent["size"]]
        return self._read_chain(ent["start"], ent["size"])

    def tree(self):
        """(path, entry) for every stream, via the directory's sibling trees."""
        out = []

        def visit(idx, prefix):
            if idx in (FREESECT, ENDOFCHAIN) or idx >= len(self.dirents):
                return
            e = self.dirents[idx]
            visit(e["left"], prefix)
            visit(e["right"], prefix)
            path = prefix + e["name"]
            if e["type"] == 2:
                out.append((path, e))
            if e["child"] not in (FREESECT, ENDOFCHAIN):
                visit(e["child"], path + "/" if e["type"] != 5 else prefix)

        root = self.dirents[0]
        visit(root["child"], "")
        return out


def attachments(cfb):
    """[(filename, bytes)] in attachment order."""
    streams = dict(cfb.tree())
    out = []
    stores = sorted({p.split("/")[0] for p in streams
                     if p.startswith("__attach_version1.0_#")})
    for store in stores:
        name_ent = (streams.get(f"{store}/__substg1.0_3707001F")
                    or streams.get(f"{store}/__substg1.0_3704001F"))
        data_ent = streams.get(f"{store}/__substg1.0_37010102")
        if not data_ent:
            continue  # embedded message or OLE object - out of scope
        name = (cfb.read_stream(name_ent).decode("utf-16-le", "replace")
                if name_ent else f"{store[-8:]}.bin").strip("\x00")
        out.append((name, cfb.read_stream(data_ent)))
    return out


def body_text(cfb):
    streams = dict(cfb.tree())
    ent = streams.get("__substg1.0_1000001F")
    if ent:
        return cfb.read_stream(ent).decode("utf-16-le", "replace")
    ent = streams.get("__substg1.0_1000001E")
    if ent:
        return cfb.read_stream(ent).decode("cp1252", "replace")
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("msg")
    ap.add_argument("--list", action="store_true", help="list attachments, extract nothing")
    ap.add_argument("-a", "--attachments", help="folder to save attachments into")
    ap.add_argument("-o", "--out", help="file to save the body text into")
    args = ap.parse_args()

    cfb = Cfb(Path(args.msg).read_bytes())
    att = attachments(cfb)

    if args.list or not (args.attachments or args.out):
        for name, data in att:
            print(f"{len(data):>10}  {name}")
        return 0

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(body_text(cfb), encoding="utf-8")
        print(f"body    : {args.out}")

    if args.attachments:
        outdir = Path(args.attachments)
        outdir.mkdir(parents=True, exist_ok=True)
        for name, data in att:
            safe = "".join(c for c in name if c not in '<>:"/\\|?*').strip() or "unnamed.bin"
            p = outdir / safe
            p.write_bytes(data)
            print(f"{len(data):>10}  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
