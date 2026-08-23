r"""Report whether the HIA/NSW build contract can be produced yet. Stdlib only.

    python hia_probe.py                          # every region's contract folder
    python hia_probe.py --region TAMWORTH        # one region (job region, not folder name)
    python hia_probe.py --job-dir "<job's CONTRACT DOCUMENTATION>"   # region from the path

The business holds a valid HIA licence (17 Aug 2026), so the HIA build contract
is REQUIRED to ship as a filled .docx + .pdf pair (CD-5.2a) - but only once a
current fillable Word blank exists in the region's contract-template folder.
This probe is the detection half of that requirement: it classifies every
build-contract blank and says, machine-readably, whether the region is still
BLOCKED (data sheet only) or a CANDIDATE template has landed.

Classification, in the order the rules bite (CD-1.3, CD-5.1, CD-5.2a):

  SUPERSEDED   under an SS\ folder - forbidden, whatever it looks like
  OFF-LIMITS   name carries DONT USE - off-limits until MCR approves
  FLAT PDF     a .pdf with no form text fields - this server cannot fill it
  FILLABLE PDF a .pdf WITH form text fields - new capability question; the
               pipeline fills .docx only, so tell a person before relying on it
  CANDIDATE    a live .docx build-contract blank outside SS, not DONT USE -
               the unblock. The probe NEVER fills it: the fill step
               (fill_hia.py) must first be authored and verified against the
               real template, like every other filler here, and regressed
               against completed contracts. Commissioning that is a person's
               call.

Verdict line per region, for the driver to relay:

  hia contract: BLOCKED - ...        (produce the CD-5 data sheet, flag the gap)
  hia contract: CANDIDATE - <name>   (template landed; fill step not yet
                                      commissioned - still data sheet this run)

draft_contract.py runs this on every --job-dir save and writes hia_status.txt
into the workdir, so the status ships with the evidence instead of relying on
hand-written prose staying accurate.

Path to the unblock (trialled 17 Aug 2026, see
runtime\contract-admin\outputs\_hia-conversion-trial\trial-report.md): Word's
PDF reflow converts the licensed blanks at ~95% text fidelity but breaks
pagination, tables and checkbox blocks - a person repairs the reflow docx page
by page against the PDF, MCR approves it, and it lands in the region's CONTRACT
folder, where this probe picks it up.
"""
import argparse
import re
import sys
from pathlib import Path

CONTRACTS_ROOT = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS")

# Job region -> the contract-template folder its build contract comes from.
# Tamworth/Gunnedah have no contract folder of their own: NSW jobs take the
# NSW contract filed under Sydney (references/contract-template-map.md).
REGION_TO_FOLDER = {
    "TAMWORTH": ("NSW", Path(r"REGION - SYDNEY\CONTRACT")),
    "GUNNEDAH": ("NSW", Path(r"REGION - SYDNEY\CONTRACT")),
    "SYDNEY":   ("NSW", Path(r"REGION - SYDNEY\CONTRACT")),
    "SEQ":      ("QLD", Path(r"REGION - SEQ\CONTRACT")),
    "CUDGEN":   ("QLD", Path(r"REGION - SEQ\CONTRACT")),
}

# A build-contract blank, by name: "BUILD CONTRACT" or HIA + CONTRACT. This
# deliberately catches the Gables-specific one too (it is a build contract).
# NOT_BLANK_RE removes pack items and land contracts that share those words:
# the general conditions, the consumer guide, the Gables sales contract.
BLANK_RE = re.compile(r"BUILD CONTRACT|HIA.*CONTRACT|CONTRACT.*HIA", re.I)
NOT_BLANK_RE = re.compile(r"GENERAL CONDITIONS|SALES CONTRACT|CONSUMER", re.I)


def pdf_text_fields(path):
    """Count of /FT /Tx text fields in the raw bytes (pdf_probe.py's check)."""
    data = path.read_bytes()
    return len(re.findall(rb"/FT\s*/Tx", data))


