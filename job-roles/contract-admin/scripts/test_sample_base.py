r"""Self-test for another job's inclusions as the base (CD-6.6, sample_base.py). Synthetic values only.

    python test_sample_base.py

A synthetic "sample" is made from the live Gunnedah blank the way the team makes
one: filled for an earlier lot, PROMOTIONAL UPGRADES marked "– Main Dwelling",
and an "UPGRADED INCLUSIONS – AUX DWELLING" section with its labels added. Then:

  base       the base is the blank with the sample's specification; the sample's
             client details reach neither the base nor this job's document
  stops      the sample names its client in its specification; its standard
             wording is not the blank's; a Sydney/SEQ blank; a missing list
  removals   the request's removal with `replaces`: the one line goes; the
             label's last line takes the label with it (26061 row 5); a line
             named twice is refused; any other item mode is refused on Gunnedah
  headings   the mixed-case dwelling heading pairs labels as the blank does;
             SEQ and Sydney read their headings as before
  scan       the last check: a document naming the sample's client fails

Reads the live blanks under Z:\PROCEDURES & FORMS (read-only); writes only under
runtime\contract-admin\state\ (removed at the end). The Word layout pass and gate
on a sample base are exercised end to end through draft_contract.py.
"""
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import edit_inclusions as E  # noqa: E402
import sample_base as SB  # noqa: E402

SCRATCH = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "_sample-base-selftest"
CONTRACTS = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS")
GUNNEDAH = next(iter(sorted((CONTRACTS / "REGION - GUNNEDAH, NSW").glob("*INTEGRITY*.docx"))), None)
SEQ = next(iter(sorted((CONTRACTS / "REGION - SEQ" / "INCLUSIONS" / "INVESTOR & FIRST HOME OWNER")
                       .glob("[0-9]*.docx"))), None)

EARLIER = {"lot_no": "7701", "street": "(7) Placeholder Close", "suburb": "SAMPLEVILLE NSW", "estate": "",
           "house_type": "Sample 145 + Auxiliary Unit", "house_size": "208.71 m\u00b2",
           "facade": "Sample Fa\u00e7ade", "garage_side": "Right Hand Side", "price": "611,100.00",
           "owner_1": "Jordan TESTOWNER", "owner_2": "", "owners": "Jordan TESTOWNER",
           "site_address": "7701, (7) Placeholder Close, SAMPLEVILLE NSW 2999", "builders_rep": "Michael CRONK"}
THIS = {"lot_no": "8802", "street": "(8) Example Street", "suburb": "SAMPLEVILLE NSW", "estate": "Sample Heights",
        "house_type": "Sample 145 + Auxiliary Unit", "house_size": "232.72 m\u00b2", "facade": "Sample Fa\u00e7ade",
        "garage_side": "", "price": "654,300.00", "owner_1": "Robin EXAMPLE", "owner_2": "",
        "owners": "Robin EXAMPLE", "site_address": "8802, (8) Example Street, SAMPLEVILLE NSW 2999",
        "builders_rep": "Michael CRONK"}
INFRA = "Any additional costs associated with Council Infrastructure charges (if applicable) are the responsibility of the Owner"
AUX = [("Shelving", ["Melamine shelving throughout"]),
       ("Benchtops", ["20mm stone bench tops throughout"]),
       ("Provisions", ["Includes one (1) off water meter", "Separate TV antenna to the main residence & the auxiliary unit"]),
       ("Statutory Regulations", [INFRA])]

fails = []


def check(cond, what):
    print(("  ok   " if cond else "  FAIL ") + what)
    if not cond:
        fails.append(what)


def py(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=HERE)


def fill(job, out):
    jp = out.with_suffix(".json")
    jp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    r = py("fill_inclusions.py", "--template", GUNNEDAH, "--job", jp, "--out", out)
    assert r.returncode == 0 and out.exists(), r.stdout + r.stderr
    return jp


