# DocuSign draft envelope implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After `/new-contract-template` saves a real build contract into a job folder, create a DocuSign **draft** envelope (status `created`, never sent) from the right company template with the buyers, subject and message filled from the job.

**Architecture:** A pure Python script, `docusign_payload.py`, turns the job JSON plus the driver's route record into one envelope payload file and a readable mapping report; it never touches the network. Claude then performs three read calls and one gated create call on the `docusign-demo` MCP, following a reference document written in the style of the OSC intake reference. The approval prompt on the create call is the human gate.

**Tech Stack:** Python 3.11+ stdlib only (the server has no `python-docx`, no `pytest`; self-tests are plain scripts run with `python test_x.py`), Markdown skill/rule docs, `docusign-demo` MCP (`createEnvelope`, `getTemplates`, `getEnvelopes`, `getUserInfo`).

**Spec:** [`docs/superpowers/brainstorms/2026-10-13-docusign-draft-envelope.md`](../brainstorms/2026-10-13-docusign-draft-envelope.md)

## Global Constraints

- Branch: `docusign-integration` (already exists, matches `main`). Every change lands through a PR; never commit to `main`; no AI attribution trailers.
- No client data anywhere in the repo: tests use synthetic names, emails and job numbers only. Never copy template role defaults (real people) into code, tests or docs.
- Never pass `status: "sent"`, never `updateEnvelope` to send, never a `remoteUrl`, never set internal roles, never void, never call `createEnvelopeFromTemplate`.
- The draft is created only when `BUILD CONTRACT` routed `PRODUCTION`; a `TEST` route produces the payload files and no call.
- Template is matched by exact name **after trimming whitespace** (three stored names carry a trailing space). No template id is stored in the repo.
- Subject: `Complete with DocuSign: BUILD CONTRACT - LOT <lot>, <SUBURB>` (suburb in capitals, state word dropped, same rule as `doc_suffix`).
- Message (fixed, never regenerated per job): `Dear <first names joined " & ">,` blank line, `Please find the building contract for review and signing.` blank line, `Thank you`, `Sales Admin`.
- Custom field: `textCustomFields: [{name: "JobNo", value: <job_no>, show: "false", required: "false"}]`.
- Scripts live in `job-roles/contract-admin/scripts/`; run them from the repo root as `python job-roles/contract-admin/scripts/<name>.py`. They are stdlib-only and import siblings via `sys.path.insert(0, HERE)`.
- Markdown in this repo uses compact tables (`|---|---|`); keep that style.

---

## File structure

| File | Responsibility |
|---|---|
| `job-roles/contract-admin/scripts/draft_contract.py` (modify) | Add `is_company_owner(name)` beside `owner_token`, and `write_routes(workdir, routes)` that records each document's route to `routes.txt` after the driver decides it |
| `job-roles/contract-admin/scripts/docusign_payload.py` (create) | Template pick, recipient mapping, subject/message, custom field, stop conditions; writes `docusign_envelope.json` + `docusign_payload.txt` |
| `job-roles/contract-admin/scripts/test_docusign_payload.py` (create) | Synthetic self-test, plain asserts, temp workdir |
| `job-roles/contract-admin/scripts/test_routing.py` (modify) | One extra check for `write_routes` |
| `job-roles/contract-admin/scripts/README.md` (modify) | Two table rows |
| `.claude/skills/new-contract-template/references/docusign-draft.md` (create) | The MCP procedure Claude follows: calls in order, checks, stops, never-list |
| `.claude/skills/new-contract-template/SKILL.md` (modify) | Step 8, step 7 report lines, Safety rules sentence, description line |
| `job-roles/contract-admin/rules/contract-docs.md` (modify) | `CD-10` block; CD-8 wording |
| `job-roles/contract-admin/workflows/new-contract.md` (modify) | Step 8 row, HITL section, Outputs, Relies on |
| `job-roles/contract-admin/CLAUDE.md`, `CLAUDE.md` (modify) | One HITL paragraph each |
| `docs/mcp-servers.md` (modify) | Read-only tools on `allow`; the draft step described |
| `.claude/settings.json` (modify) | Four read-only DocuSign tools to `allow` |

---

### Task 1: Driver records the per-document route, and exposes the company-owner test

**Files:**
- Modify: `job-roles/contract-admin/scripts/draft_contract.py` (near line 131 `COMPANY_TAILS` / `owner_token`, and in `main()` after the `route     :` print loop around line 450)
- Test: `job-roles/contract-admin/scripts/test_routing.py`

**Interfaces:**
- Produces: `is_company_owner(name: str) -> bool` and `write_routes(workdir: Path, routes: dict[str, tuple[str, Path]]) -> Path` in `draft_contract.py`. `routes.txt` format, one line per kind: `<KIND>\t<PRODUCTION|TEST>\t<destination>`. Task 2 imports both.

- [ ] **Step 1: Add the failing checks to `test_routing.py`**

Append before the final summary/cleanup of the file (keep the existing cases intact):

```python
def check_write_routes_and_company():
    wd = SCRATCH / "routes-wd"
    wd.mkdir(parents=True, exist_ok=True)
    routes = {"BUILD CONTRACT": ("PRODUCTION", Path(r"Z:\PROJECTS\X\CONTRACT DOCUMENTATION")),
              "INCLUSIONS": ("TEST", Path(r"Z:\T\template-testing\job"))}
    out = dc.write_routes(wd, routes)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["BUILD CONTRACT\tPRODUCTION\tZ:\\PROJECTS\\X\\CONTRACT DOCUMENTATION",
                     "INCLUSIONS\tTEST\tZ:\\T\\template-testing\\job"], lines
    assert dc.is_company_owner("EXAMPLE HOLDINGS PTY LTD ATF EXAMPLE FAMILY TRUST")
    assert dc.is_company_owner("Sample Nominees Pty. Ltd.")
    assert dc.is_company_owner("THE EXAMPLE FAMILY TRUST")
    assert not dc.is_company_owner("Alex EXAMPLE")
    print("  write_routes + is_company_owner: ok")
```

and call `check_write_routes_and_company()` where the other checks are invoked.

- [ ] **Step 2: Run it and watch it fail**

Run: `python job-roles/contract-admin/scripts/test_routing.py`
Expected: `AttributeError: module 'draft_contract' has no attribute 'write_routes'`

- [ ] **Step 3: Implement**

In `draft_contract.py`, replace the body of `owner_token` so the company test is shared:

