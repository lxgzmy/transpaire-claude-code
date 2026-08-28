"""Check fill_prelim.py still reproduces the corrected preliminary agreements.

    python regress_prelim.py

Reference set (28 Aug 2026): the three Sydney agreements the team corrected by
hand and then held up as the standard in their review of the AI-filled
documents (AI.Manual.comparison (2).xlsx, "Preliminary Agreement" sheet) -
jobs 26032 (single client, fee left at the standard $30,000), 26052 (two
clients) and 26019 (single client). These supersede the two Tamworth
agreements (26036/26045) the previous suite reproduced: the team's feedback
rejects exactly the Tamworth cosmetics the old suite enforced (the 62-space
layout run, names on tab stops, cloned signature fonts).

For each reference job: read the fill values back out of the corrected
document, fill the current blank with them, and require the two documents'
full visible text to be identical ignoring spaces (the editors hand-type
1-9 spaces of lead; no other character may differ). 26032 and 26052 must
also match block-for-block on structure (tabs/breaks/cells, space runs
collapsed) - that is where the spacing conventions are held. 26019 carries
a stray hand-typed tab after the residential address, so it is text-only.

Two deliberate deviations from the corrected documents, both from the sheet:
two buyers get ("Clients") where the corrected 26052 kept the template's
("Client") - normalised before comparing - and signature names are typed at
Calibri 12 where the corrected documents sit at 10-11pt (font size is
invisible to text comparison; the synthetic suite asserts it in the XML).

A synthetic two-client fill then asserts what text comparison cannot see:
inline names + ("Clients"), the residential label starting its own paragraph,
the standard-fee default, Calibri-12 signature runs, and the re-indented
sunset clause and spacer.

Exit code 0 = all suites pass.
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fill_prelim as fp  # anchors, pPr/rPr targets and regexes stay in sync

BLANK = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS\REGION - SYDNEY\CONTRACT"
             r"\NSW PRELIMINARY AGREEMENT 2024.docx")
# Resolved by job number at runtime - completed filenames carry client
# surnames, which stay out of this repo.
SYDNEY = Path(r"Z:\PROJECTS\SYDNEY")
#            label                                glob      drop_fee  structure
REF_JOBS = [("26032 lot 5085 (single, std fee)", "26032*", True,  True),
            ("26052 lot 2053 (two clients)",     "26052*", False, True),
            ("26019 lot 4153 (single)",          "26019*", False, False)]

RESI_LABEL = fp.RESI_LABEL
CONS_LABEL = fp.CONS_LABEL


def ref_doc(pattern):
    for job in SYDNEY.glob(pattern):
        hit = next((job / "CONTRACT" / "CONTRACT DOCUMENTATION")
                   .glob("PRELIMINARY AGREEMENT*.docx"), None)
        if hit:
            return hit
    return None


def text(path):
    """All visible text, run boundaries ignored."""
    import html
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    return html.unescape("".join(
        m.group(1) for m in re.finditer(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml, re.S)))


def structure(path):
    """docx_text's view: blocks with tabs/breaks/cells encoded. Catches an
    extra or missing tab that pure run-text comparison is blind to - the
    corrected agreements keep exactly one tab before ("Client"), and the
    split residential-address paragraph must be a real paragraph, not a
    line's worth of spaces."""
    import xml.etree.ElementTree as ET
    from docx_text import walk
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    return walk(root)


def norm(s, plural=False, spaceless=False):
    """Collapse space runs (hand-typed lead varies 1-9 spaces across the
    corrected documents); optionally fold the sheet-mandated ("Clients")
    back to the ("Client") the corrected 26052 kept. spaceless drops spaces
    entirely - the text suite runs characters-only (26019 carries a stray
    hand-typed tab-and-space; the structure suites on the clean pair are
    what hold the spacing)."""
    if plural:
        s = s.replace("Clients”", "Client”")
    return s.replace(" ", "") if spaceless else re.sub(r" {2,}", " ", s)


def values_from(real):
    """Read the fill values back out of a corrected agreement."""
    t = text(real)
    names = re.search(r"Constructions”\)And\s+(.+?)\s*\(“Client",
                      t).group(1).strip()
    owner_1, _, owner_2 = names.partition(" & ")
    resi = re.search(re.escape(RESI_LABEL) + r"\s+(.+?)\s*\(For", t).group(1)
    cons = re.search(re.escape(CONS_LABEL) + r"\s+Lot (.+?)Herein", t).group(1)
    fee = re.search(r"pay Transpire Constructions \$([\d,]+)\.", t).group(1)
    return {"owner_1": owner_1, "owner_2": owner_2.strip(),
            "residential_address": resi.strip(), "site_address": cons.strip(),
            "prelim_fee": fee, "builders_rep": "Michael CRONK"}


