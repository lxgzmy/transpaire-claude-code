---
name: osc-api
description: >
  Query and (with a person's confirmed yes) update the production OnSite
  Companion via the osc-api-prod MCP server, using the preloaded endpoint
  reference instead of runtime discovery. Use whenever a task touches OSC data - jobs, job activities,
  clients, contacts, variations, defects, inspections, documents, alerts -
  e.g. "list recent jobs in OSC", "activities for job 26055", "find client X".
---

# OSC API (OnSite Companion)

Fast-path knowledge for the **`osc-api-prod` MCP server** (see
`docs/mcp-servers.md` and `shared/mcp/osc-api/README.md`). It connects to the
**production** OnSite Companion, the one staff use (owner approval, 13 Oct
2026). The old `osc-api` server pointed at a dev copy frozen on 21 Aug 2026;
writes there never reached staff, and it is retired. This skill supplies what
the tools would otherwise have to discover at run time (endpoints, field
names, the query patterns that work), so a request costs one or two calls
instead of six to ten.

**Never put a hostname, address, or credential in this skill or anywhere in
the repo, and never paste one into a chat.** All of that lives in `OSC_*`
settings in the git-ignored `production.env` beside `shared/mcp/osc-api/`,
which Claude cannot read. The endpoint reference here is generated with that
guardrail enforced.

## Prerequisites

- The `osc-api-prod` MCP server is registered at **project scope** by the
  repo's committed `.mcp.json`, so every session opened in the repo folder has
  its tools. Read tools, allowed without a prompt: `osc_token_info`,
  `osc_list_endpoints`, `osc_describe_endpoint`, `osc_get`, plus
  `osc_prepare_write`, `osc_prepare_changes` and `osc_cancel_write`, which
  send nothing. The one
  tool that changes OSC is `osc_confirm_write`, on `ask`. If the tools are
  missing, the session was opened outside the repo folder or predates a pull:
  ask the user to start a new session in `Z:\CLAUDE CODE\transpire-claude-code`.
- **Pre-flight, first call of any OSC task: `osc_token_info`.** Check
  `config.environment` is `production` and `live_check.live` is true. A false
  `live_check` means the connection is answering from a stale copy (newest job
  older than 30 days): stop, say so in one line, write nothing.
- The **write switch** `OSC_ENABLE_WRITES` is set in the `.mcp.json` `env`
  block and beats `production.env`. The server is a child of the session,
  started fresh each time, so a session showing `enable_writes: false` while
  `.mcp.json` says true simply predates the change; a new session is the whole
  fix. `osc_token_info` shows `enable_writes_source` (`env` = `.mcp.json`,
  `dotenv` = `production.env`, `default` = unset). Changing the switch is a PR
  to `.mcp.json`, never a run-time edit.
- Every response is **live client data** under the org guardrails: fine to
  show the user, never written to the repo, `C:`, or Dropbox.

## Changing OSC: prepare, confirm, read back

There is no direct write tool. Every change goes through the gate in
`shared/mcp/osc-api/osc_mcp/gate.py`:

1. **`osc_prepare_write(method, path, job_id, body | form+files)`** sends
   nothing. It refuses anything that is not one of the 14 contract-intake
   changes (create/update client, person, client and job contact links, job;
   complete an activity; answer an activity question; job or activity
   message), any record not tied to `job_id` (the job the person is working
   on), an ambiguous or missing target, an unknown field, or a protected one
   (contract price, contract number, region on an existing job, DataBuild
   client code). It reads the current values, keeps only the fields that
   really change, and returns `confirmation_text`: the job, each change as
   *now X, will be Y* (clears and overwrites spelled out), notes when a client
   or person is shared with other jobs, and duplicate warnings.
2. **Show `confirmation_text` to the person exactly as written** and wait.
   Do not summarise it, merge it with other text, or answer for them.
3. **`osc_confirm_write(confirmation_code, user_reply)`** with their reply
   verbatim. Only a plain yes sends; "no" cancels; anything else ("yes but…")
   sends nothing, so prepare the changed request and show its new
   confirmation. The gate reads OSC again first: if the record or the request
   changed since the person confirmed, it sends nothing and returns a new
   confirmation to show them. A code is used once, is replaced by a newer
   check of the same target, and expires after 30 minutes.
4. The result's `result_text` says what happened after reading the record
   back: done, or exactly which fields did not take or changed unexpectedly.
   Relay it. `sent_unverified` means look in OSC before anything else.

**Several changes to one job: `osc_prepare_changes(job_id, changes)`.** Each
change gets exactly the checks above; the person reads one confirmation for
all of them and one plain yes sends them in order, each read back. Anything
OSC already holds is left out and listed; any change that cannot go ahead
blocks the lot. Each change after the first is checked again just before it
goes, and the batch stops at the first one that fails or no longer matches
(`state: stopped` comes with a new confirmation for the rest). A later change
can use an ID an earlier one creates: `{{N.clientID}}` for a new job's
client, `{{N.personID}}` in a contact-link path. `job_id` is empty only for a
batch that creates the client, people and job of a new intake. The contract
intake uses one batch per stage (the `new-contract-template` skill, step 1a).

Never describe a change as made unless `osc_confirm_write` returned
`state: verified`. A person who says no, does not answer, or asks for
something else gets no change, and that is reported plainly.

## Golden rules (each one learned the hard way)

1. **Always page.** An unpaged `GET /api/Jobs` returns so much data it
   crashes the MCP connection. Every collection query gets `$top` (and
   usually `$select`); add `$orderby` when recency or sequence matters.
2. **Body-filter GETs need `odata_filter`.** `GET /api/Jobs` (and other
   collection GETs marked `(json body)` in the reference) return HTTP 415
   unless a JSON body is sent; pass `odata_filter={"shouldShowMyJobsOnly": false}`.
3. **`jobID` is a GUID; people use the contract number.** "Job 26055" is
   `contractNumber` (a string: `contractNumber eq '26055'`). Resolve contract
   number to GUID first, then hit the per-job endpoints and pass that GUID as
   `job_id` to every change.
4. **Send only what changes.** PATCH keeps any field left out and clears a
   field sent as null or empty (checked on the 8 Oct 2026 writes), so a body
   carries the changed fields only. The gate drops unchanged values itself and
   sends custom fields as the full set, because OSC may replace that list
   whole.
5. **Attachments go through `form`/`files`, not `body`.** The message
   endpoints take `multipart/form-data`:
   `form={"Subject": "...", "Body": "...", "Documents[0].description": "..."}`
   and `files={"Documents[0].file": "<absolute path on the MCP server>"}`.
   The file must sit under an upload root (`OSC_UPLOAD_ROOTS`, default the
   checkout's `runtime\` folder); copy it there first. The preview checks the
   file (size, under a root) without opening it.

## Query cookbook (verified against spec v7.3, Sep 2026)

Most recent jobs:

```
osc_get path=/api/Jobs
        query={"$orderby": "createdOnUtc desc", "$top": 5,
               "$select": "jobID,contractNumber,clientName,siteAddress,createdOnUtc,workflowStatusName"}
        odata_filter={}
```

Find a job by contract number (then keep its `jobID` GUID):

```
osc_get path=/api/Jobs
        query={"$filter": "contractNumber eq 12345", "$top": 2}
        odata_filter={}
```

(If the filter errors on type, try the quoted form `'12345'`.)

Workflow activities for a job — filter `/api/JobActivities` by the GUID:

```
osc_get path=/api/JobActivities
        query={"$filter": "jobID eq <guid>", "$orderby": "sequence",
               "$top": 200,
               "$select": "sequence,description,completionDate,bookedStartDate,forecastedStartDate,forecastedCompletionDate,isNotApplicable,serviceProvider"}
```

Activity status is derived, not a field: `completionDate` set → complete;
`isNotApplicable` → N/A; otherwise pending (booked dates show what is
scheduled). A job's variations: `GET /api/Jobs/{JobID}/Variations`; its
defects, inspections, documents, contacts: see the per-job endpoints in the
reference.

Collection responses arrive in a paging envelope
(`currentPage, pagedItems, sourceCollectionCount`) or OData form
(`@odata.count, value`) — read the items out of the envelope.

## Endpoint and field reference

[`references/endpoints.md`](references/endpoints.md) — all endpoints from the
OpenAPI spec grouped by tag, writes marked `[WRITE]`, plus property names for
the core entities (use them for `$select` / `$filter` / `$orderby` instead of
guessing). Only fall back to `osc_list_endpoints` / `osc_describe_endpoint`
when the reference looks stale or lacks a detail.

Regenerate when Companion Systems moves the API version (the file header
records the spec version it was built from):

```powershell
& "<repo>\shared\mcp\osc-api\.venv\Scripts\python.exe" `
  "<repo>\.claude\skills\osc-api\scripts\generate_endpoints.py"
```

The generator reads `OSC_SWAGGER_URL` from the environment / `.env`, strips
every host string, and refuses to write if one leaks into the output.