```python
def is_company_owner(name):
    """True when the owner is a company or trust (CD-3.9), by the same tail
    test owner_token uses for the filename token."""
    up = " ".join(str(name).upper().replace(".", "").split())
    up = up.split(" ATF ")[0]
    for tail in COMPANY_TAILS:
        if f" {tail.replace('.', '')} " in f" {up} ":
            return True
    return up.endswith("TRUST")


def owner_token(name):
    """(docstring unchanged)"""
    up = " ".join(name.upper().replace(".", "").split())
    up = up.split(" ATF ")[0]  # trustee-for clause never feeds the filename
    if is_company_owner(name):
        return up.split()[0]
    return name.split(" ATF ")[0].split()[-1].upper()
```

Add after `route_kind`:

```python
def write_routes(workdir, routes):
    """Record each document kind's decided route so later steps (the DocuSign
    draft, step 8) can read it without re-deriving it after the save - after
    the save the job folder holds the document, so a recomputation would say
    TEST for what was in fact a PRODUCTION first draft."""
    out = Path(workdir) / "routes.txt"
    lines = [f"{kind}\t{mode}\t{dest}" for kind, (mode, dest) in routes.items()]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
```

In `main()`, directly after the `for k in wanted: ... print(f"  route ...")` loop, add:

```python
        write_routes(workdir, routes)
```

(`workdir` is already resolved above that point; if it is resolved later, move the call to just after it is.)

- [ ] **Step 4: Run the tests**

