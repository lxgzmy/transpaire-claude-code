---
name: ca-new-job
description: >
  Run the Contract-Admin new-job intake workflow end to end from an EOI /
  contract request email file. Use when the user invokes /ca-new-job with an
  email file path, or asks to process a new job / EOI / contract request into
  OnSite Companion. Reads the email, runs the extraction script, resolves the
  verification flags with web-lookup evidence, presents the draft sheets for
  human review, dry-runs the OSC entry narration, and drafts the DataBuild
  email. Draft-only: never writes to OSC or sends email itself.
---

# Contract-Admin: New Job intake (EOI → OSC draft sheets)

Orchestrates `job-roles/contract-admin/workflows/new-job.md` Phase 1. The
argument is the path to the request-email file (`.txt`, `.md`, or pasted body).
Authoritative field rules: `job-roles/contract-admin/rules/job-details.md`
(`JD-*`). **You draft and verify; a human performs every OSC/DataBuild write
and sends every email.**

## Steps

1. **Read the email file** the user pointed at. If it is an Outlook `.msg`,
   convert it first (needs `pip install extract-msg` once per machine):

   ```
   python job-roles/contract-admin/scripts/msg_to_text.py "<file.msg>" -o <workdir>/email.txt
   ```

   Real request emails are **forwarded chains** (sales manager → contract
   admin, forwarded marketer email, e-sign notifications) — read the whole
   chain, not just the top message. Confirm it is a new-job request; if the
   client ID is not mentioned as attached, note it (JD-0.1).

2. **Duplicate-check reminder (JD-0.2).** Tell the user the lot number and
   estate, and that OSC must be searched for an existing job before creation.
   Do not continue past extraction until they confirm.

3. **Run the extractor** (from the repo root):

   ```
   python job-roles/contract-admin/scripts/extract_eoi.py <email-file> -o <workdir>/job.json
   ```

   `<workdir>`: on the server use
   `Z:\CLAUDE CODE\transpaire-claude-code\runtime\contract-admin\outputs\<job>\`;
   on a dev machine use the session scratchpad. Never commit `job.json`.

4. **Read `job.json`.** If any field the email clearly contains came out
   null, extract it yourself from the email text, correct `job.json`, and say
   so — then add the missed pattern to `scripts/extract_eoi.py` later (flag it).

5. **Resolve every verification flag with evidence:**
   - Postcode: web-search "<suburb> <state> postcode" (JD-2.6).
   - Council: web-search "<suburb> <state> Local Council" (JD-3.7); if two
     councils are plausible, say so and point to the Estimate-folder check.
   - Insert the verified postcode into `postcode` and `job_name` in
     `job.json`. Record the source URLs — they go in the evidence bundle.

6. **Present the draft sheets** (job creation, job details, contacts) as
   tables citing the `JD-*` rule per value, plus all remaining flags.
   **HITL GATE: ask the human to approve or correct before going on.**

7. **Dry-run the entry narration:**

   ```
   python job-roles/contract-admin/scripts/osc_entry.py <workdir>/job.json
   ```

   Show the output — this is the exact step list the human follows in OSC
   (live pywinauto entry stays blocked until control IDs are mapped; see
   `scripts/README.md`).

8. **Draft the DataBuild email** (JD-6.1) through the `transpaire-writing`
   skill: full project name + contract price, addressed to the DataBuild
   administrator. Present as a draft — the human sends it.

9. **Write the evidence bundle** to `<workdir>`: the final `job.json`, the
   lookup sources, the dry-run narration, and the email draft. Summarise
   what the human still has to do: OSC search + entry, send DataBuild email,
   price check on confirmation (JD-6.2), then wait for the PLAN (JD-8).

## Hard rules

- Never run `osc_entry.py --live`.
- Never send email; never write to OSC/DataBuild.
- Never guess postcode, council, or garage side — verify or escalate.
- Real client emails and `job.json` outputs never go into git.
