r"""Every fix, every family and region: the cross-family regression run.

    python regress_families.py          every live inclusions blank and both build
                                         contracts, through the run's own fill and
                                         content-edit commands (XML, no Word, minutes)
    python regress_families.py --e2e    also one synthetic job per family through
                                         draft_contract.py --job-dir on a scratch
                                         PROJECTS tree (Word, PDFs, the gate, a revision
                                         into SS\ in each region; about an hour)

Why it exists (job 26061 feedback, 9-10 Nov 2026). Four of the sheet's ten rows were
fixes already made for one family or region that had never reached another: the
signature Date: line and the highlights (fixed for Sydney and SEQ, not Gunnedah), and
the estate in the build contract's land and cover addresses (fixed for QLD, not NSW).
Each fix came with a test for the family it was reported on, and the shared checks
asked "for the families that have this": test_live_blanks checked Date: lines only
where the family had tab stops, and the gate passed a document with no tab-stopped
line at all. Gunnedah had none, so nothing failed.

Here each outcome the team has asked for is one row, checked on every family and
region the run fills. A family passes the row, or EXEMPT names the family and the
reason. There is no third way: a family with no rule for an outcome fails it. A blank
added on the drive, or a new family in fill_inclusions.FAMILIES, is checked on every
row by the next run (a new family also needs its synthetic job here, or it fails).
A new fix adds its row here, beside its own family test.

Synthetic values only. Reads the live blanks under Z:\PROCEDURES & FORMS and the
staged build contracts (read-only); writes only under
runtime\contract-admin\state\_regress-families\ (cleared at the start of each run,
kept after it for reading). Exit 0 = every row passes or is exempt.
"""
import argparse
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_contract as dc  # noqa: E402
import edit_inclusions as E  # noqa: E402
import fill_inclusions as fi  # noqa: E402
import gate_inclusions as gi  # noqa: E402
import hia_probe  # noqa: E402
import test_live_blanks as live  # noqa: E402

SCRATCH = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "_regress-families"

# Two owners and a named estate on every job: most of the rows below are about
# where those land.
NSW_JOB = {
    "lot_no": "9101", "street": "9 Sample Road", "suburb": "SAMPLEVILLE NSW", "estate": "Sample Heights",
    "house_type": "Sample 145", "house_size": "232.72 m\u00b2", "facade": "Sample Fa\u00e7ade",
    "garage_side": "Right Hand Side", "price": "600,000.00", "owner_1": "Alex SAMPLE", "owner_2": "Sam SAMPLE",
    "owners": "Alex SAMPLE & Sam SAMPLE", "site_address": "9101, 9 Sample Road, SAMPLEVILLE NSW 2999",
    "builders_rep": "Michael CRONK", "job_no": "99981", "site_hia": "9 Sample Road, Sampleville",
    "land_street": "9 Sample Road", "land_suburb": "SAMPLEVILLE", "land_postcode": "2999", "dp_no": "",
    "owner_mobile": "0400 000 000", "owner_email": "alex@example.com", "owner_address": "1 Example Street",
    "owner_suburb": "EXAMPLETOWN", "owner_state": "NSW", "owner_postcode": "2000",
}
QLD_JOB = {
    "lot_no": "9102", "street": "Example Drive", "suburb": "SAMPLETOWN QLD", "estate": "Sample Estate",
    "house_type": "Sample 200", "house_size": "200.00 m\u00b2", "facade": "Sample Fa\u00e7ade",
    "garage_side": "Left Hand Side", "price": "500,000.00", "owner_1": "Jo EXAMPLE", "owner_2": "Kim EXAMPLE",
    "owners": "Jo EXAMPLE & Kim EXAMPLE", "site_address": "9102, Example Drive (Sample Estate), SAMPLETOWN QLD 4000",
    "builders_rep": "Michael CRONK", "job_no": "99982", "sp_rp": "", "land_street": "Example Drive",
    "land_suburb": "SAMPLETOWN", "land_state": "QLD", "land_postcode": "4000",
    "owner_mobile": "0400 000 001", "owner_email": "jo@example.com", "owner_address": "2 Example Street",
    "owner_suburb": "EXAMPLETOWN", "owner_state": "QLD", "owner_postcode": "4000",
    "upgrades": {"storeys": 1, "items": []},
}
# the job each family's blanks are filled with, and its region
JOBS = {
    "sydney": dict(NSW_JOB, upgrades={"area": "box_hill", "storeys": 1, "bathroom2_ground": True, "items": []}),
    "gunnedah": NSW_JOB,
    "seq": QLD_JOB,
}
REGION_OF = {"sydney": "NSW", "gunnedah": "NSW", "seq": "QLD"}
# where the PROJECTS tree puts each family's job (hia_probe reads the region from it)
PROJECTS_REGION = {"sydney": "SYDNEY", "gunnedah": "GUNNEDAH", "seq": "SEQ"}
# what each region's documents read with those values
WANT = {
    "NSW": {"estate": "Sample Heights", "page1": "(9) Sample Road", "street": "(9) Sample Road, (Sample Heights)",
            "box": "Lot 9101, (9) Sample Road, (Sample Heights), SAMPLEVILLE NSW 2999",
            "land": "(9) Sample Road, (Sample Heights)",
            "cover": "(9) Sample Road, (Sample Heights), SAMPLEVILLE NSW 2999"},
    "QLD": {"estate": "Sample Estate", "page1": "Example Drive", "street": "Example Drive, (Sample Estate)",
            "box": "Lot 9102, Example Drive (Sample Estate), SAMPLETOWN QLD 4000",
            "land": "Example Drive, (Sample Estate)",
            "cover": "Example Drive, (Sample Estate) SAMPLETOWN QLD 4000"},
}
# (row, family or region): why that family or region does not take the outcome.
# Every entry needs the evidence it rests on; an entry whose row now passes is reported.
EXEMPT = {}

