---
name: osc-api
description: >
  Query and (with approval) update OnSite Companion via the osc-api MCP
  server, using the preloaded endpoint reference instead of runtime
  discovery. Use whenever a task touches OSC data - jobs, job activities,
  clients, contacts, variations, defects, inspections, documents, alerts -
  e.g. "list recent jobs in OSC", "activities for job 26055", "find client X".
---

# OSC API (OnSite Companion)

Fast-path knowledge for the **`osc-api` MCP server** (see
`docs/mcp-servers.md` and `shared/mcp/osc-api/README.md`). The server exposes
five generic tools; this skill supplies what they would otherwise have to
discover at run time — endpoints, field names, and the query patterns that
work — so a request costs one or two calls instead of six to ten.

**Never put a hostname, address, or credential in this skill or anywhere in
the repo.** All of that lives in `OSC_*` environment variables (git-ignored
`.env` beside `shared/mcp/osc-api/`). The endpoint reference here is
generated with that guardrail enforced.

## Prerequisites

- The `osc-api` MCP server is registered at **user scope**, so every new
  session has the tools: `osc_token_info`, `osc_list_endpoints`,
  `osc_describe_endpoint`, `osc_get` (all read, allowed without prompts) and
  `osc_write` (gated). If the tools are missing, the session predates the
  registration — ask the user to start a new session / reload the window.
- The nominal *dev* environment serves **real production client data**.
  Treat every response as live client data under the org guardrails: fine to
  show the user, never written to the repo, `C:`, or Dropbox.

## Golden rules (each one learned the hard way)

1. **Always page.** An unpaged `GET /api/Jobs` returns so much data it
   crashes the MCP connection. Every collection query gets `$top` (and
   usually `$select`); add `$orderby` when recency or sequence matters.
2. **Body-filter GETs need `odata_filter`.** `GET /api/Jobs` (and other
   collection GETs marked `(json body)` in the reference) return HTTP 415
   unless a JSON body is sent — pass `odata_filter={}` for "no filter".
3. **`jobID` is a GUID; people use the contract number.** "Job 26055" is
   `contractNumber` (on some models `contractNo`). Resolve contract number →
   GUID first, then hit the per-job endpoints.
4. **Writes are gated three ways** (server flag, `ask` rule, `confirm=true`)
   and stay that way. Some writes send real email (`EmailWorkReleases`) or
   are hard to undo (`Complete`, `Delete`). Draft, show the human, wait.

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
