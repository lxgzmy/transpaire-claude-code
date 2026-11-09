r"""Self-test for the job 26061 feedback sheet (9 Nov 2026). Synthetic values only.

    python test_feedback_0911.py

  rows 3, 7-10  the estate - ESTATE filled, and after the street wherever a
                street runs on into the address, NSW and QLD alike: the
                inclusions' signature-page STREET: and "located at;" box, the
                build contract's land STREET ADDRESS and cover SITE. Page 1's
                STREET : stays bare. A parent-address ESTATE stays put.
                The request's estate folder fills a blank ESTATE only when the
                request names the estate again outside the path.
  row 4         the Gunnedah blank's highlights cleared
  row 6         the Gunnedah signature lines on tab stops (one x per Date:)
  CD-6.6        --finish gives a hand-filled document the same finishing

Reads the live blanks under Z:\PROCEDURES & FORMS (read-only) and the staged
NSW build contract; writes only under runtime\contract-admin\state\ (removed
at the end). Routing (CD-7.5-7.7) is test_routing.py; the OSC rows 1-2 are
shared/mcp/osc-api/tests/test_write_gate.py.
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
import draft_contract as dc  # noqa: E402
import fill_hia  # noqa: E402
import street_format as S  # noqa: E402

SCRATCH = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "_feedback-0911-selftest"
CONTRACTS = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS")
GUNNEDAH = next(iter(sorted((CONTRACTS / "REGION - GUNNEDAH, NSW").glob("*INTEGRITY*.docx"))), None)
SEQ = next(iter(sorted((CONTRACTS / "REGION - SEQ" / "INCLUSIONS" / "INVESTOR & FIRST HOME OWNER")
                       .glob("[0-9]*.docx"))), None)
STAGED_NSW = dc.STAGED_HIA["NSW"]

NSW_JOB = {"lot_no": "9101", "street": "9 Sample Road", "suburb": "SAMPLEVILLE NSW",
           "estate": "Sample Heights", "house_type": "Sample 145 + Auxiliary Unit",
           "house_size": "232.72 m\u00b2", "facade": "Sample Fa\u00e7ade", "garage_side": "",
           "price": "600,000.00", "owner_1": "Alex Jordan SAMPLE", "owner_2": "",
           "owners": "Alex Jordan SAMPLE", "site_address": "9101, 9 Sample Road, SAMPLEVILLE NSW 2999",
           "builders_rep": "Michael CRONK", "job_no": "99999", "site_hia": "9 Sample Road, Sampleville",
           "land_street": "9 Sample Road", "land_suburb": "SAMPLEVILLE", "land_postcode": "2999",
           "dp_no": "", "owner_mobile": "0400 000 000", "owner_email": "alex@example.com",
           "owner_address": "1 Example Street", "owner_suburb": "EXAMPLETOWN", "owner_state": "NSW",
           "owner_postcode": "2000"}
QLD_JOB = {"lot_no": "9102", "street": "Example Drive", "suburb": "SAMPLETOWN QLD", "estate": "Sample Estate",
           "house_type": "Sample 200", "house_size": "200.00 m\u00b2", "facade": "Sample Fa\u00e7ade",
           "garage_side": "", "price": "500,000.00", "owner_1": "Sam SAMPLE", "owner_2": "",
           "owners": "Sam SAMPLE", "site_address": "9102, Example Drive (Sample Estate), SAMPLETOWN QLD 4000",
           "builders_rep": "Michael CRONK"}

fails = []


def check(cond, msg):
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    if not cond:
        fails.append(msg)


def text_of(docx):
    r = subprocess.run([sys.executable, str(HERE / "docx_text.py"), str(docx)],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def fill(blank, job, name):
    jf = SCRATCH / f"{name}.json"
    jf.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    out = SCRATCH / f"{name}.docx"
    r = subprocess.run([sys.executable, str(HERE / "fill_inclusions.py"), "--template", str(blank),
                        "--job", str(jf), "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
    return out, r.stdout + r.stderr


def estate_helpers():
    print("estate helpers (street_format)")
    check(S.with_estate("(9) Sample Road", "Sample Heights") == "(9) Sample Road, (Sample Heights)",
          "street + estate -> '(9) Sample Road, (Sample Heights)'")
    check(S.with_estate("Sample Road (Sample Heights)", "Sample Heights") == "Sample Road, (Sample Heights)",
          "estate already bracketed: only the comma added, never twice")
    check(S.estate_name("37 Example Road, (Sample Estate)") == "", "parent-address ESTATE is not an estate name")
    v, notes = S.estate_job({"street": "(9) Sample Road", "estate": "Sample Heights",
                             "site_address": "9101, (9) Sample Road, SAMPLEVILLE NSW 2999"})
    check(v["site_address"] == "9101, (9) Sample Road, (Sample Heights), SAMPLEVILLE NSW 2999" and not notes,
          "site address takes the estate after the street")
    v, _ = S.estate_job({"street": "Example Drive", "estate": "Sample Estate", "site_address": QLD_JOB["site_address"]})
    check(v["site_address"] == QLD_JOB["site_address"] and v["street_estate"] == "Example Drive, (Sample Estate)",
          "SEQ site address that names the estate is left as written; STREET: still gets it")
    v, _ = S.estate_job({"street": "Example Drive", "estate": "", "site_address": "1, Example Drive, X QLD 4000"})
    check(v["street_estate"] == "Example Drive" and v["site_address"] == "1, Example Drive, X QLD 4000",
          "no estate: nothing changes")


def estate_from_request():
    print("estate from the request (draft_contract.resolve_estate)")
    path = r"Z:\ESTATES INFORMATION\NSW\SAMPLEVILLE\SAMPLE HEIGHTS"
    check(dc.estates_named(f"see {path}\n", "NSW", "SAMPLEVILLE") == ["Sample Heights"], "estate folder read")
    check(dc.estates_named(r"Z:\ESTATES INFORMATION\NSW\SAMPLE REGION\SAMPLEVILLE", "NSW", "SAMPLEVILLE") == [],
          "a folder named for the suburb is not an estate")
    check(dc.estates_named(r"Z:\ESTATES INFORMATION\SEQ\SAMPLE\12 - 14 EXAMPLE ST, SAMPLE\Lot 6", "QLD", "X") == [],
          "a street folder is not an estate")
    check(dc.estates_named(r"Z:\ESTATES INFORMATION\SEQ\SAMPLE\SAMPLE ESTATE", "NSW", "X") == [],
          "another state's folder is not this job's estate")
    wd = SCRATCH / "estate-wd"
    wd.mkdir(parents=True, exist_ok=True)
    job = dict(NSW_JOB, estate="")
    jp = wd / "job.json"
    jp.write_text(json.dumps(job), encoding="utf-8")
    (wd / "email_original.txt").write_text(f"Hi\n{path}\nThanks\n", encoding="utf-8")
    out, v = dc.resolve_estate(job, jp, wd)
    check(out == jp and v["estate"] == "", "path alone (named nowhere else): ESTATE left blank, flagged")
    (wd / "email_original.txt").write_text(f"Lot 9101 Sample Heights contract\n{path}\n", encoding="utf-8")
    out, v = dc.resolve_estate(job, jp, wd)
    check(out.name == "job.estate.json" and v["estate"] == "Sample Heights"
          and json.loads(out.read_text(encoding="utf-8"))["estate"] == "Sample Heights",
          "path + the estate named in the request: ESTATE written in a resolved copy, flagged")
    out, v = dc.resolve_estate(dict(job, estate="Other Estate"), jp, wd)
    check(out == jp and v["estate"] == "Other Estate", "an ESTATE the job JSON sets is never replaced")


def gunnedah_inclusions():
    print("Gunnedah inclusions (NSW)")
    if not GUNNEDAH:
        check(False, "Gunnedah blank not found under Z:\\PROCEDURES & FORMS")
        return
    out, log = fill(GUNNEDAH, NSW_JOB, "gunnedah")
    text = text_of(out)
    check("ESTATE :" in text and re.search(r"ESTATE :\s*Sample Heights", text) is not None, "ESTATE : filled")
    check(re.search(r"STREET :\s*\(9\) Sample Road\s*~", text) is not None, "page 1 STREET : the bare street")
    check(text.count("STREET:   (9) Sample Road, (Sample Heights)") + text.count("STREET: (9) Sample Road, (Sample Heights)")
          >= 2 or len(re.findall(r"STREET:\s*\(9\) Sample Road, \(Sample Heights\)", text)) >= 2,
          "signature-page STREET: '(9) Sample Road, (Sample Heights)' on both copies")
    check("Lot 9101, (9) Sample Road, (Sample Heights), SAMPLEVILLE NSW 2999" in text,
          "'located at;' box 'Lot 9101, (9) Sample Road, (Sample Heights), SAMPLEVILLE NSW 2999'")
    xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    check("<w:highlight" not in xml and "highlight: 6 highlighted run(s)" in log,
          "the blank's six highlights cleared and listed in the report")
    lines = [p for p in re.findall(r"<w:p\b[^>]*>.*?</w:p>", xml, re.S)
             if "Date:" in p and re.search(r"Name of Owner 1:|Name of Owner 2:|Owners Witness Name:|"
                                           r"Builders Representative:", p)]
    on_tabs = [p for p in lines if 'w:pos="2235"' in p and 'w:pos="7560"' in p]
    check(len(lines) >= 8 and len(on_tabs) == len(lines),
          f"every signature line with a Date: on the 2235/7560 tab stops ({len(on_tabs)}/{len(lines)})")
    # --finish on a hand-filled document: the blank itself stands in for one
    fin = SCRATCH / "finished.docx"
    r = subprocess.run([sys.executable, str(HERE / "fill_inclusions.py"), "--template", str(GUNNEDAH),
                        "--finish", str(GUNNEDAH), "--out", str(fin)], capture_output=True, text=True, encoding="utf-8")
    fxml = zipfile.ZipFile(fin).read("word/document.xml").decode("utf-8") if fin.exists() else ""
    check(r.returncode == 0 and "<w:highlight" not in fxml and fxml.count('w:pos="7560"') >= 8
          and "Wording untouched" in r.stdout,
          "--finish: tab stops and no highlight on a document filled another way")
    # the signature lines' dotted leaders are trimmed to end before the Date: stop (CD-9.9); nothing else
    words = lambda x: re.sub(r"[\s…]+", "", "".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", x, re.S)))
    blank_xml = zipfile.ZipFile(GUNNEDAH).read("word/document.xml").decode("utf-8")
    check(words(fxml) == words(blank_xml), "--finish changes no wording (spaces and dotted leaders aside)")


def seq_inclusions():
    print("SEQ inclusions (QLD)")
    if not SEQ:
        check(False, "SEQ blank not found under Z:\\PROCEDURES & FORMS")
        return
    out, _ = fill(SEQ, QLD_JOB, "seq")
    text = text_of(out)
    check(len(re.findall(r"STREET:\s*Example Drive, \(Sample Estate\)", text)) >= 2,
          "signature-page STREET: 'Example Drive, (Sample Estate)' (the team's copy of 26059 had to add it)")
    check("Lot 9102, Example Drive (Sample Estate), SAMPLETOWN QLD 4000" in text,
          "site box as the job JSON writes it (SEQ's own form, already naming the estate)")


def nsw_build_contract():
    print("NSW build contract")
    v = fill_hia.derive_values(S.bracket_job(dict(NSW_JOB))[0], "NSW")
    check(v["land_street"] == "(9) Sample Road, (Sample Heights)", "item 5 STREET ADDRESS with the estate")
    check(v["site_hia"] == "(9) Sample Road, (Sample Heights), SAMPLEVILLE NSW 2999",
          "cover SITE: one line, estate, SUBURB NSW postcode")
    if not STAGED_NSW.exists():
        check(False, f"staged NSW template missing: {STAGED_NSW}")
        return
    jf = SCRATCH / "nsw-bc.json"
    jf.write_text(json.dumps(NSW_JOB, ensure_ascii=False), encoding="utf-8")
    out = SCRATCH / "nsw-bc.docx"
    r = subprocess.run([sys.executable, str(HERE / "fill_hia.py"), "--template", str(STAGED_NSW), "--job", str(jf),
                        "--out", str(out), "--region", "NSW"], capture_output=True, text=True, encoding="utf-8")
    text = text_of(out) if out.exists() else ""
    check(r.returncode == 0 and "(9) Sample Road, (Sample Heights), SAMPLEVILLE NSW 2999" in text
          and "(9) Sample Road, (Sample Heights)" in text.split("SAMPLEVILLE NSW 2999", 1)[-1],
          "filled contract: cover SITE and The Land read with the estate")


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    estate_helpers()
    estate_from_request()
    gunnedah_inclusions()
    seq_inclusions()
    nsw_build_contract()
    shutil.rmtree(SCRATCH, ignore_errors=True)
    print(("FAIL - " + "; ".join(fails)) if fails else "PASS - 0 failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