def make_sample(out, extra_aux_line=None, change_standard=False, black_heading=False):
    """The earlier lot's filled inclusions with an aux dwelling section added, its
    heading in the template's blue as the team's samples have it (or black)."""
    fill(EARLIER, out)
    E.use_family("gunnedah")
    cols = E.Columns(E.read_xml(out))
    L, R = cols.left, cols.right
    head = E.upgraded_headings(R)[0]
    R[head] = R[head].replace("PROMOTIONAL UPGRADES", "PROMOTIONAL UPGRADES \u2013 Main Dwelling")
    labels, groups = E.upgraded_section(cols)
    last_l, last_r = labels[-1] + 1, groups[-1][1]
    blank_l, blank_r = E.blank_like(L, last_l), E.blank_like(R, last_r)
    aux_head = (E.make_para(R[head], "UPGRADED INCLUSIONS \u2013 AUX DWELLING") if black_heading else
                re.sub(r'\sw14:(?:paraId|textId)="[^"]+"', "",   # a new paragraph: Word gives it its own ids
                       R[head].replace("PROMOTIONAL UPGRADES \u2013 Main Dwelling",
                                       "UPGRADED INCLUSIONS \u2013 AUX DWELLING")))
    new_l, new_r = [], [blank_r, aux_head]
    aux = [(lab, lines + ([extra_aux_line] if extra_aux_line and lab == "Shelving" else [])) for lab, lines in AUX]
    for lab, lines in aux:
        new_l += [blank_l, E.make_para(L[labels[0]], lab)]
        new_r += [blank_r] + [E.make_para(R[groups[0][0]], t) for t in lines]
    # the aux heading takes a line the labels do not: one more blank on the left
    L[last_l:last_l] = [blank_l] + new_l
    R[last_r:last_r] = new_r
    if change_standard:
        k = next(i for i, p in enumerate(R) if E.norm(E.ptext(p)).startswith("Engineer consultation"))
        R[k] = E.make_para(R[k], "Engineer consultation & soil test only")
    E.write_docx(out, out, cols.rebuild())
    return out


def ptexts(docx):
    return [E.norm(E.ptext(p)) for p in E.P_RE.findall(E.normalise_self_closing(E.read_xml(docx)))]


def main():
    if not GUNNEDAH or not GUNNEDAH.exists():
        print("SKIP: the live Gunnedah blank is not reachable (Z: not mapped)")
        return 0
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    try:
        run()
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)
    print("\nPASS" if not fails else f"\nFAIL ({len(fails)})")
    return 1 if fails else 0