INC_ROWS, BC_ROWS = [], []


def inc_row(name, source):
    def deco(f):
        INC_ROWS.append((name, source, f))
        return f
    return deco


def bc_row(name, source):
    def deco(f):
        BC_ROWS.append((name, source, f))
        return f
    return deco


def run_py(script, *args):
    return subprocess.run([sys.executable, str(HERE / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def flat_text(docx):
    """The document's visible text on one line: docx_text.py's tab and break marks as spaces."""
    t = run_py("docx_text.py", docx, "--max", "0").stdout
    return " ".join(re.sub(r"\s[|/~]\s", " ", t).split())


class Doc:
    """One filled document and what the row checks read from it."""

    def __init__(self, path, family, region, job):
        self.path, self.family, self.region, self.job = Path(path), family, region, job
        self.want = WANT[region]
        with zipfile.ZipFile(self.path) as z:
            self.xml = z.read("word/document.xml").decode("utf-8")
        self.text = flat_text(self.path)
        self.gate = []
        if family:
            E.use_family(family)
            gi.check_xml(str(self.path), self.gate)


def last(lines):
    return lines[-1] if lines else ""


# ---------------------------------------------------------------- inclusions rows
@inc_row("every field filled", "blank 8, 31 Oct 2026")
def r_fields(d):
    return d.check_ok, d.check_msg


@inc_row("owners in each owners box", "#100")
def r_owners(d):
    ok, got = live.owners_boxes(d.xml, d.job["owners"])
    return ok, "" if ok else f"boxes read {got}"


@inc_row("site address in its box", "CD-3.3, #100")
def r_site_box(d):
    lines = []
    return gi.check_site_box(str(d.path), lines), last(lines)


@inc_row("every Date: on the signature tab stops", "Sydney sheet 9.9 rows 14-15, #94, 26061 row 6")
def r_dates(d):
    if not (fi.FAMILIES[d.family].get("tabs") or {}).get("sig_date"):
        return False, f"the {d.family} family has no signature tab stops (fill_inclusions.FAMILIES)"
    lines = []
    ok = gi.check_signature_lines(str(d.path), lines, d.family)
    if "no tab-stopped signature lines" in last(lines):
        return False, last(lines)
    return ok, last(lines)


@inc_row("no highlight or run shading", "#58, #94, 26061 row 4")
def r_highlight(d):
    bad = [l for l in d.gate if "highlight(s)" in l and "FAIL" in l]
    return not bad, last(bad) or "none"


@inc_row("black except the package headings", "#58")
def r_colour(d):
    bad = [l for l in d.gate if l.startswith("colour") and "FAIL" in l and "highlight(s)" not in l]
    return not bad, "; ".join(bad) or next((l for l in d.gate if "package heading(s) keep" in l), "black")


@inc_row("no template instruction left", "Sydney sheet 9.9")
def r_notes(d):
    bad = [l for l in d.gate if l.startswith("notes") and "FAIL" in l]
    return not bad, last(bad) or "none left"


@inc_row("footer total is Word's page count", "16 Oct 2026")
def r_footer(d):
    lines = []
    return gi.check_footer_total(str(d.path), lines), last(lines)


@inc_row("ESTATE filled", "26061 row 3")
def r_estate(d):
    ok = re.search(r"ESTATE\s*:\s*" + re.escape(d.want["estate"]), d.text) is not None
    return ok, "" if ok else f"no 'ESTATE : {d.want['estate']}'"


@inc_row("signature STREET: with the estate, page 1 bare", "26059 hand fix, 26061 row 7")
def r_street(d):
    # page 1's STREET comes first in document order (its label is "STREET :" on most blanks and
    # "STREET:" on SEQ blank 8); every later one is a signature-page copy
    found = re.findall(r"STREET\s*:\s*(.{0,60})", d.text)
    page1, sig = (found[0], found[1:]) if found else ("", [])
    good = [s for s in sig if s.startswith(d.want["street"])]
    bare = page1.startswith(d.want["page1"]) and not page1.startswith(d.want["street"])
    ok = bool(sig) and len(good) == len(sig) and bare
    return ok, (f"{len(good)}/{len(sig)} signature-page STREET: read '{d.want['street']}'"
                + ("" if bare else f"; page 1 STREET reads '{page1[:40]}', not the bare street"))


@inc_row("site box names the estate", "26061 row 8")
def r_box_estate(d):
    ok = d.want["box"] in d.text
    return ok, "" if ok else f"no '{d.want['box']}'"


# ---------------------------------------------------------------- build contract rows
@bc_row("every value filled", "regress_hia")
def b_values(d):
    j = d.job
    missing = [v for v in (j["lot_no"], j["owner_1"], j["owner_2"], j["job_no"]) if v not in d.text]
    return not missing, f"missing {missing}" if missing else ""


@bc_row("land street with the estate", "#89 (QLD), 26061 row 10")
def b_land(d):
    n = d.text.count(d.want["land"])
    return n >= 2, f"'{d.want['land']}' {n} time(s) (cover and The Land)"


@bc_row("cover SITE: street, estate, suburb, state, postcode", "#89/#93 (QLD), 26061 row 9")
def b_cover(d):
    ok = d.want["cover"] in d.text
    return ok, "" if ok else f"no '{d.want['cover']}'"


def name_line(xml, value):
    """(tab stop positions, tab-led) of the NAME paragraph that carries value, or None."""
    first = fi.xml_escape(value.split()[0])
    for p in re.findall(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", xml, re.S):
        t = "".join(fi.run_text(r.group(0)) for r in fi.RUN_RE.finditer(p))
        if value in t and t.lstrip().upper().startswith("NAME"):
            k = p.find(f">{first}")
            return set(re.findall(r'<w:tab w:val="\w+" w:pos="(\d+)"/>', p)), "<w:tab/>" in p[:k]
    return None


@bc_row("owner signature NAME level with the builder's", "review item 13 (NSW), 27 Oct 2026 review (QLD)")
def b_sig_name(d):
    if d.region == "QLD":
        # the builder's name ships prefilled in a two-column section: the owner's is typed at
        # its measured x and size (regress_hia keeps the geometry in step with the template)
        import regress_hia
        with contextlib.redirect_stdout(io.StringIO()):
            geometry = regress_hia.builder_name_geometry()
        why = regress_hia.sig_name_check(str(d.path), d.job["owners"])
        return geometry is not False and not why, why or "owner NAME at the builder's x and size"
    owner, builder = name_line(d.xml, d.job["owners"]), name_line(d.xml, d.job["builders_rep"])
    if not owner or not builder:
        return False, f"NAME line not found for {'the owners' if not owner else 'the builder'}"
    shared = owner[0] & builder[0]
    ok = bool(shared) and owner[1] and builder[1]
    return ok, (f"both names tab-led at {sorted(shared)} tw" if ok else
                f"owner stops {sorted(owner[0])} tab-led {owner[1]}, builder stops {sorted(builder[0])} "
                f"tab-led {builder[1]}")


# ---------------------------------------------------------------- making the documents
def write_job(wd, job):
    wd.mkdir(parents=True, exist_ok=True)
    jf = wd / "job.json"
    jf.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    (wd / "email_original.txt").write_text(f"Contract Order - Lot {job['lot_no']} {job['street']}\n",
                                           encoding="utf-8")
    return jf


def make_inclusions(blank, family, wd):
    """The inclusions as the run makes them before Word: check, fill, then the content edit
    where the run edits this family. Returns (Doc or None, note)."""
    job = JOBS[family]
    jf = write_job(wd, job)
    out = wd / "INCLUSIONS.docx"
    chk = run_py("fill_inclusions.py", "--template", blank, "--job", jf, "--check")
    fill = run_py("fill_inclusions.py", "--template", blank, "--job", jf, "--out", out)
    if fill.returncode != 0 or not out.exists():
        return None, "fill failed: " + last((fill.stdout + fill.stderr).strip().splitlines())
    stages = "fill"
    if dc.edits_inclusions(family, None, (job.get("upgrades") or {}).get("items") or []):
        measure = dc.cached_measure(blank)
        if not measure:
            return None, ("the run edits this family, and no current Word measurement of this blank is "
                          "cached: run --e2e on it (or one draft_contract.py run) to make it")
        r = run_py("edit_inclusions.py", "--docx", out, "--job", jf, "--blank", blank, "--blank-measure", measure,
                   "--out", out, "--report", wd / "edit_inclusions.txt", "--plan", wd / "layout_plan.json",
                   "--family", family)
        if r.returncode != 0:
            return None, "content edit failed: " + last((r.stdout + r.stderr).strip().splitlines())
        stages = "fill + content edit"
    d = Doc(out, family, REGION_OF[family], job)
    d.check_ok = chk.returncode == 0
    d.check_msg = "" if d.check_ok else last((chk.stdout + chk.stderr).strip().splitlines())
    return d, stages


def build_template(region):
    """The build contract template the run would take: the region's one approved blank, else
    the staged interim template (draft_contract CD-5.2b)."""
    folder = hia_probe.CONTRACTS_ROOT / hia_probe.REGION_TO_FOLDER["SYDNEY" if region == "NSW" else "SEQ"][1]
    rows = hia_probe.classify(folder) if folder.is_dir() else []
    approved = [folder / rel for status, rel, _ in rows if status == "CANDIDATE"]
    return approved[0] if len(approved) == 1 else dc.STAGED_HIA[region]


def make_build(region, wd):
    job = NSW_JOB if region == "NSW" else QLD_JOB
    jf = write_job(wd, job)
    template = build_template(region)
    out = wd / "BUILD CONTRACT.docx"
    chk = run_py("fill_hia.py", "--template", template, "--job", jf, "--check", "--region", region)
    r = run_py("fill_hia.py", "--template", template, "--job", jf, "--out", out, "--region", region)
    if r.returncode != 0 or not out.exists():
        return None, f"{template.name}: fill failed: " + last((r.stdout + r.stderr).strip().splitlines())
    d = Doc(out, None, region, job)
    d.check_ok = chk.returncode == 0
    return d, template.name


# ---------------------------------------------------------------- the matrix
class Matrix:
    def __init__(self, rows, columns):
        self.rows, self.columns = rows, columns            # columns: [(key, label)]
        self.cells = {}                                     # (row, key) -> [(subject, ok, detail)]
        self.failures, self.notes = [], []

    def judge(self, key, subject, doc, why_missing="", quiet=False):
        if doc is None:
            # nothing to read: one failure for the subject, not one per row (quiet when the
            # end-to-end rows already report the run that saved nothing)
            if not quiet:
                self.failures.append(f"{subject}: not made - {why_missing}")
            for name, _, _ in self.rows:
                self.cells.setdefault((name, key), []).append((subject, False, "not made"))
            return
        for name, _, f in self.rows:
            try:
                ok, detail = f(doc)
            except Exception as e:   # a check that cannot read the document fails it
                ok, detail = False, f"check error: {type(e).__name__}: {e}"
            reason = EXEMPT.get((name, key))
            if reason and ok:
                self.notes.append(f"exemption no longer needed: '{name}' passes on {subject} ({reason})")
            self.cells.setdefault((name, key), []).append((subject, ok or bool(reason), "exempt" if reason else ""))
            if not ok and not reason:
                self.failures.append(f"{name} | {subject}: {detail}")

    def show(self, title):
        print(f"\n{title}")
        width = max(len(n) for n, _, _ in self.rows) + 2
        print(" " * (width + 2) + "".join(f"{label:<14}" for _, label in self.columns))
        for name, source, _ in self.rows:
            cells = []
            for key, _ in self.columns:
                got = self.cells.get((name, key), [])
                if not got:
                    cells.append(f"{'-':<14}")
                    continue
                passed = sum(1 for _, ok, _ in got if ok)
                tag = ("exempt" if any(e == "exempt" for _, _, e in got) else "ok" if passed == len(got)
                       else "not made" if all(e == "not made" for _, _, e in got) else "FAIL")
                cells.append(f"{tag + f' {passed}/{len(got)}':<14}")
            print(f"  {name:<{width}}" + "".join(cells) + f"  [{source}]")


# ---------------------------------------------------------------- end to end
E2E_JOBS = [
    # (family, blank pick, label, revision): revision "full" re-runs the whole job, "bc" re-runs
    # the build contract alone (the routing is one code path; each region is shown once)
    ("gunnedah", lambda b: b.parent.name.startswith("REGION - GUNNEDAH"), "gunnedah", "full"),
    ("sydney", lambda b: b.name.startswith("1. Sydney"), "sydney std", None),
    ("sydney", lambda b: b.name.startswith("3. Sydney"), "sydney aux", None),
    ("seq", lambda b: b.name.startswith("1. Sth East") and b.parent.name.startswith("INVESTOR"), "seq", "bc"),
]


def top_level(job_dir, kind):
    return sorted(p for p in job_dir.iterdir() if p.is_file() and kind in p.name.upper())


def e2e(blanks, inc, bc, routing):
    base = SCRATCH / "e2e"
    for n, (family, pick, label, revision) in enumerate(E2E_JOBS, 1):
        blank = next((b for b in blanks if pick(b)), None)
        key = f"e2e:{label}"
        if blank is None:
            inc.judge(key, label, None, "blank not found on the drive")
            continue
        job = dict(JOBS[family], job_no=f"9997{n}")
        job_dir = (base / "PROJECTS" / PROJECTS_REGION[family] /
                   f"{job['job_no']} - LOT {job['lot_no']} {job['street'].upper()}" / "CONTRACT" / "CONTRACT DOCUMENTATION")
        job_dir.mkdir(parents=True)
        wd = base / "work" / label.replace(" ", "-")
        jf = write_job(wd, job)
        t0 = time.time()
        r = subprocess.run([sys.executable, str(HERE / "draft_contract.py"), "--job", str(jf), "--template", str(blank),
                            "--job-dir", str(job_dir)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        (wd / "run-1.txt").write_text(r.stdout + r.stderr, encoding="utf-8")
        print(f"  {label}: first save, exit {r.returncode}, {time.time() - t0:.0f} s")
        docs = {k: [p for p in top_level(job_dir, k) if p.suffix == ".docx"] for k in ("INCLUSIONS", "BUILD CONTRACT")}
        pdfs = {k: [p for p in top_level(job_dir, k) if p.suffix == ".pdf"] for k in ("INCLUSIONS", "BUILD CONTRACT")}
        why = f"run exit {r.returncode}: " + last([l for l in (r.stdout + r.stderr).splitlines() if l.strip()])
        d = Doc(docs["INCLUSIONS"][0], family, REGION_OF[family], job) if docs["INCLUSIONS"] else None
        if d:
            d.check_ok, d.check_msg = r.returncode == 0, "" if r.returncode == 0 else why
        inc.judge(key, label, d, why, quiet=True)
        b = Doc(docs["BUILD CONTRACT"][0], None, REGION_OF[family], job) if docs["BUILD CONTRACT"] else None
        bc.judge(key, label, b, why, quiet=True)
        gate = (wd / "gate_inclusions.txt").read_text(encoding="utf-8", errors="replace") if (wd / "gate_inclusions.txt").exists() else ""
        routing.record(key, "saved: docx + pdf of each document",
                       r.returncode == 0 and all(len(docs[k]) == 1 and len(pdfs[k]) == 1 for k in docs),
                       f"{why}; in the job folder: " + ", ".join(f"{k} {len(docs[k])} docx {len(pdfs[k])} pdf"
                                                                 for k in docs))
        edits = dc.edits_inclusions(family, None, (job.get("upgrades") or {}).get("items") or [])
        gate_fails = [l.strip() for l in gate.splitlines() if "FAIL" in l and not l.startswith("verdict")]
        routing.record(key, "gate PASS where the run edits",
                       (not edits) or re.search(r"^verdict\s*:\s*PASS", gate, re.M) is not None,
                       "; ".join(gate_fails) or last(gate.strip().splitlines()) or "no gate report")
        if revision:
            before = {p.name: p.read_bytes() for p in job_dir.iterdir() if p.is_file()}
            job2 = dict(job, price="610,000.00" if REGION_OF[family] == "NSW" else "510,000.00")
            write_job(wd, job2)
            cmd = [sys.executable, str(HERE / "draft_contract.py"), "--job", str(jf), "--job-dir", str(job_dir)] + \
                (["--build-contract-only"] if revision == "bc" else ["--template", str(blank)])
            t0 = time.time()
            r2 = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            (wd / "run-2.txt").write_text(r2.stdout + r2.stderr, encoding="utf-8")
            print(f"  {label}: revision ({revision}), exit {r2.returncode}, {time.time() - t0:.0f} s")
            kinds = ("INCLUSIONS", "BUILD CONTRACT") if revision == "full" else ("BUILD CONTRACT",)
            ss = job_dir / "SS"
            moved = all((ss / n).exists() and (ss / n).read_bytes() == data
                        for n, data in before.items() if any(k in n.upper() for k in kinds))
            fresh = all(len(top_level(job_dir, k)) == 2 for k in kinds)
            routing.record(key, "revision: new pair in, old pair to SS\\", r2.returncode == 0 and moved and fresh,
                           f"exit {r2.returncode}, old pair in SS\\ byte for byte {moved}, one pair per document {fresh}")


class Routing:
    def __init__(self):
        self.rows = {}
        self.failures = []

    def record(self, key, name, ok, detail):
        self.rows.setdefault(name, {})[key] = ok
        if not ok:
            self.failures.append(f"{name} | {key}: {detail}")

    def show(self, keys):
        print("\nend to end: the saved job")
        for name, got in self.rows.items():
            print(f"  {name:<40}" + "".join(f"{('ok' if got[k] else 'FAIL') if k in got else '-':<14}" for k in keys))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--e2e", action="store_true", help="also run one synthetic job per family end to end (Word)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    failures = []

    # coverage: every family has a job, a region and a live blank; every blank has a family
    blanks = live.live_blanks()
    fams = {b: fi.pick_family(str(b))[0] for b in blanks}
    for f in fi.FAMILIES:
        for what, table in (("synthetic job", JOBS), ("region", REGION_OF), ("PROJECTS region", PROJECTS_REGION)):
            if f not in table:
                failures.append(f"coverage | family {f} has no {what} in regress_families.py")
        if f not in fams.values():
            failures.append(f"coverage | family {f} has no live blank on the drive")
    failures += [f"coverage | {b.name}: no family" for b, f in fams.items() if f is None]
    order = [f for f in fi.FAMILIES if f in JOBS]
    print(f"regress_families: {len(blanks)} live inclusions blank(s) - "
          + ", ".join(f"{f} {sum(1 for x in fams.values() if x == f)}" for f in order))

    inc = Matrix(INC_ROWS, [(f, f) for f in order])
    for n, blank in enumerate(blanks, 1):
        fam = fams[blank]
        if fam not in JOBS:
            continue
        doc, note = make_inclusions(blank, fam, SCRATCH / f"inc-{n:02d}")
        inc.judge(fam, f"{fam} {blank.name[:40]}", doc, note)
        print(f"  {fam:<9} {blank.name[:60]:<60} {note if doc else 'NOT MADE: ' + note}")

    bc = Matrix(BC_ROWS, [("NSW", "NSW"), ("QLD", "QLD")])
    for region in ("NSW", "QLD"):
        doc, note = make_build(region, SCRATCH / f"bc-{region}")
        bc.judge(region, f"{region} {note}", doc, note)
        print(f"  build contract {region}: {note}")

    routing = Routing()
    if args.e2e:
        print("\nend to end (draft_contract.py --job-dir, Word):")
        e2e(blanks, inc, bc, routing)
        keys = [f"e2e:{label}" for _, _, label, _ in E2E_JOBS]
        inc.columns += [(k, k[4:]) for k in keys]
        bc.columns += [(k, k[4:]) for k in keys]

    inc.show("inclusions (fill and content edit as the run does them; e2e = the saved document)")
    bc.show("build contracts")
    if args.e2e:
        routing.show([f"e2e:{label}" for _, _, label, _ in E2E_JOBS])
    failures += inc.failures + bc.failures + routing.failures
    for n in inc.notes + bc.notes:
        print(f"NOTE {n}")
    if EXEMPT:
        print("\nexempt:")
        for (name, key), reason in EXEMPT.items():
            print(f"  {name} | {key}: {reason}")
    if failures:
        print("\nfailures:")
        for f in failures:
            print(f"  FAIL {f}")
    print(f"\n{'PASS' if not failures else 'FAIL'} - {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