def classify(folder):
    """(status, path, note) for every build-contract blank under folder."""
    rows = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.name.startswith("~$"):
            continue
        if not BLANK_RE.search(p.stem) or NOT_BLANK_RE.search(p.stem):
            continue
        if p.suffix.lower() not in (".docx", ".pdf"):
            continue
        rel = p.relative_to(folder)
        if any(part.upper() == "SS" for part in rel.parts):
            rows.append(("SUPERSEDED", rel, "SS\\ - forbidden (CD-1.3)"))
        elif "DONT USE" in p.stem.upper():
            rows.append(("OFF-LIMITS", rel, "until MCR approves"))
        elif p.suffix.lower() == ".pdf":
            n = pdf_text_fields(p)
            if n:
                rows.append(("FILLABLE PDF", rel,
                             f"{n} text field(s) - pipeline fills .docx only; tell a person"))
            else:
                rows.append(("FLAT PDF", rel, "no form fields - cannot fill (CD-5.1)"))
        else:
            rows.append(("CANDIDATE", rel, "live .docx blank - fill step not yet "
                                           "commissioned/verified against it"))
    return rows


def region_from_job_dir(job_dir):
    parts = [p.upper() for p in Path(job_dir).parts]
    if "PROJECTS" in parts:
        idx = parts.index("PROJECTS")
        if idx + 1 < len(parts) and parts[idx + 1] in REGION_TO_FOLDER:
            return parts[idx + 1]
    return None


def report(region):
    state, sub = REGION_TO_FOLDER[region]
    folder = CONTRACTS_ROOT / sub
    print(f"=== {region} job -> {state} build contract -> {folder}")
    if not folder.is_dir():
        print("  ERROR: contract folder not found - check the Z: mapping")
        print("  hia contract: BLOCKED - contract folder unreachable")
        return "BLOCKED"
    rows = classify(folder)
    for status, rel, note in rows:
        print(f"  {status:<13} {rel}   ({note})")
    if not rows:
        print("  (no build-contract blanks found at all)")
    candidates = [rel for status, rel, _ in rows if status == "CANDIDATE"]
    fillable_pdfs = [rel for status, rel, _ in rows if status == "FILLABLE PDF"]
    if candidates:
        names = "; ".join(str(c) for c in candidates)
        print(f"  hia contract: CANDIDATE - {names}. NOT filled this run: the fill "
              f"step must be authored and verified against it first (CD-5.2a).")
        return "CANDIDATE"
    extra = (f" (a FILLABLE PDF exists - {fillable_pdfs[0]} - but the pipeline "
             f"fills .docx only; tell a person)" if fillable_pdfs else "")
    print(f"  hia contract: BLOCKED - no fillable Word blank; data sheet only "
          f"(CD-5.1/5.2a){extra}")
    return "BLOCKED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", help="job region: " + ", ".join(REGION_TO_FOLDER))
    ap.add_argument("--job-dir", help="the job's CONTRACT DOCUMENTATION folder - "
                                      "the region is read from the path")
    args = ap.parse_args()

    if args.job_dir:
        region = region_from_job_dir(args.job_dir)
        if not region:
            print(f"  hia contract: region not recognised in path {args.job_dir} - "
                  f"probing every region instead")
            regions = list(REGION_TO_FOLDER)
        else:
            regions = [region]
    elif args.region:
        r = args.region.upper()
        if r not in REGION_TO_FOLDER:
            sys.exit(f"ERROR: unknown region {args.region!r} - one of: "
                     + ", ".join(REGION_TO_FOLDER))
        regions = [r]
    else:
        regions = list(REGION_TO_FOLDER)

    # De-duplicate regions that share a contract folder for the all-regions view
    seen = set()
    for r in regions:
        folder = REGION_TO_FOLDER[r][1]
        if len(regions) > 1 and folder in seen:
            continue
        seen.add(folder)
        report(r)
        print()
    return 0


# This console is cp1252; template names can carry anything.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