Run: `python job-roles/contract-admin/scripts/test_routing.py`
Expected: all existing checks still print ok, plus `write_routes + is_company_owner: ok`. (On a Mac the scratch root under `runtime\` is created relative to the repo; it is git-ignored.)

Also run: `python job-roles/contract-admin/scripts/regress_hia.py` and `python job-roles/contract-admin/scripts/regress_inclusions.py` if the staged templates are reachable (server only); on a dev clone note they were skipped.

- [ ] **Step 5: Commit**

```bash
git add job-roles/contract-admin/scripts/draft_contract.py job-roles/contract-admin/scripts/test_routing.py
git commit -m "contract-admin: driver records per-document routes to routes.txt; is_company_owner shared

The DocuSign draft step needs to know whether the build contract was a
PRODUCTION first draft, and recomputing after the save would say TEST.
Company/trust detection is factored out of owner_token so the template
pick can use the same rule. test_routing covers both."
```

---

### Task 2: `docusign_payload.py` core: template pick and recipients

**Files:**
- Create: `job-roles/contract-admin/scripts/docusign_payload.py`
- Create: `job-roles/contract-admin/scripts/test_docusign_payload.py`

**Interfaces:**
- Consumes: `draft_contract.is_company_owner`, `draft_contract.STATES`, `hia_probe.region_from_job_dir`, `hia_probe.REGION_TO_FOLDER`.
- Produces: `class PayloadStop(Exception)`; `TEMPLATES: dict[(state, variant)] -> dict(name, buyer_roles, default_roles)`; `variant_for(values) -> ("single"|"two"|"company", flags: list[str])`; `pick_template(state, values) -> (template: dict, flags)`; `recipients_for(template, values) -> (templateRoles: list[dict], sources: list[str])`. Task 3 adds subject/message/custom field and the envelope assembly on top.

- [ ] **Step 1: Write the failing test**

`test_docusign_payload.py`:

```python
r"""Self-test for docusign_payload.py (CD-10, 13 Oct 2026).

    python test_docusign_payload.py

Synthetic values only. No DocuSign call is ever made by the module under
test; this checks the template pick, recipient mapping, subject and message,
the custom field, the stop conditions and the files written.
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import docusign_payload as dp  # noqa: E402

SINGLE = {"job_no": "26099", "lot_no": "12", "suburb": "Testville NSW",
          "owner_1": "Alex EXAMPLE", "owner_email": "alex@example.com"}
TWO = dict(SINGLE, owner_2="Sam SAMPLE", owner_2_email="sam@example.com")
THREE = dict(TWO, owner_3="Jo THIRD")
COMPANY = {"job_no": "26098", "lot_no": "4", "suburb": "Pallara QLD",
           "owner_1": "EXAMPLE HOLDINGS PTY LTD ATF EXAMPLE FAMILY TRUST",
           "guarantor_name": "Casey SIGNER", "guarantor_email": "casey@example.com"}


def check_template_pick():
    t, flags = dp.pick_template("NSW", SINGLE)
    assert t["name"] == "NSW Build _ Single Buyer" and flags == [], (t, flags)
    t, flags = dp.pick_template("NSW", TWO)
    assert t["name"] == "NSW Build _ 2 Buyers" and flags == []
    t, flags = dp.pick_template("NSW", COMPANY)
    assert t["name"] == "NSW Build _ Company"
    t, flags = dp.pick_template("QLD", SINGLE)
    assert t["name"] == "QLD Build _ Single Buyer"
    t, flags = dp.pick_template("QLD", TWO)
    assert t["name"] == "QLD Build _ 2 Buyer"
    t, flags = dp.pick_template("QLD", COMPANY)
    assert t["name"] == "QLD Build _ Company"
    t, flags = dp.pick_template("NSW", THREE)
    assert t["name"] == "NSW Build _ 2 Buyers"
    assert flags and "owner_3" in flags[0], flags
    print("  template pick: ok")


def check_recipients():
    t, _ = dp.pick_template("NSW", TWO)
    roles, sources = dp.recipients_for(t, TWO)
    assert roles == [{"roleName": "Buyer 1", "name": "Alex EXAMPLE", "email": "alex@example.com"},
                     {"roleName": "Buyer 2", "name": "Sam SAMPLE", "email": "sam@example.com"}], roles
    assert sources == ["Buyer 1: owner_1 + owner_email", "Buyer 2: owner_2 + owner_2_email"], sources
    t, _ = dp.pick_template("QLD", TWO)
    roles, _ = dp.recipients_for(t, TWO)
    assert [r["roleName"] for r in roles] == ["BUYER 1", "Buyer 2"]
    t, _ = dp.pick_template("QLD", COMPANY)
    roles, sources = dp.recipients_for(t, COMPANY)
    assert roles == [{"roleName": "Buyer - Company Guarantor", "name": "Casey SIGNER",
                      "email": "casey@example.com"}], roles
    # stops
    for bad, needle in ((dict(TWO, owner_2_email=""), "owner_2_email"),
                        (dict(SINGLE, owner_email=None), "owner_email"),
                        (dict(COMPANY, guarantor_email=""), "guarantor_email"),
                        (dict(COMPANY, guarantor_name=""), "guarantor_name")):
        state = "QLD" if "guarantor_name" in bad else "NSW"
        t, _ = dp.pick_template(state, bad)
        try:
            dp.recipients_for(t, bad)
        except dp.PayloadStop as e:
            assert needle in str(e), (needle, e)
        else:
            raise AssertionError(f"no stop for missing {needle}")
    print("  recipients: ok")


if __name__ == "__main__":
    check_template_pick()
    check_recipients()
    print("docusign_payload self-test: all ok")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected: `ModuleNotFoundError: No module named 'docusign_payload'`

- [ ] **Step 3: Implement the module**

`docusign_payload.py`:

```python
r"""Build the DocuSign draft-envelope payload for a job (CD-10, 13 Oct 2026).

    python docusign_payload.py --job <workdir>/job.json --job-dir "<CONTRACT DOCUMENTATION>"
                               [--region NSW|QLD] [--server docusign-demo]

Reads the job JSON and the driver's routes.txt, picks the DocuSign template by
region x buyer type, maps the buyer-side roles, writes the subject, message and
JobNo custom field, and leaves two files in the workdir:

  docusign_envelope.json  - what Claude passes to createEnvelope (templateId
                            left empty: resolved by name through getTemplates)
  docusign_payload.txt    - the mapping with a source per recipient, the roles
                            left as template defaults, flags, and the list of
                            what staff do in DocuSign before sending

This script never calls DocuSign. The MCP calls are Claude's, per the skill's
references/docusign-draft.md, and the create call is gated by the approval
prompt. Exit codes: 0 payload written (call or no-call stated in the files),
2 a stop condition (reason in docusign_payload.txt and on stderr).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_contract as dc  # noqa: E402
import hia_probe  # noqa: E402


class PayloadStop(Exception):
    """A stop condition: nothing is created, the reason is reported."""


# Template map (spec: Rules / Template pick). Names as stored in the account,
# compared after trimming whitespace. buyer_roles are set from the job;
# default_roles are the template's own people and are never passed.
TEMPLATES = {
    ("NSW", "single"):  {"name": "NSW Build _ Single Buyer", "buyer_roles": ["Buyer"],
                         "default_roles": ["Buyer Witness", "Builder", "Builder Witness", "Date Contract"]},
    ("NSW", "two"):     {"name": "NSW Build _ 2 Buyers", "buyer_roles": ["Buyer 1", "Buyer 2"],
                         "default_roles": ["Builder", "Builder Witness", "Signer 1"]},
    ("NSW", "company"): {"name": "NSW Build _ Company", "buyer_roles": ["Buyer - Company Guarantor"],
                         "default_roles": ["Builder", "Builder Witness", "Date Contract"]},
    ("QLD", "single"):  {"name": "QLD Build _ Single Buyer", "buyer_roles": ["Buyer"],
                         "default_roles": ["Builder"]},
    ("QLD", "two"):     {"name": "QLD Build _ 2 Buyer", "buyer_roles": ["BUYER 1", "Buyer 2"],
                         "default_roles": ["Builder"]},
    ("QLD", "company"): {"name": "QLD Build _ Company", "buyer_roles": ["Buyer - Company Guarantor"],
                         "default_roles": ["Builder"]},
}

OWNER_KEYS = ("owner_1", "owner_2", "owner_3")


def _s(values, key):
    return str(values.get(key) or "").strip()


def variant_for(values):
    """('single'|'two'|'company', flags). Company wins; three or more owners
    use the 2 Buyers template with the rest flagged (as CD-3.8 fills them)."""
    owners = [_s(values, k) for k in OWNER_KEYS if _s(values, k)]
    if not owners:
        raise PayloadStop("owner_1 is empty - no buyer to address the envelope to")
    if any(dc.is_company_owner(o) for o in owners):
        return "company", []
    if len(owners) == 1:
        return "single", []
    flags = []
    if len(owners) > 2:
        flags.append(f"owner_3 and beyond ({', '.join(owners[2:])}) have no role on the "
                     f"2 Buyers template - staff add them in DocuSign before sending")
    return "two", flags


def pick_template(state, values):
    if state not in ("NSW", "QLD"):
        raise PayloadStop(f"region state {state!r} has no DocuSign template (NSW or QLD only)")
    variant, flags = variant_for(values)
    return TEMPLATES[(state, variant)], flags


def recipients_for(template, values):
    """templateRoles for the buyer-side roles, each with its source field."""
    roles, sources = [], []
    if template["buyer_roles"] == ["Buyer - Company Guarantor"]:
        name, email = _s(values, "guarantor_name"), _s(values, "guarantor_email")
        if not name:
            raise PayloadStop("guarantor_name missing - the Company template signs through the guarantor")
        if not email:
            raise PayloadStop("guarantor_email missing - no address to send the Company template to")
        roles.append({"roleName": "Buyer - Company Guarantor", "name": name, "email": email})
        sources.append("Buyer - Company Guarantor: guarantor_name + guarantor_email")
        return roles, sources
    pairs = (("owner_1", "owner_email"), ("owner_2", "owner_2_email"))
    for role, (nkey, ekey) in zip(template["buyer_roles"], pairs):
        name, email = _s(values, nkey), _s(values, ekey)
        if not name:
            continue  # single-buyer template has one role; a second owner never reaches here
        if not email:
            raise PayloadStop(f"{ekey} missing for {role} ({name}) - every buyer needs an email")
        roles.append({"roleName": role, "name": name, "email": email})
        sources.append(f"{role}: {nkey} + {ekey}")
    if not roles:
        raise PayloadStop("no buyer could be mapped")
    return roles, sources
```

(The CLI, subject, message, custom field and file writing come in Tasks 3 and 4; leave the module ending here for now.)

- [ ] **Step 4: Run the test**

Run: `python job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected:
```
  template pick: ok
  recipients: ok
docusign_payload self-test: all ok
```

- [ ] **Step 5: Commit**

```bash
git add job-roles/contract-admin/scripts/docusign_payload.py job-roles/contract-admin/scripts/test_docusign_payload.py
git commit -m "contract-admin: docusign_payload.py - template pick by region x buyer type, buyer roles from the job JSON

Six templates exist in the DocuSign account (Single Buyer / 2 Buyers /
Company per region). Buyer-side role names differ per template, so the map
carries them; internal roles are listed only so the report can say they
were left as template defaults. Missing buyer or guarantor email is a stop."
```

---

### Task 3: Subject, message, custom field and envelope assembly

**Files:**
- Modify: `job-roles/contract-admin/scripts/docusign_payload.py`
- Modify: `job-roles/contract-admin/scripts/test_docusign_payload.py`

**Interfaces:**
- Consumes: Task 2's `pick_template`, `recipients_for`.
- Produces: `subject_for(values) -> str`, `message_for(values, template) -> str`, `build_envelope(state, values, server) -> dict` returning `{"server", "templateName", "envelopeDefinition", "defaultRoles", "sources", "flags", "staffBeforeSending"}` where `envelopeDefinition` is exactly what `createEnvelope` takes (with `templateId: ""`). Task 4's CLI writes it out.

- [ ] **Step 1: Add the failing checks**

Append to the test file (and call them in `__main__`):

```python
def check_subject_and_message():
    assert dp.subject_for(TWO) == "Complete with DocuSign: BUILD CONTRACT - LOT 12, TESTVILLE"
    assert dp.subject_for(dict(SINGLE, suburb="North Kellyville")) == \
        "Complete with DocuSign: BUILD CONTRACT - LOT 12, NORTH KELLYVILLE"
    t, _ = dp.pick_template("NSW", TWO)
    assert dp.message_for(TWO, t) == ("Dear Alex & Sam,\n\n"
                                      "Please find the building contract for review and signing.\n\n"
                                      "Thank you\nSales Admin")
    t, _ = dp.pick_template("QLD", COMPANY)
    assert dp.message_for(COMPANY, t).startswith("Dear Casey,\n")
    print("  subject + message: ok")


def check_build_envelope():
    env = dp.build_envelope("NSW", TWO, "docusign-demo")
    d = env["envelopeDefinition"]
    assert d["status"] == "created"
    assert d["templateId"] == ""
    assert d["emailSubject"] == dp.subject_for(TWO)
    assert d["customFields"] == {"textCustomFields": [
        {"name": "JobNo", "value": "26099", "show": "false", "required": "false"}]}
    assert [r["roleName"] for r in d["templateRoles"]] == ["Buyer 1", "Buyer 2"]
    assert env["templateName"] == "NSW Build _ 2 Buyers"
    assert env["defaultRoles"] == ["Builder", "Builder Witness", "Signer 1"]
    assert env["server"] == "docusign-demo"
    assert any("placeholder" in s for s in env["staffBeforeSending"]), env["staffBeforeSending"]
    assert "remoteUrl" not in json.dumps(d) and '"sent"' not in json.dumps(d)
    env = dp.build_envelope("NSW", SINGLE, "docusign-demo")
    assert any("Buyer Witness" in s for s in env["staffBeforeSending"])
    try:
        dp.build_envelope("NSW", dict(TWO, job_no=""), "docusign-demo")
    except dp.PayloadStop as e:
        assert "job_no" in str(e)
    else:
        raise AssertionError("no stop for missing job_no")
    print("  build_envelope: ok")
```

- [ ] **Step 2: Run and watch it fail**

Run: `python job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected: `AttributeError: module 'docusign_payload' has no attribute 'subject_for'`

- [ ] **Step 3: Implement**

Append to `docusign_payload.py`:

```python
MESSAGE_BODY = "Please find the building contract for review and signing."
MESSAGE_SIGNOFF = "Thank you\nSales Admin"


def suburb_caps(values):
    """Suburb in capitals without the trailing state word (doc_suffix's rule)."""
    words = _s(values, "suburb").split()
    if words and words[-1].upper() in dc.STATES:
        words = words[:-1]
    return " ".join(words).upper()


def subject_for(values):
    lot, suburb = _s(values, "lot_no"), suburb_caps(values)
    if not (lot and suburb):
        raise PayloadStop(f"lot_no/suburb needed for the subject (got lot={lot!r}, suburb={suburb!r})")
    return f"Complete with DocuSign: BUILD CONTRACT - LOT {lot}, {suburb}"


def first_names(values, template):
    if template["buyer_roles"] == ["Buyer - Company Guarantor"]:
        return [_s(values, "guarantor_name").split()[0]]
    names = []
    for key in OWNER_KEYS[:len(template["buyer_roles"])]:
        n = _s(values, key)
        if n:
            names.append(n.split()[0])
    return names


def message_for(values, template):
    return f"Dear {' & '.join(first_names(values, template))},\n\n{MESSAGE_BODY}\n\n{MESSAGE_SIGNOFF}"


def staff_list(template, flags):
    items = ["Replace the template's placeholder PDFs with the job's PDFs from the job folder "
             "(build contract, inclusions, preliminary agreement where one exists, plans)."]
    if "Buyer Witness" in template["default_roles"]:
        items.append("The Buyer Witness role holds the template's default person - change or remove it.")
    items.append("Check every field and signature tab landed on the job's documents, then send.")
    return items + flags


def build_envelope(state, values, server):
    job_no = _s(values, "job_no")
    if not job_no:
        raise PayloadStop("job_no missing - the JobNo custom field is how a draft is found again")
    template, flags = pick_template(state, values)
    roles, sources = recipients_for(template, values)
    definition = {
        "status": "created",
        "templateId": "",
        "emailSubject": subject_for(values),
        "emailBlurb": message_for(values, template),
        "templateRoles": roles,
        "customFields": {"textCustomFields": [
            {"name": "JobNo", "value": job_no, "show": "false", "required": "false"}]},
    }
    return {
        "server": server,
        "templateName": template["name"],
        "envelopeDefinition": definition,
        "defaultRoles": list(template["default_roles"]),
        "sources": sources,
        "flags": flags,
        "staffBeforeSending": staff_list(template, flags),
    }
```

- [ ] **Step 4: Run the test**

Run: `python job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected: four `ok` lines and `all ok`.

- [ ] **Step 5: Commit**

```bash
git add job-roles/contract-admin/scripts/docusign_payload.py job-roles/contract-admin/scripts/test_docusign_payload.py
git commit -m "contract-admin: docusign_payload.py - subject, fixed message, JobNo custom field, envelope assembly

Subject follows the pattern the existing templates carry; the message is
fixed wording (not generated per job); status is always created and
templateId is left for Claude to resolve by name. The staff-before-sending
list is produced here so the report never has to improvise it."
```

---

### Task 4: CLI, route check and the two output files

**Files:**
- Modify: `job-roles/contract-admin/scripts/docusign_payload.py`
- Modify: `job-roles/contract-admin/scripts/test_docusign_payload.py`
- Modify: `job-roles/contract-admin/scripts/README.md` (two rows)

**Interfaces:**
- Consumes: Task 1's `routes.txt` format, `hia_probe.region_from_job_dir`, `hia_probe.REGION_TO_FOLDER`.
- Produces: `read_build_contract_route(workdir) -> "PRODUCTION"|"TEST"`, `state_for(job_dir, region) -> "NSW"|"QLD"`, `write_payload(workdir, env, call) -> (json_path, txt_path)`, `main(argv) -> int`. `docusign_envelope.json` carries a top-level `"call": true|false` plus everything from `build_envelope`. The reference (Task 5) reads these.

- [ ] **Step 1: Add the failing checks**

```python
def check_cli_files():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        (wd / "job.json").write_text(json.dumps(TWO), encoding="utf-8")
        (wd / "routes.txt").write_text("INCLUSIONS\tTEST\tZ:\\t\nBUILD CONTRACT\tPRODUCTION\tZ:\\p\n",
                                       encoding="utf-8")
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "NSW", "--server", "docusign-demo"])
        assert rc == 0, rc
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["call"] is True and env["templateName"] == "NSW Build _ 2 Buyers"
        txt = (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        assert "CALL: yes" in txt and "Buyer 1: owner_1 + owner_email" in txt and "Signer 1" in txt
        # TEST route -> files written, no call
        (wd / "routes.txt").write_text("BUILD CONTRACT\tTEST\tZ:\\t\n", encoding="utf-8")
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "QLD"])
        assert rc == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["call"] is False and env["server"] == "docusign-demo"
        assert "CALL: no" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        # no routes.txt -> stop
        (wd / "routes.txt").unlink()
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "QLD"])
        assert rc == 2
        assert "routes.txt" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        # region from a job dir path
        assert dp.state_for(r"Z:\PROJECTS\SEQ\26098 LOT 4\CONTRACT\CONTRACT DOCUMENTATION", None) == "QLD"
        assert dp.state_for(r"Z:\PROJECTS\SYDNEY\26099\CONTRACT\CONTRACT DOCUMENTATION", None) == "NSW"
        try:
            dp.state_for(r"Z:\PROJECTS\NOWHERE\x", None)
        except dp.PayloadStop:
            pass
        else:
            raise AssertionError("unknown region did not stop")
    print("  cli + files: ok")
```

Note: `hia_probe.region_from_job_dir` splits on `Path.parts`; on macOS a Windows path is one part, so for the dev-clone run of this check split the path on backslashes first inside `state_for` (shown below).

- [ ] **Step 2: Run and watch it fail**

Run: `python job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected: `AttributeError: ... no attribute 'main'`

- [ ] **Step 3: Implement**

Append to `docusign_payload.py`:

```python
def state_for(job_dir, region):
    """'NSW' or 'QLD' from --region, else from the job folder's region segment."""
    if region:
        return region.upper()
    parts = [p.upper() for p in str(job_dir or "").replace("\\", "/").split("/") if p]
    if "PROJECTS" in parts:
        idx = parts.index("PROJECTS")
        if idx + 1 < len(parts) and parts[idx + 1] in hia_probe.REGION_TO_FOLDER:
            return hia_probe.REGION_TO_FOLDER[parts[idx + 1]][0]
    raise PayloadStop(f"region not recognised from {job_dir!r} - pass --region NSW|QLD")


def read_build_contract_route(workdir):
    path = Path(workdir) / "routes.txt"
    if not path.is_file():
        raise PayloadStop("routes.txt not in the workdir - run draft_contract.py --job-dir first "
                          "(the route decides whether a draft is created)")
    for line in path.read_text(encoding="utf-8").splitlines():
        kind, _, rest = line.partition("\t")
        if kind == "BUILD CONTRACT":
            return rest.split("\t")[0]
    raise PayloadStop("routes.txt has no BUILD CONTRACT line - no build contract was routed, "
                      "so there is nothing to put in DocuSign")


def write_payload(workdir, env, call, stop=None):
    workdir = Path(workdir)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if stop:
        txt = f"DOCUSIGN DRAFT - STOPPED ({stamp})\nCALL: no\nREASON: {stop}\n"
        (workdir / "docusign_payload.txt").write_text(txt, encoding="utf-8")
        return None, workdir / "docusign_payload.txt"
    env = dict(env, call=call, generated=stamp)
    jpath = workdir / "docusign_envelope.json"
    jpath.write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    d = env["envelopeDefinition"]
    lines = [f"DOCUSIGN DRAFT PAYLOAD ({stamp})",
             f"CALL: {'yes' if call else 'no'}"
             + ("" if call else "  (build contract routed TEST - payload for inspection only)"),
             f"server        : {env['server']}",
             f"template      : {env['templateName']}  (resolve id by exact trimmed name)",
             f"status        : {d['status']}",
             f"subject       : {d['emailSubject']}",
             "message       :", *("    " + l for l in d["emailBlurb"].splitlines()),
             "recipients set:", *(f"    {s}" for s in env["sources"]),
             "template defaults left as they are: " + ", ".join(env["defaultRoles"]),
             f"custom field  : JobNo={d['customFields']['textCustomFields'][0]['value']}"]
    if env["flags"]:
        lines += ["flags:", *(f"    {f}" for f in env["flags"])]
    lines += ["staff before sending:", *(f"    - {s}" for s in env["staffBeforeSending"])]
    tpath = workdir / "docusign_payload.txt"
    tpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jpath, tpath


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job", required=True, help="job JSON (its folder is the workdir)")
    ap.add_argument("--job-dir", help="the job's CONTRACT DOCUMENTATION folder (region comes from it)")
    ap.add_argument("--region", help="NSW or QLD, when --job-dir is not given")
    ap.add_argument("--server", default="docusign-demo",
                    help="MCP server name the draft will be created on (docusign-demo = sandbox)")
    args = ap.parse_args(argv)
    job = Path(args.job)
    workdir = job.parent
    try:
        values = json.loads(job.read_text(encoding="utf-8"))
        route = read_build_contract_route(workdir)
        state = state_for(args.job_dir, args.region)
        env = build_envelope(state, values, args.server)
    except PayloadStop as e:
        write_payload(workdir, None, False, stop=str(e))
        print(f"DOCUSIGN DRAFT STOPPED: {e}", file=sys.stderr)
        return 2
    call = route == "PRODUCTION"
    jpath, tpath = write_payload(workdir, env, call)
    print(tpath.read_text(encoding="utf-8"))
    print(f"written: {jpath.name}, {tpath.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test**

Run: `python job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected: five `ok` lines and `all ok`. Then run the CLI help once: `python job-roles/contract-admin/scripts/docusign_payload.py --help` prints the docstring.

- [ ] **Step 5: README rows**

In `job-roles/contract-admin/scripts/README.md`, add to the table (same style as the neighbours):

```markdown
| `docusign_payload.py` | **Working — no network** | Job JSON + the driver's `routes.txt` → `docusign_envelope.json` (the exact `createEnvelope` payload, `status: created`, template named not id'd) + `docusign_payload.txt` (recipient sources, template defaults left alone, flags, what staff do in DocuSign before sending). Template by region × buyer type (`CD-10`). Stops on a missing buyer/guarantor email or an unrecognised region; a TEST-routed build contract gets the files and `CALL: no`. The MCP calls themselves are Claude's, per the skill's `references/docusign-draft.md`. |
| `test_docusign_payload.py` | **Passing** | Synthetic self-test: all six template picks, three-owner flag, missing-email and missing-guarantor stops, subject/message text, `JobNo` custom field, TEST route → files but no call, region from the job-folder path. Temp workdir, no client data. |
```

- [ ] **Step 6: Commit**

```bash
git add job-roles/contract-admin/scripts/docusign_payload.py job-roles/contract-admin/scripts/test_docusign_payload.py job-roles/contract-admin/scripts/README.md
git commit -m "contract-admin: docusign_payload.py CLI - reads routes.txt, writes the envelope payload and mapping report

A PRODUCTION build-contract route marks the payload call: yes; TEST writes
the same files for inspection with call: no; a missing routes.txt or an
unrecognised region is a stop. README rows added."
```

---

### Task 5: The MCP procedure reference and the skill's step 8

**Files:**
- Create: `.claude/skills/new-contract-template/references/docusign-draft.md`
- Modify: `.claude/skills/new-contract-template/SKILL.md` (front-matter description; step 7 at ~line 551; insert step 8 before `## Auxiliary and dual-key dwellings` at ~line 594; Safety rules "Outward acts stay human" paragraph at ~line 619)

**Interfaces:**
- Consumes: `docusign_envelope.json` layout from Task 4 (`call`, `server`, `templateName`, `envelopeDefinition`, `defaultRoles`, `sources`, `flags`, `staffBeforeSending`); `docusign_payload.txt`.
- Produces: `docusign_result.json` written by Claude (fields below), referenced by Task 6's docs.

- [ ] **Step 1: Write the reference**

`references/docusign-draft.md` (outer fence is four backticks because the content has fences of its own):

````markdown
# DocuSign draft within the new contract workflow (step 8)

Use this reference after step 7's report, and only when
`docusign_payload.txt` says `CALL: yes` (the build contract routed PRODUCTION
in step 5). The envelope is a **draft** (`status: created`). Sending, document
replacement, witness/date roles and voiding are a person's acts in the DocuSign
web UI. The `docusign-demo` server is the **sandbox**: its envelopes have no
legal effect, and the report must say SANDBOX. A production server, when one is
registered, is named `docusign` (see `docs/mcp-servers.md`).

**The approval prompt on `createEnvelope` is the human yes.** Do not ask a
second time in chat; do not proceed past a decline. Every other call below is
read-only.

## 1. Build the payload

```
python job-roles/contract-admin/scripts/docusign_payload.py --job <workdir>/job.json --job-dir "<job's CONTRACT DOCUMENTATION>"
```

Exit 2 = a stop condition; put its `REASON:` line in the report and finish.
`CALL: no` = a template-testing refresh; mention the payload files and finish.
Otherwise read `docusign_envelope.json`: `templateName`, `envelopeDefinition`.

## 2. Account and template (read-only)

1. `getUserInfo` → `accounts[0].account_id` (the `accountId` for every later
   call) and the `mcpSessionId` to pass along. A failure is stop 1: "DocuSign
   not connected or not signed in - open `/mcp`, select the server, sign in".
2. `getTemplates(accountId, search_text=<templateName>, user_filter="all")`.
   Keep the templates whose `name.strip()` equals `templateName.strip()`.
   Exactly one → its `templateId`. Zero or more than one is stop 2: report
   the names returned and finish.

## 3. Duplicate check (read-only)

`getEnvelopes(accountId, custom_field="JobNo=<job_no>", from_date=<today minus 180 days, YYYY-MM-DD>, count=40)`.
(The tool's own description asks for `getEnvelopeVsAgreementSkill` first; call
it, it only returns guidance.) An envelope whose status is anything other than
`voided` or `declined` is stop 4: report its `envelopeId` and `status` as the
existing draft, and finish. Nothing found → continue.

## 4. Create the draft (gated)

`createEnvelope(accountId, envelopeDefinition=<envelopeDefinition from the
JSON with templateId set>)`. Pass the definition exactly: `status` stays
`created`; do not add `documents`, `remoteUrl`, `compositeTemplates` or any
role not in `templateRoles`. The prompt appears here; a decline is stop 5,
reported as "not created, declined" (a normal outcome).

The response carries `envelopeId`, `status` (`created`) and `uri`.

## 5. Record and report

Write `<workdir>/docusign_result.json`:

```json
{"server": "docusign-demo", "envelopeId": "...", "status": "created",
 "templateId": "...", "templateName": "...", "jobNo": "...",
 "created": "<ISO timestamp>", "stop": null}
```

On a stop, the same file with `envelopeId: null` and `stop: "<reason>"`.

Report lines (added to the step 7 table): server (SANDBOX/PRODUCTION),
template, recipients set with their sources (`sources` from the JSON), roles
left as template defaults (`defaultRoles`), the envelope id, and the
`staffBeforeSending` list verbatim, headed "Before sending, in DocuSign:".
Say plainly that the draft holds the template's placeholder PDFs until staff
replace them.

## Never

`status: sent`; `updateEnvelope` to send or change status; `remoteUrl`
documents; setting Builder, Builder Witness, Date Contract, Signer 1 or Buyer
Witness; voiding; `createEnvelopeFromTemplate` (it sends and cannot be held at
draft); a second create for the same job in one run.
````

- [ ] **Step 2: Skill edits**

Front-matter `description`: change the last sentence `Never sends, signs, or issues anything.` to `Creates a DocuSign draft envelope (never sent) after a real build contract saves; never sends, signs, or issues anything.`

Step 7: after the sentence ending `the reader checks them in their own time.` add:

```markdown
When the build contract routed PRODUCTION, the report also carries the step 8
lines (server, template, recipients and sources, template-default roles,
envelope id, and the "Before sending, in DocuSign" list) once step 8 has run.
```

Insert before `## Auxiliary and dual-key dwellings`:

```markdown
### 8. DocuSign draft — only after a PRODUCTION build-contract save

Follow [DocuSign draft](references/docusign-draft.md). In one line: build the
payload with `docusign_payload.py` (it reads the driver's `routes.txt`; a
TEST-routed build contract yields the files and no call), resolve the
template by exact name, check no envelope already carries this `JobNo`, then
`createEnvelope` with `status: created` — the approval prompt on that call is
the person's yes, and a decline ends the step as a normal outcome. The draft
holds the template's placeholder PDFs until staff replace them with the job's
PDFs in DocuSign; the report says so every time, with the staff list the
script produced. Sandbox (`docusign-demo`) drafts have no legal effect — name
the server in the report. Rules: CD-10.
```

Safety rules, replace `Never send email, never issue to DocuSign, never sign or
initial anything, and never write to DataBuild.` with:

```markdown
Never send email, never send or issue a DocuSign envelope, never sign or
initial anything, and never write to DataBuild. The one DocuSign write the
run makes is a `created` draft through the gated `createEnvelope` call
(step 8, CD-10) — approved at the prompt, per call; it is not an issue and
not covered by the automatic document-save exception.
```

- [ ] **Step 3: Check the links resolve**

Run: `ls .claude/skills/new-contract-template/references/docusign-draft.md && grep -n 'docusign-draft.md' .claude/skills/new-contract-template/SKILL.md`
Expected: the file exists and the skill links it once in step 8.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/new-contract-template/references/docusign-draft.md .claude/skills/new-contract-template/SKILL.md
git commit -m "new-contract-template: step 8 - DocuSign draft envelope after a PRODUCTION build-contract save

Reference in the OSC intake's style: payload script, three read-only calls
(getUserInfo, getTemplates by trimmed name, getEnvelopes by JobNo custom
field), one gated createEnvelope with status created. The prompt is the
approval; sending, document replacement and voiding stay in the DocuSign UI."
```

---

### Task 6: Rules, workflow, CLAUDE.md files, MCP doc and permissions

**Files:**
- Modify: `job-roles/contract-admin/rules/contract-docs.md` (insert `## CD-10` after the CD-9 block, before `## CD-8 What only a person does` at ~line 502; edit CD-8's last clause)
- Modify: `job-roles/contract-admin/workflows/new-contract.md` (Phase 1 table after row 7; HITL gates paragraph; Outputs; Relies on)
- Modify: `job-roles/contract-admin/CLAUDE.md` (Human-in-the-loop, after the 17 Aug exception paragraph)
- Modify: `CLAUDE.md` (Human-in-the-loop, after the 10 Sep 2026 exception bullet)
- Modify: `docs/mcp-servers.md` (Human-in-the-loop subsection under DocuSign; "How job-roles use it")
- Modify: `.claude/settings.json` (`permissions.allow`)

- [ ] **Step 1: CD-10 block**

Insert before `## CD-8 What only a person does`:

```markdown
## CD-10 DocuSign draft envelope (instruction, 13 Oct 2026)

- **CD-10.1** After a run whose build contract routed PRODUCTION (CD-7.7),
  the skill creates a DocuSign envelope with `status: created` — a draft. It
  never sends. The approval prompt on the `createEnvelope` call is the
  person's yes, per call; a decline ends the step. A template-testing refresh
  produces the payload files only.
- **CD-10.2** Template by region × buyer type, matched by exact name after
  trimming whitespace, never by a stored id: NSW/QLD × Single Buyer (one
  owner), 2 Buyers (two or more; owner 3+ flagged, as CD-3.8), Company (a
  company or trust owner, the CD-3.9 condition). Zero or several matches
  stop the step.
- **CD-10.3** Only buyer-side roles are set: owner 1/2 names with
  `owner_email`/`owner_2_email`; on the Company template the guarantor
  (`guarantor_name`, `guarantor_email`). Builder, Builder Witness, Date
  Contract, Signer 1 and Buyer Witness keep the template defaults and are
  listed in the report; Buyer Witness is a staff change before sending. A
  missing buyer or guarantor email stops the step.
- **CD-10.4** Subject `Complete with DocuSign: BUILD CONTRACT - LOT <lot>,
  <SUBURB>`; message fixed (`Dear <first names>,` / `Please find the building
  contract for review and signing.` / `Thank you` / `Sales Admin`); custom
  field `JobNo` = job number, used to find an existing envelope before
  creating another.
- **CD-10.5** Documents are not attached by the run: the MCP accepts only a
  public URL, and client PDFs are never published. The draft carries the
  template's placeholder PDFs until staff replace them in DocuSign with the
  job's PDFs from the job folder. The report says so every time.
- **CD-10.6** Evidence in the workdir only: `docusign_envelope.json`,
  `docusign_payload.txt`, `docusign_result.json`. Nothing from this step goes
  into the job folder.
- **CD-10.7** The sandbox server (`docusign-demo`) is named SANDBOX in the
  report; its drafts have no legal effect. Production needs its own server
  registration first (`docs/mcp-servers.md`).
```

In CD-8, change `and any DocuSign issue to a client.` to `replacing the placeholder PDFs in the DocuSign draft, and sending it (CD-10).`

- [ ] **Step 2: Workflow doc**

Phase 1 table, add after row 7:

```markdown
| 8 | **DocuSign draft** — only when the build contract routed PRODUCTION: `docusign_payload.py` builds the envelope (template by region × buyer type, buyers from the job, subject/message, `JobNo` custom field), Claude resolves the template by name, checks for an existing `JobNo` envelope, and calls `createEnvelope` with `status: created`; the approval prompt is the gate. Draft holds placeholder PDFs until staff replace them in DocuSign | Claude (via `docusign-demo` MCP) | CD-10 |
```

HITL gates: in the sentence beginning `What stays with a person, permanently: every outward-facing act — email, signature, DocuSign —` change `DocuSign` to `sending a DocuSign envelope (the run creates only a draft, behind the approval prompt on the create call, CD-10)`.

Outputs: add `- DocuSign draft envelope (sandbox while \`docusign-demo\` is the server), with \`docusign_envelope.json\` / \`docusign_payload.txt\` / \`docusign_result.json\` in the evidence bundle (CD-10)`.

Relies on: add `- [\`../scripts/docusign_payload.py\`](../scripts/docusign_payload.py) — envelope payload (\`test_docusign_payload.py\` guards it)` and `- [DocuSign draft reference](../../../.claude/skills/new-contract-template/references/docusign-draft.md) — the MCP procedure`.

- [ ] **Step 3: CLAUDE.md paragraphs**

Role `CLAUDE.md`, after the 17 Aug exception paragraph:

```markdown
**DocuSign draft (13 Oct 2026):** after a build contract saves into the job
folder, `/new-contract-template` creates a DocuSign envelope with
`status: created` — a draft, never sent — through the gated `createEnvelope`
call; the approval prompt on that call is the person's yes, per call. This is
a gated external write, not an extension of the automatic save. Replacing the
template's placeholder PDFs, fixing witness/date roles and sending stay human
(CD-10).
```

Root `CLAUDE.md`, a new bullet after the 10 Sep 2026 exception:

```markdown
- **Gated write, not an exception (13 Oct 2026):** `/new-contract-template`
  step 8 creates a DocuSign **draft** envelope (`status: created`) after a
  real build-contract save. The create call sits under `ask` in
  `.claude/settings.json`, so the prompt is the human approval, per call.
  Sending stays human. Read-only DocuSign calls the step needs (`getUserInfo`,
  `getTemplates`, `getEnvelopes`, `getEnvelopeVsAgreementSkill`) are on
  `allow`.
```

- [ ] **Step 4: `docs/mcp-servers.md`**

In the DocuSign Human-in-the-loop subsection, replace the paragraph starting `Every DocuSign tool call therefore prompts for approval, including read-only ones.` with:

```markdown
Every DocuSign write prompts for approval. Since 13 Oct 2026 four read-only
tools are on `allow` so the contract workflow's draft step prompts once, on
the create call: `getUserInfo`, `getTemplates`, `getEnvelopes`,
`getEnvelopeVsAgreementSkill`. Everything else on the server, `createEnvelope`
included, stays on `ask`. Do not widen this further without the same review.
```

In "How job-roles use it", Contract Administration bullet, add: `and, since 13 Oct 2026, the draft envelope step 8 of /new-contract-template (status created, never sent; CD-10)`.

- [ ] **Step 5: settings.json**

Add to `permissions.allow` (keep the `mcp__docusign-demo` entry in `ask`; a specific allow beats the server-wide ask for these names):

```json
"mcp__docusign-demo__getUserInfo",
"mcp__docusign-demo__getTemplates",
"mcp__docusign-demo__getEnvelopes",
"mcp__docusign-demo__getEnvelopeVsAgreementSkill",
```

Run: `python -c "import json; json.load(open('.claude/settings.json')); print('settings.json ok')"`
Expected: `settings.json ok`

Then verify the precedence in a fresh session in the repo folder: call
`getUserInfo` on `docusign-demo`. Expected: no prompt. If it still prompts,
the server-wide `"mcp__docusign-demo"` entry in `ask` is winning over the
specific allows; remove that entry (an MCP tool with no rule prompts by
default, so the posture is unchanged for every write tool) and change the
`docs/mcp-servers.md` sentence from "stays on `ask`" to "prompts by default
(no rule)". Record which of the two applied in the commit message.

- [ ] **Step 6: Commit**

```bash
git add job-roles/contract-admin/rules/contract-docs.md job-roles/contract-admin/workflows/new-contract.md job-roles/contract-admin/CLAUDE.md CLAUDE.md docs/mcp-servers.md .claude/settings.json
git commit -m "contract-admin: CD-10 DocuSign draft rules; workflow, CLAUDE.md, MCP doc and permissions follow

Draft creation is a gated external write (prompt per call), not an
extension of the automatic save. Four read-only DocuSign tools go to allow
so the step prompts once, on createEnvelope."
```

---

### Task 7: Sandbox end-to-end with a synthetic job, then the PR

**Files:**
- No repo changes except the plan checkboxes; the run's files live under `runtime\contract-admin\outputs\_docusign-selftest\` (git-ignored).

**Interfaces:**
- Consumes: everything above; the `docusign-demo` MCP signed in.

- [ ] **Step 1: Synthetic workdir**

Create `runtime/contract-admin/outputs/_docusign-selftest/job.json` with synthetic values (two owners, emails at `example.com`, `job_no` `00000`, `lot_no` `1`, `suburb` `Testville NSW`) and `routes.txt` containing `BUILD CONTRACT\tPRODUCTION\tZ:\x`. Run:

```
python job-roles/contract-admin/scripts/docusign_payload.py --job runtime/contract-admin/outputs/_docusign-selftest/job.json --region NSW
```

Expected: `CALL: yes`, template `NSW Build _ 2 Buyers`.

- [ ] **Step 2: Follow the reference by hand in a Claude session**

`getUserInfo` → `getTemplates(search_text="NSW Build _ 2 Buyers")` → exactly one match → `getEnvelopes(custom_field="JobNo=00000", from_date=<180 days ago>)` → none → `createEnvelope` with the JSON's definition plus the resolved `templateId`. Approve at the prompt.

Expected: response `status: "created"`, an `envelopeId`. Write `docusign_result.json` as the reference says.

- [ ] **Step 3: Verify, then clean up**

`getEnvelopes(custom_field="JobNo=00000", from_date=<today>)` returns the draft with `status: created` and the two buyer recipients. Then void or delete the draft in the DocuSign web UI (sandbox). Record in the PR body: role names accepted, draft held at `created`, custom field searchable, draft voided.

If a role name is rejected, fix the `TEMPLATES` map in `docusign_payload.py` and the spec, add the exact name to `test_docusign_payload.py`, and re-run from Step 1.

- [ ] **Step 4: Full test pass**

```
python job-roles/contract-admin/scripts/test_docusign_payload.py
python job-roles/contract-admin/scripts/test_routing.py
```

Expected: both `all ok`.

- [ ] **Step 5: Push and open the PR (do not merge)**

```bash
git push -u origin docusign-integration
```

Then open a PR against `main` titled `contract-admin: DocuSign draft envelope after a PRODUCTION build-contract save (CD-10)` whose body links the spec and this plan, lists the six templates by name, states what the step never does, and gives the sandbox verification from Step 3. No AI attribution footer. Leave the PR open for the reviewer.