def run_fill(vals, out):
    jf = out.with_name("job.json")
    jf.write_text(json.dumps(vals, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(HERE / "fill_prelim.py"),
                        "--template", str(BLANK), "--job", str(jf),
                        "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8")
    jf.unlink(missing_ok=True)
    return r


def main():
    tmp = HERE.parent.parent.parent / "runtime" / "contract-admin" / "reports" / "_regress"
    tmp.mkdir(parents=True, exist_ok=True)
    failures = 0

    for name, pattern, drop_fee, with_structure in REF_JOBS:
        real = ref_doc(pattern)
        if not real:
            print(f"FAIL  {name} - no corrected agreement found for {pattern}")
            failures += 1
            continue
        vals = values_from(real)
        plural = bool(vals["owner_2"])
        if drop_fee:
            vals["prelim_fee"] = ""   # exercises the standard-fee default
        out = tmp / "prelim_filled.docx"
        r = run_fill(vals, out)
        if not out.exists():
            print(f"FAIL  {name} - fill did not run: {r.stderr.strip()[:200]}")
            failures += 1
            continue
        got = norm(text(out), plural, spaceless=True)
        want = norm(text(real), plural, spaceless=True)
        got_s = ([(k, norm(t, plural)) for k, t in structure(out)]
                 if with_structure else None)
        want_s = ([(k, norm(t, plural)) for k, t in structure(real)]
                  if with_structure else None)
        out.unlink(missing_ok=True)
        if got == want and got_s == want_s:
            what = "text AND structure" if with_structure else "text (spaces ignored)"
            print(f"PASS  {name} - {what} identical to the corrected agreement")
        elif got != want:
            failures += 1
            i = next((k for k, (a, b) in enumerate(zip(got, want)) if a != b),
                     min(len(got), len(want)))
            print(f"FAIL  {name} - first text divergence at char {i}:")
            print(f"      filled: ...{got[max(0, i-40):i+40]!r}")
            print(f"      real  : ...{want[max(0, i-40):i+40]!r}")
        else:
            failures += 1
            i = next((k for k, (a, b) in enumerate(zip(got_s, want_s)) if a != b),
                     min(len(got_s), len(want_s)))
            print(f"FAIL  {name} - text matches but structure differs at block {i + 1}:")
            print(f"      filled: {got_s[i] if i < len(got_s) else '(missing)'}")
            print(f"      real  : {want_s[i] if i < len(want_s) else '(missing)'}")

    # synthetic two-client suite: everything text comparison cannot see
    vals = {"owner_1": "Alpha ONE", "owner_2": "Beta TWO",
            "residential_address": "1 Test Street, TESTVILLE NSW 2000",
            "site_address": "9, Example Road, TESTVILLE NSW 2000",
            "prelim_fee": "", "builders_rep": "Michael CRONK"}
    out = tmp / "prelim_two.docx"
    r = run_fill(vals, out)
    if not out.exists():
        print(f"FAIL  two-client smoke - fill did not run: {r.stderr.strip()[:200]}")
        failures += 1
    else:
        t = text(out)
        blocks = structure(out)
        xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf8")
        out.unlink(missing_ok=True)
        ps = [m.group(0) for m in fp.P_RE.finditer(xml)]
        sun = next((n for n, p in enumerate(ps)
                    if fp.SUNSET_ANCHOR in fp.run_text(p)), None)

        def ppr_ok(n):
            m = fp.PPR_RE.search(ps[n]) if n is not None and 0 <= n < len(ps) else None
            return bool(m) and m.group(0) == fp.BODY_PPR

        checks = [
            ("names flow inline after And",
             "And  Alpha ONE & Beta TWO" in t),
            ("two buyers sign as (“Clients”)",
             "(“Clients”)" in t and "(“Client”)" not in t),
            # docx_text counts pPr tab-stop definitions as " | ", so a block
            # can lead with marker noise; "own paragraph" = nothing but that
            # noise before the label
            ("residential label starts its own paragraph",
             any(RESI_LABEL in b
                 and not b.split(RESI_LABEL)[0].strip(" |/")
                 for _, b in blocks)),
            ("standard fee kept when none supplied", "$30,000." in t),
            ("owner 1 signing line", "  Alpha ONE" in t),
            ("owner 2 signing line", "  Beta TWO" in t),
            ("builders rep signing line", "   Michael CRONK" in t),
            ("signature names typed Calibri 12", xml.count(fp.SIG_RPR) == 3),
            ("sunset clause ¶ re-indented", ppr_ok(sun)),
            ("spacer above sunset ¶ re-indented",
             ppr_ok(sun - 1 if sun is not None else None)),
        ]
        bad = [label for label, ok in checks if not ok]
        if bad:
            failures += 1
            print(f"FAIL  two-client smoke - {', '.join(bad)}")
        else:
            print("PASS  two-client smoke - structure, fonts and indents hold")

    print("\n" + ("PASS" if not failures else f"FAIL - {failures} suite(s)"))
    return 1 if failures else 0


# This console is cp1252; document text carries curly quotes and dotted leaders.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
