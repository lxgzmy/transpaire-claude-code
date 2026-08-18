r"""Regression for fill_hia.py against both staged HIA conversions. Stdlib only.

    python regress_hia.py

Run after any fill_hia.py change, alongside regress_inclusions.py and
regress_prelim.py. Uses SYNTHETIC values only (no client data): for each
region it asserts that

  1. --check resolves every anchor on that region's staged template
     (a miss means the template or the anchor set changed - stop and look),
  2. a fill writes a docx whose document.xml still parses,
  3. every synthetic value actually appears in the filled text, and
  4. the NSW liquidated-damages replacement swaps the $25.00 prefill.

The staged templates live in runtime\ (this machine's checkout), so the test
SKIPS with a notice on a clone that has no staged conversions - it can only
pass or fail where the templates exist.
"""
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
        "template": STAGED / "NSW BUILD CONTRACT upd 30.07.2026 - REPAIRED UNAPPROVED.docx",
        "values": {
            "owners": "Testfirst TESTSURNAME", "job_no": "99991", "lot_no": "901",
            "site_hia": "(9) Sample Street, SAMPLEVILLE NSW 2999",
            "owner_1": "Testfirst TESTSURNAME", "owner_address": "9 Example Road",
            "owner_suburb": "EXAMPLETON", "owner_state": "NSW", "owner_postcode": "2998",
            "owner_mobile": "0400 000 001", "owner_email": "regress@example.invalid",
            "dp_no": "1234567", "land_street": "(9) Sample Street",
            "land_suburb_pc": "SAMPLEVILLE 2999", "liq_damages": "$77.00",
        },
        "replaced_prefill": "$25.00",
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
        "replaced_prefill": "$ 25.00",
    },
}


def docx_text(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    ET.fromstring(xml)  # assertion 2: the XML still parses
    return re.sub(" +", " ", " ".join(
        m.group(1) for m in re.finditer(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml, re.S)))


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
    if spec["replaced_prefill"] in text:
        print(f"  {region}: FAIL - the {spec['replaced_prefill']} LD prefill survived "
              f"a fill that should have replaced it")
        return False
    print(f"  {region}: PASS ({len([v for v in values.values() if v])} values filled, "
          f"XML valid, LD prefill replaced)")
    return True


def main():
    print("regress_hia: fill_hia.py vs the staged HIA conversions (synthetic values)")
    results = []
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
