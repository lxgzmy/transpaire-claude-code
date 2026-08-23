r"""Regression for fill_hia.py against both staged HIA templates. Stdlib only.

    python regress_hia.py

Run after any fill_hia.py change, alongside regress_inclusions.py and
regress_prelim.py. Uses SYNTHETIC values only (no client data): for each
region it asserts that

  1. --check resolves every anchor on that region's staged template
     (a miss means the template or the anchor set changed - stop and look),
  2. a fill writes a docx whose document.xml still parses,
  3. every synthetic value actually appears in the filled text, and
  4. every replaced prefill/placeholder is gone (the $25.00 LD figure, and on
     NSW the $000,000.00-style price placeholders when figures are supplied).

NSW's staged template is the team's own Word build (21 Aug 2026); QLD's is
still the repaired PDF conversion. The staged templates live in runtime\
(this machine's checkout), so the test SKIPS with a notice on a clone that
has no staged templates - it can only pass or fail where they exist.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGED = HERE.parents[2] / "runtime" / "contract-admin" / "outputs" / "_hia-word-templates"

SYNTH = {
    "NSW": {
        "template": STAGED / "NSW BUILD CONTRACT Final 21.08.2026 - TEAM BUILD PENDING MCR.docx",
        "values": {
            "owners": "Testfirst TESTSURNAME & Second TESTOWNER",
            "job_no": "99991", "lot_no": "901",
            "site_hia": "(9) Sample Street, SAMPLEVILLE NSW 2999",
            "owner_1": "Testfirst TESTSURNAME", "owner_2": "Second TESTOWNER",
            "owner_address": "9 Example Road",
            "owner_suburb": "EXAMPLETON", "owner_state": "NSW", "owner_postcode": "2998",
            "owner_mobile": "0400 000 001", "owner_email": "regress@example.invalid",
            "dp_no": "1234567", "land_street": "(9) Sample Street",
            "land_suburb": "SAMPLEVILLE", "land_postcode": "2999",
            "liq_damages": "$77.00", "builders_rep": "Regress REPNAME",
            "guarantor_name": "Guaran TESTGUARANTOR",
            "guarantor_address": "9 Guarantee Grove",
            "guarantor_suburb": "EXAMPLETON", "guarantor_state": "NSW",
            "guarantor_postcode": "2997",
            # CD-5.4: figures only ever arrive pre-keyed from DataBuild
            "price_excl_gst": "$636,363.64", "gst_amount": "$63,636.36",
            "price_incl_gst": "$700,000.00", "deposit": "$70,000.00",
        },
        # prefills/placeholders that must NOT survive the fill
        "gone": ["$25.00", "$000,000.00", "$00,00.00", "$00,000.00"],
    },
    "QLD": {
        "template": STAGED / "QLD HIA BUILD CONTRACT 09.02.2023 upd 30.07.26 - REPAIRED UNAPPROVED.docx",
        "values": {
            "owners": "Testfirst TESTSURNAME", "job_no": "99992", "lot_no": "902",
            "site_hia": "Sample Street, SAMPLEVILLE QLD 4999",
            "owner_1": "Testfirst TESTSURNAME", "owner_address": "9 Example Road",
            "owner_suburb": "EXAMPLETON", "owner_state": "QLD", "owner_postcode": "4998",
            "owner_mobile": "0400 000 002", "owner_email": "regress@example.invalid",
            "sp_rp": "SP999999", "land_street": "Sample Street",
            "land_suburb": "SAMPLEVILLE", "land_state": "QLD", "land_postcode": "4999",
            "liq_damages": "$88.00",
        },
        "gone": ["$ 25.00"],
    },
}


def docx_text(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    ET.fromstring(xml)  # assertion 2: the XML still parses
    return re.sub(" +", " ", " ".join(
        html.unescape(m.group(1))
        for m in re.finditer(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml, re.S)))


def run(region, spec, tmp):
    template, values = spec["template"], spec["values"]
    if not template.exists():
        print(f"  {region}: SKIP - no staged template at {template}")
        return None
    job = Path(tmp) / f"job_{region}.json"
    job.write_text(json.dumps(values), encoding="utf-8")
    out = Path(tmp) / f"filled_{region}.docx"

    check = subprocess.run([sys.executable, str(HERE / "fill_hia.py"), "--template",
                            str(template), "--job", str(job), "--check",
                            "--region", region],
                           capture_output=True, text=True, encoding="utf-8")
    if check.returncode != 0 or "ANCHOR MISSING" in check.stdout:
        print(f"  {region}: FAIL - anchor check\n{check.stdout}{check.stderr}")
        return False

    fill = subprocess.run([sys.executable, str(HERE / "fill_hia.py"), "--template",
                           str(template), "--job", str(job), "--out", str(out),
                           "--region", region],
                          capture_output=True, text=True, encoding="utf-8")
    if fill.returncode != 0 or not out.exists():
        print(f"  {region}: FAIL - fill\n{fill.stdout}{fill.stderr}")
        return False

    text = docx_text(out)
    missing = [v for v in values.values()
               if v and re.sub(" +", " ", v) not in text]
    if missing:
        print(f"  {region}: FAIL - value(s) not in the filled text: {missing}")
        return False
    survived = [g for g in spec["gone"] if g in text]
    if survived:
        print(f"  {region}: FAIL - prefill(s)/placeholder(s) survived a fill that "
              f"should have replaced them: {survived}")
        return False
    print(f"  {region}: PASS ({len([v for v in values.values() if v])} values filled, "
          f"XML valid, {len(spec['gone'])} prefill(s) replaced)")
    return True


def legacy_key_split():
    """Older NSW job JSONs carry 'SUBURB POSTCODE' as one land_suburb_pc value;
    the filler must split it for the team-build template's separate labels."""
    sys.path.insert(0, str(HERE))
    import fill_hia
    d = fill_hia.derive_values(
        {"land_suburb_pc": "SAMPLEVILLE 2999", "owners": "A", "owner_1": "A"}, "NSW")
    ok = d.get("land_suburb") == "SAMPLEVILLE" and d.get("land_postcode") == "2999"
    print(f"  legacy land_suburb_pc split: {'PASS' if ok else 'FAIL - ' + repr(d)}")
    return ok


def main():
    print("regress_hia: fill_hia.py vs the staged HIA templates (synthetic values)")
    results = [legacy_key_split()]
    with tempfile.TemporaryDirectory(dir=STAGED.parent if STAGED.parent.is_dir() else None) as tmp:
        for region, spec in SYNTH.items():
            results.append(run(region, spec, tmp))
    if any(r is False for r in results):
        return 1
    if all(r is None for r in results):
        print("  every region skipped - no staged templates on this checkout")
    return 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