def run():
    print("== base")
    sample = make_sample(SCRATCH / "SAMPLE_LOT 7701.docx")
    doc = SCRATCH / "INCLUSIONS_LOT 8802.docx"
    job = fill(THIS, doc)
    base = SCRATCH / SB.cache_name(GUNNEDAH, sample)
    r = py("sample_base.py", "--blank", GUNNEDAH, "--sample", sample, "--job", job, "--out-blank", base,
           "--docx", doc, "--report", SCRATCH / "sample_base.txt")
    check(r.returncode == 0, f"the sample builds a base (exit {r.returncode}) {r.stdout[-300:] if r.returncode else ''}")
    check("standard      : the sample's standard sections read exactly as the blank" in r.stdout,
          "the standard sections are compared with the blank and match")
    check("UPGRADED INCLUSIONS \u2013 AUX DWELLING - 4 label(s), 5 line(s)" in r.stdout,
          "the aux dwelling section is read: 4 labels, 5 lines")
    check("all 5 line(s) come from the sample" in r.stdout and "a person's check" in r.stdout,
          "the report lists what comes from the sample and the plan-dependent wording to check")
    bt, dt = ptexts(base), ptexts(doc)
    check("UPGRADED INCLUSIONS \u2013 AUX DWELLING" in bt and INFRA in bt, "the base carries the sample's aux section")
    check(not any("TESTOWNER" in t or "Placeholder" in t or "7701" in t for t in bt),
          "the base names nothing of the sample's client (its page 1 and signature pages are the blank's)")
    check("UPGRADED INCLUSIONS \u2013 AUX DWELLING" in dt and any("Robin EXAMPLE" in t for t in dt),
          "this job's document: the sample's specification, this job's client")
    check(not any("TESTOWNER" in t or "Placeholder" in t or "7701" in t or "611,100" in t for t in dt),
          "this job's document names nothing of the sample's client")
    r2 = py("sample_base.py", "--blank", GUNNEDAH, "--sample", sample, "--job", job, "--out-blank", base)
    check("unchanged - its Word measurement is reused" in r2.stdout, "the same sample again reuses the base as is")
    def repeated(path):
        with zipfile.ZipFile(path) as z:
            ids = re.findall(r'w14:paraId="([0-9A-Fa-f]+)"', z.read("word/document.xml").decode("utf-8"))
        return {i for i in ids if ids.count(i) > 1}
    # Word itself repeats the ids of a text box's paragraphs in its fallback copy
    # (86 in the Gunnedah blank); the transplant must add no repeat of its own
    check(repeated(doc) <= repeated(GUNNEDAH), "no paragraph id repeated beyond the blank's own text-box copies")

    black = make_sample(SCRATCH / "SAMPLE_black.docx", black_heading=True)
    r = py("sample_base.py", "--blank", GUNNEDAH, "--sample", black, "--job", job, "--out-blank", SCRATCH / "b0.docx")
    heads = [p for p in E.P_RE.findall(E.normalise_self_closing(E.read_xml(SCRATCH / "b0.docx")))
             if "AUX DWELLING" in E.ptext(p)] if (SCRATCH / "b0.docx").exists() else []
    check(r.returncode == 0 and "given the blank's heading formatting" in r.stdout
          and bool(heads) and bool(re.search(r'<w:color w:val="(?!000000)', heads[0])),
          "a sample heading left black takes the blank's heading blue (issue #58)")

    print("== stops")
    leak = make_sample(SCRATCH / "SAMPLE_leak.docx", extra_aux_line="As agreed with Jordan TESTOWNER")
    r = py("sample_base.py", "--blank", GUNNEDAH, "--sample", leak, "--job", job, "--out-blank", SCRATCH / "b1.docx")
    check(r.returncode == 1 and "names its own client" in r.stdout and not (SCRATCH / "b1.docx").exists(),
          "a sample whose specification names its client stops, nothing written")
    drift = make_sample(SCRATCH / "SAMPLE_drift.docx", change_standard=True)
    r = py("sample_base.py", "--blank", GUNNEDAH, "--sample", drift, "--job", job, "--out-blank", SCRATCH / "b2.docx")
    check(r.returncode == 1 and "built on another blank" in r.stdout and not (SCRATCH / "b2.docx").exists(),
          "a sample whose standard wording is not the blank's stops")
    if SEQ and SEQ.exists():
        r = py("sample_base.py", "--blank", SEQ, "--sample", sample, "--job", job, "--out-blank", SCRATCH / "b3.docx")
        check(r.returncode == 1 and "AUXILIARY blanks of their own" in r.stdout,
              "an SEQ blank refuses a sample base (QLD has an AUXILIARY blank)")
    nolist = SCRATCH / "SAMPLE_nolist.docx"
    shutil.copy2(sample, nolist)
    xml = E.read_xml(nolist).replace("UPGRADED INCLUSIONS \u2013 AUX DWELLING",
                                     "UPGRADED INCLUSIONS \u2013 AUX DWELLING", 1)
    a, b = E.body_table(E.normalise_self_closing(xml))
    body = E.normalise_self_closing(xml)[a:b]
    body2 = re.sub(r"(<w:pPr>)", r'\1<w:numPr><w:ilvl w:val="0"/><w:numId w:val="9999"/></w:numPr>', body, count=1)
    E.write_docx(nolist, nolist, E.normalise_self_closing(xml)[:a] + body2 + E.normalise_self_closing(xml)[b:])
    r = py("sample_base.py", "--blank", GUNNEDAH, "--sample", nolist, "--job", job, "--out-blank", SCRATCH / "b4.docx")
    check(r.returncode == 1 and "list numbering 9999 is not defined in the blank" in r.stdout,
          "a list the blank does not define stops")

    print("== removals")
    E.use_family("gunnedah")
    measure = SCRATCH / "base.measure.json"
    measure.write_text(json.dumps({"left": [{"i": 0, "text": "Letterbox", "page": 1, "top": 0}],
                                   "right": [], "pages": 16}), encoding="utf-8")

    def edit(items, name):
        j = dict(THIS, upgrades={"items": items})
        jp = SCRATCH / f"{name}.json"
        jp.write_text(json.dumps(j, ensure_ascii=False), encoding="utf-8")
        out = SCRATCH / f"{name}.docx"
        return py("edit_inclusions.py", "--docx", doc, "--job", jp, "--blank", base, "--blank-measure", measure,
                  "--out", out, "--plan", SCRATCH / f"{name}.plan.json", "--family", "gunnedah"), out

    r, out = edit([{"category": "Statutory Regulations", "dwelling": "aux", "mode": "remove",
                    "replaces": "Council Infrastructure charges", "confidence": "high",
                    "request": "just remove the note about infrastructure fees"}], "infra")
    check(r.returncode == 0, f"the request's removal applies (exit {r.returncode}) {r.stdout[-300:] if r.returncode else ''}")
    if out.exists():
        cols = E.Columns(E.read_xml(out))
        secs = E.upgraded_sections(cols)
        aux = next(s for s in secs if s["dwelling"] == "aux")
        labels = [E.norm(E.ptext(cols.left[i])) for i in aux["labels"]]
        check(labels == ["Shelving", "Benchtops", "Provisions"],
              f"the label left with nothing goes with its line (row 5): {labels}")
        check(INFRA not in ptexts(out), "the infrastructure note is gone")
        check("the line named was its only one" in r.stdout, "the report says the label went with its only line")
        import gate_inclusions
        E.use_family("gunnedah")
        rep = []
        gate_inclusions.check_xml(str(out), rep)
        check(not any("FAIL" in x for x in rep if x.startswith("colour")),
              f"the gate reads both dwelling headings as package headings: {[x for x in rep if x.startswith('colour')]}")
        plan = json.loads((SCRATCH / "infra.plan.json").read_text(encoding="utf-8"))
        pairs = [(s["left"], s["right"]) for s in plan["steps"] if s["kind"] == "pair"]
        check(("Provisions", "Includes one (1) off water meter") in pairs and
              not any(l == "Statutory Regulations" for l, _ in pairs),
              "the layout plan levels each aux label with its first line")
    r, out = edit([{"category": "Provisions", "dwelling": "aux", "mode": "remove", "replaces": "water meter"}], "one")
    if out.exists():
        cols = E.Columns(E.read_xml(out))
        aux = next(s for s in E.upgraded_sections(cols) if s["dwelling"] == "aux")
        labels = [E.norm(E.ptext(cols.left[i])) for i in aux["labels"]]
        t = ptexts(out)
        check("Provisions" in labels and "Includes one (1) off water meter" not in t
              and any("Separate TV antenna" in x for x in t),
              "one line of two goes; the label keeps the other")
    else:
        check(False, f"one line of two goes ({r.stdout[-200:]})")
    # "in" is in both Provisions lines ("Includes ...", "... the main residence ...")
    r, _ = edit([{"category": "Provisions", "dwelling": "aux", "mode": "remove", "replaces": "in"}], "twice")
    check(r.returncode != 0 and "name exactly one line" in (r.stdout + r.stderr), "a line named twice is refused")
    r, out = edit([{"category": "Cooktop", "dwelling": "aux", "wording": "Sample cooktop", "confidence": "high"}], "write")
    check(r.returncode == 1 and "stays a person's edit" in r.stdout and not out.exists(),
          "writing an upgrade line on Gunnedah is refused, nothing written")

    print("== headings")
    E.use_family("gunnedah")
    check(E.is_upgraded_heading("PROMOTIONAL UPGRADES \u2013 Main Dwelling")
          and E.is_upgraded_heading("UPGRADED INCLUSIONS \u2013 AUX DWELLING")
          and E.is_upgraded_heading("PROMOTIONAL UPGRADES")
          and E.dwelling_of("PROMOTIONAL UPGRADES \u2013 Main Dwelling") == "main",
          "Gunnedah reads both headings and the mixed-case dwelling")
    check(E.is_package_heading("UPGRADED INCLUSIONS \u2013 AUX DWELLING"),
          "the aux heading keeps the template's blue (a package heading)")
    E.use_family("seq")
    check(E.is_upgraded_heading("PROMOTIONAL UPGRADES") and not E.is_upgraded_heading("UPGRADED INCLUSIONS"),
          "SEQ reads its own heading only, as before")
    E.use_family("sydney")
    check(E.is_upgraded_heading("UPGRADED INCLUSIONS \u2013 AUX DWELLING")
          and not E.is_upgraded_heading("PROMOTIONAL UPGRADES"),
          "Sydney reads its own heading only, as before")

    print("== scan")
    r = py("sample_base.py", "--scan", doc, "--sample", sample, "--job", job)
    check(r.returncode == 0, "this job's document passes the last check")
    r = py("sample_base.py", "--scan", sample, "--sample", sample, "--job", job)
    check(r.returncode == 1 and "TESTOWNER" in r.stdout and "7701" in r.stdout,
          "a document still naming the sample's client fails the last check")
    same = dict(THIS, owner_1="Jordan TESTOWNER", owners="Jordan TESTOWNER")
    jp = SCRATCH / "same.json"
    jp.write_text(json.dumps(same, ensure_ascii=False), encoding="utf-8")
    r = py("sample_base.py", "--scan", sample, "--sample", sample, "--job", jp)
    check("owner" not in r.stdout.split("FAIL")[-1] or "TESTOWNER" not in r.stdout,
          "a name this job shares with the sample is not counted against it")


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
