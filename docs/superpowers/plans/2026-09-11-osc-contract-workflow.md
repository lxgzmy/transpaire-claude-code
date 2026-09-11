# OSC contract workflow implementation plan

**Goal:** Integrate the OSC steps in issue #34's Word attachment into the existing
`/new-contract-template` workflow. DataBuild is excluded by the user's instruction.

**Architecture:** The skill orchestrates existing OSC MCP reads and approved writes,
then hands the verified job identity to the existing folder and document pipeline.
Extend endpoint introspection to expose payload schemas and add multipart uploads
for the request email. Do not build a second HTTP client or a new intake skill.

**Tech stack:** Python 3.11+, FastMCP, httpx, unittest, Markdown workflow instructions.

**Source:** Issue #34, `1.docx` (items 1–9, including screenshots), current OSC v7.3
OpenAPI schemas, `JD-*` and `CD-*` rules. The user approved integration on
11 September 2026 and excluded DataBuild. No live business writes are authorised
by this development task.

## Constraints and decisions

- Work on branch `issue-34-osc-contract-workflow` in the requested current repo.
- Preserve the Windows registration and `.env`; never commit credentials or data.
- Preserve disabled-by-default writes, per-call approval and explicit confirmation.
- Do not write contract values to OSC, complete DataBuild activity 6, or wait for
  DataBuild before contacts/documents. Do not change document pricing rules.
- Document unavailable API capabilities as manual fields, not invented payloads.
- No automatic retry of uncertain creates. Reconcile current state before resuming.

## Tasks

- [x] Extend `osc_describe_endpoint` with request/response schema references and
  complete parameter metadata. Add failing synthetic tests for nested references,
  missing references, cycles, multipart bodies and required fields; implement and
  run `python -m unittest discover -s tests -v` in `shared/mcp/osc-api`.
- [x] Add form/file arguments to `osc_write` and multipart transport in the client.
  Test actual encoded requests with `httpx.MockTransport`; prove disabled and
  unconfirmed requests never read files or send. Reject mixed JSON/form inputs,
  unavailable files and unsupported multipart routes before sending business writes.
- [x] Add `references/osc-new-contract.md` to the existing skill with item-by-item
  field mapping, exact endpoint paths, lookup resolution, approval/read-back,
  checkpoints, duplicate handling and document handoff. Update the skill, workflow,
  role/root instructions and indexes so no active rule prohibits the integration.
- [x] Run skill acceptance scenarios against new/existing jobs, missing lookup
  values, disabled writes, activity 6, multipart email, partial failures and
  unchanged document routing. Obtain independent code and workflow review.
- [x] Verify local MCP handshake, schema discovery and read-only lookup calls;
  run synthetic tests and diff checks. Delivery is by branch commit and open PR;
  merging remains human.

## Investigation evidence

The old skill prohibits OSC writes and stops when a job folder does not exist.
The MCP description returns only content types, not fields. Message attachments
require multipart binary files, while the client currently sends JSON only.
The live schema supports Jobs, Clients, Persons, activity completion/questions,
messages, and custom-field writes. Runtime lookup availability and automatic
contract-number generation need explicit checks; optional `contractNumber` in
OpenAPI alone is not proof of automatic generation.

## Verification record

- 11 synthetic tests pass, including nested schema references, method filtering,
  multipart bytes, disabled/unconfirmed writes, unreadable files and uncertain
  transport outcomes with closed file streams.
- Fresh local MCP handshake exposes `form`/`files`; authentication and
  `/api/versions` read passed. Job, client, person and activity-message schema
  descriptions returned complete local references.
- Live lookup reads confirmed the required initial template and custom-field
  labels. No business write or file upload was sent; `.env` and registration
  are unchanged.
- Independent code/workflow review found no blocking issues. Its HTTP 415
  guidance finding was fixed and regression-tested. Relative Markdown links
  and `git diff --check` pass.
- Live create/update/upload business acceptance remains a runtime check with an
  approved test job. Client Notes has no writable mapping in the checked API;
  the workflow reports it for manual entry. Contract-number generation must be
  confirmed by read-back, with a manual fallback on the same created job.
